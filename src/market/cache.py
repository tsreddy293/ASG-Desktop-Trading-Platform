from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import RLock


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    company: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    bid: float
    ask: float
    timestamp: datetime


class MarketCache:
    """Thread-safe in-memory cache for latest market snapshots."""

    def __init__(self) -> None:
        self._store: dict[str, MarketSnapshot] = {}
        self._lock = RLock()

    def upsert(self, snapshot: MarketSnapshot) -> None:
        with self._lock:
            self._store[snapshot.symbol] = self._normalized(snapshot)

    def bulk_upsert(self, snapshots: list[MarketSnapshot]) -> None:
        with self._lock:
            for snapshot in snapshots:
                self._store[snapshot.symbol] = self._normalized(snapshot)

    def get(self, symbol: str) -> MarketSnapshot | None:
        with self._lock:
            return self._store.get(symbol.upper())

    def all(self) -> list[MarketSnapshot]:
        with self._lock:
            return list(self._store.values())

    def remove(self, symbol: str) -> None:
        with self._lock:
            self._store.pop(symbol.upper(), None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @staticmethod
    def _normalized(snapshot: MarketSnapshot) -> MarketSnapshot:
        previous_close = float(snapshot.previous_close)
        ltp = float(snapshot.ltp)
        computed_change = ltp - previous_close
        computed_change_percent = 0.0 if previous_close == 0 else (computed_change / previous_close) * 100.0
        return replace(
            snapshot,
            symbol=snapshot.symbol.upper(),
            exchange=snapshot.exchange.upper(),
            ltp=ltp,
            open=float(snapshot.open),
            high=float(snapshot.high),
            low=float(snapshot.low),
            previous_close=previous_close,
            change=computed_change,
            change_percent=computed_change_percent,
            volume=int(snapshot.volume),
            bid=float(snapshot.bid),
            ask=float(snapshot.ask),
            timestamp=snapshot.timestamp or datetime.now(timezone.utc),
        )
