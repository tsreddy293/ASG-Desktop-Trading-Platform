from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from threading import Event, RLock, Thread
from time import sleep
from typing import Any, Callable

from src.core.config import config
from src.core.logger import app_logger
from src.market.cache import MarketCache, MarketSnapshot
from src.market.data_provider import MarketDataProvider, MarketProviderError, ProviderRegistry
from src.market.symbols import MarketSymbol
from src.market.watchlist_service import WatchListService


class MarketStatus(str, Enum):
    PRE_OPEN = "pre_open"
    OPEN = "open"
    POST_CLOSE = "post_close"
    CLOSED = "closed"


class MarketEventType(str, Enum):
    STATUS = "status"
    CACHE_UPDATED = "cache_updated"
    CONNECTION = "connection"
    ERROR = "error"


@dataclass(slots=True)
class MarketEvent:
    event_type: MarketEventType
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[MarketEvent], None]


class MarketEventBus:
    """Simple thread-safe event bus for UI-agnostic communication."""

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._lock = RLock()

    def subscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def emit(self, event: MarketEvent) -> None:
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover - defensive callback isolation
                app_logger.error(f"Market event handler failed: {exc}")


class MarketDataManager:
    """Live market data engine independent from UI components."""

    def __init__(
        self,
        watchlist_service: WatchListService | None = None,
        provider: MarketDataProvider | None = None,
        refresh_interval_seconds: float | None = None,
    ) -> None:
        self.watchlist_service = watchlist_service or WatchListService()
        self.provider = provider or ProviderRegistry.create(config.get("broker", ""))
        self.refresh_interval_seconds = float(
            refresh_interval_seconds
            if refresh_interval_seconds is not None
            else config.get("market_refresh_interval_seconds", 5.0)
        )
        self.refresh_interval_seconds = max(1.0, self.refresh_interval_seconds)

        self.cache = MarketCache()
        self.events = MarketEventBus()

        self._symbols: list[MarketSymbol] = []
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._failure_count = 0
        self._connection_lock = RLock()

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        self._stop_event.clear()
        self.load_watchlist()
        self._connect_provider()

        self._worker = Thread(target=self._run_loop, daemon=True)
        self._worker.start()
        app_logger.info("MarketDataManager started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        with self._connection_lock:
            self.provider.disconnect()
        self._emit(MarketEventType.CONNECTION, {"state": "disconnected"})
        app_logger.info("MarketDataManager stopped")

    def load_watchlist(self) -> list[MarketSymbol]:
        entries = self.watchlist_service.list_entries()
        self._symbols = [MarketSymbol(symbol=item.symbol, company=item.company, exchange=item.exchange) for item in entries]
        app_logger.debug(f"Loaded {len(self._symbols)} symbols into market engine")
        return list(self._symbols)

    def market_status(self, current_time: datetime | None = None) -> MarketStatus:
        now = current_time or datetime.now(timezone(timedelta(hours=5, minutes=30)))
        if now.weekday() >= 5:
            return MarketStatus.CLOSED

        local_time = now.timetz().replace(tzinfo=None)
        pre_open_start = time(9, 0)
        market_open = time(9, 15)
        market_close = time(15, 30)
        post_close_end = time(16, 0)

        if pre_open_start <= local_time < market_open:
            return MarketStatus.PRE_OPEN
        if market_open <= local_time <= market_close:
            return MarketStatus.OPEN
        if market_close < local_time <= post_close_end:
            return MarketStatus.POST_CLOSE
        return MarketStatus.CLOSED

    def refresh_once(self) -> list[MarketSnapshot]:
        if not self._symbols:
            self.load_watchlist()
        if not self._symbols:
            return []

        status = self.market_status()
        self._emit(MarketEventType.STATUS, {"status": status.value})

        try:
            snapshots = self.provider.fetch_snapshots(self._symbols)
            self.cache.bulk_upsert(snapshots)
            self._failure_count = 0
            self._emit(
                MarketEventType.CACHE_UPDATED,
                {
                    "count": len(snapshots),
                    "symbols": [snapshot.symbol for snapshot in snapshots],
                },
            )
            return snapshots
        except Exception as exc:
            self._failure_count += 1
            self._emit_error(exc)
            self._attempt_reconnect()
            return []

    def get_snapshot(self, symbol: str) -> MarketSnapshot | None:
        return self.cache.get(symbol)

    def list_snapshots(self) -> list[MarketSnapshot]:
        return self.cache.all()

    def subscribe(self, handler: EventHandler) -> None:
        self.events.subscribe(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self.events.unsubscribe(handler)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_once()
            sleep(self.refresh_interval_seconds)

    def _connect_provider(self) -> None:
        with self._connection_lock:
            if self.provider.is_connected():
                return
            self.provider.connect()
        self._emit(MarketEventType.CONNECTION, {"state": "connected"})

    def _attempt_reconnect(self) -> None:
        backoff = min(20.0, float(2 ** min(self._failure_count, 4)))
        app_logger.warning(f"Market provider reconnect attempt in {backoff:.1f}s")
        self._emit(MarketEventType.CONNECTION, {"state": "reconnecting", "backoff_seconds": backoff})
        sleep(backoff)
        try:
            with self._connection_lock:
                self.provider.disconnect()
                self.provider.connect()
            self._emit(MarketEventType.CONNECTION, {"state": "connected"})
            app_logger.info("Market provider reconnected")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._emit_error(exc)

    def _emit(self, event_type: MarketEventType, payload: dict[str, Any]) -> None:
        self.events.emit(MarketEvent(event_type=event_type, payload=payload))

    def _emit_error(self, exc: Exception) -> None:
        message = str(exc)
        app_logger.error(f"Market data refresh failed: {message}")
        error_type = "provider" if isinstance(exc, MarketProviderError) else "runtime"
        self._emit(
            MarketEventType.ERROR,
            {
                "error": message,
                "type": error_type,
                "failure_count": self._failure_count,
            },
        )
