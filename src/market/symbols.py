from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MarketSymbol:
    """Canonical market symbol model used by the market engine only."""

    symbol: str
    company: str
    exchange: str = "NSE"

    @property
    def instrument_key(self) -> str:
        return f"{self.exchange}:{self.symbol}"
