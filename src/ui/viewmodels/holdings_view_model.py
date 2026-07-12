from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.marketdata.model import MarketDataEvent, MarketEventType
from src.services.portfolio_service import PortfolioService


class HoldingsViewModel(QObject):
    holdingsUpdated = Signal(list)
    errorOccurred = Signal(str)

    def __init__(self, service: PortfolioService | None = None) -> None:
        super().__init__()
        self._service = service or PortfolioService()

    def start(self) -> None:
        self._service.subscribe(self._on_market_event)
        self.refresh()

    def stop(self) -> None:
        self._service.unsubscribe(self._on_market_event)

    def refresh(self) -> None:
        try:
            self.holdingsUpdated.emit(self._service.get_holdings())
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    def _on_market_event(self, event: MarketDataEvent) -> None:
        if event.event_type == MarketEventType.TICK:
            self.refresh()
