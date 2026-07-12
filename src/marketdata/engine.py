from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, RLock, Thread
from time import sleep
from typing import Callable, Protocol

from src.core.config import config
from src.core.logger import app_logger
from src.marketdata.model import MarketDataEvent, MarketEventType
from src.marketdata.repository import MarketDataRepository


class AngelOneGateway(Protocol):
    """Future integration contract for Angel One SmartAPI streaming gateway."""

    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...


EventHandler = Callable[[MarketDataEvent], None]


@dataclass(slots=True)
class MarketDataEngine:
    """Central event-driven market engine updating repository state."""

    repository: MarketDataRepository
    refresh_interval_seconds: float = 2.0
    angel_one_gateway: AngelOneGateway | None = None
    _handlers: list[EventHandler] = field(default_factory=list, init=False)
    _lock: RLock = field(default_factory=RLock, init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _worker: Thread | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        configured = config.get("market_refresh_interval_seconds", self.refresh_interval_seconds)
        self.refresh_interval_seconds = max(1.0, float(configured))

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = Thread(target=self._run, daemon=True)
        self._worker.start()
        self._emit(MarketDataEvent(MarketEventType.CONNECTION, [], self._now(), "market engine started"))
        app_logger.info("Central MarketDataEngine started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        self._emit(MarketDataEvent(MarketEventType.CONNECTION, [], self._now(), "market engine stopped"))
        app_logger.info("Central MarketDataEngine stopped")

    def subscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                changed = self.repository.step_market()
                self._emit(MarketDataEvent(MarketEventType.TICK, changed, self._now(), "market tick"))
            except Exception as exc:  # pragma: no cover
                app_logger.error(f"Central market engine tick failed: {exc}")
                self._emit(MarketDataEvent(MarketEventType.ERROR, [], self._now(), str(exc)))
            sleep(self.refresh_interval_seconds)

    def _emit(self, event: MarketDataEvent) -> None:
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # pragma: no cover
                app_logger.error(f"MarketDataEngine subscriber error: {exc}")

    @staticmethod
    def _now():
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)
