from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

from src.market.cache import MarketSnapshot
from src.market.symbols import MarketSymbol


class MarketProviderError(RuntimeError):
    """Raised when a market data provider operation fails."""


class MarketDataProvider(Protocol):
    """Provider contract for any broker/feed implementation."""

    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...

    def fetch_snapshots(self, symbols: list[MarketSymbol]) -> list[MarketSnapshot]:
        ...


@dataclass(slots=True)
class SimulatedMarketDataProvider:
    """Production-safe simulated provider until real broker integrations are added."""

    seed_price: float = 1000.0
    _connected: bool = field(default=False, init=False)

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def fetch_snapshots(self, symbols: list[MarketSymbol]) -> list[MarketSnapshot]:
        if not self._connected:
            raise MarketProviderError("Provider is not connected")

        now = datetime.now(timezone.utc)
        results: list[MarketSnapshot] = []
        for index, item in enumerate(symbols):
            previous_close = self.seed_price + (index * 17)
            wave = ((now.second + index) % 12) - 6
            ltp = previous_close + float(wave)
            high = max(previous_close + 10.0, ltp)
            low = min(previous_close - 10.0, ltp)
            results.append(
                MarketSnapshot(
                    symbol=item.symbol,
                    company=item.company,
                    exchange=item.exchange,
                    ltp=ltp,
                    open=previous_close - 2.0,
                    high=high,
                    low=low,
                    previous_close=previous_close,
                    change=ltp - previous_close,
                    change_percent=0.0,
                    volume=100000 + (index * 5000) + now.second * 100,
                    bid=ltp - 0.1,
                    ask=ltp + 0.1,
                    timestamp=now + timedelta(milliseconds=index),
                )
            )
        return results


class ProviderRegistry:
    """Registry for future broker-specific providers."""

    SUPPORTED_BROKERS = {
        "groww",
        "5paisa",
        "zerodha",
        "angelone",
        "dhan",
    }

    @classmethod
    def create(cls, broker: str | None) -> MarketDataProvider:
        normalized = (broker or "").strip().lower()
        if not normalized:
            return SimulatedMarketDataProvider()
        if normalized in cls.SUPPORTED_BROKERS:
            # Real adapters will be introduced in a later sprint.
            return SimulatedMarketDataProvider()
        raise MarketProviderError(f"Unsupported broker provider: {broker}")
