from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class LiveMarketRow:
    symbol: str
    company: str
    exchange: str
    ltp: float
    change_percent: float
    volume: int
    high: float
    low: float
    timestamp: datetime
    open: float = 0.0
    close: float = 0.0
    bid: float = 0.0
    ask: float = 0.0


class MarketAdapter(Protocol):
    """Contract for market data adapters used by MarketDataService."""

    name: str

    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...

    def fetch_live_market(self, exchange: str, symbol_query: str = "") -> list[LiveMarketRow]:
        ...

    def supports_streaming(self) -> bool:
        ...

    def subscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        ...

    def unsubscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        ...
