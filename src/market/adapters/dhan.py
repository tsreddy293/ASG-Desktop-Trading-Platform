from __future__ import annotations

from src.market.adapters.base import LiveMarketRow


class DhanAdapter:
    """Adapter placeholder for Dhan API integration."""

    name = "dhan"

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = False

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def fetch_live_market(self, exchange: str, symbol_query: str = "") -> list[LiveMarketRow]:
        raise NotImplementedError("Dhan login is not implemented yet")

    def supports_streaming(self) -> bool:
        return True

    def subscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        raise NotImplementedError("Dhan streaming is not implemented yet")

    def unsubscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None
