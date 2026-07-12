from __future__ import annotations

from src.marketdata.engine import EventHandler
from src.marketdata.service import MarketDataService, market_data_service


class MarketDataController:
    """Controller façade for application lifecycle and subscriptions."""

    def __init__(self, service: MarketDataService | None = None) -> None:
        self.service = service or market_data_service

    def start(self) -> None:
        self.service.start()

    def stop(self) -> None:
        self.service.stop()

    def subscribe(self, handler: EventHandler) -> None:
        self.service.subscribe(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self.service.unsubscribe(handler)
