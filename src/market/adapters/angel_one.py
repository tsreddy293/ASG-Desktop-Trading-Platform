from __future__ import annotations

from src.market.adapters.base import LiveMarketRow


class AngelOneSmartApiAdapter:
    """Adapter placeholder for Angel One SmartAPI integration."""

    name = "angelone"

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        # Broker login/token lifecycle will be implemented in a later phase.
        self._connected = False

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def fetch_live_market(self, exchange: str, symbol_query: str = "") -> list[LiveMarketRow]:
        raise NotImplementedError("Angel One SmartAPI login is not implemented yet")

    def supports_streaming(self) -> bool:
        return True

    def subscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        raise NotImplementedError("Angel One SmartAPI streaming is not implemented yet")

    def unsubscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None
