from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.marketdata.model import MarketDataEvent, MarketEventType
from src.services.portfolio_service import PortfolioService


class PositionsViewModel(QObject):
    positionsUpdated = Signal(list)
    errorOccurred = Signal(str)

    def __init__(self, service: PortfolioService | None = None) -> None:
        super().__init__()
        self._service = service or PortfolioService()
        self._filter = "ALL"
        self._sort = "Alphabetical"

    def start(self) -> None:
        self._service.subscribe(self._on_market_event)
        self.refresh()

    def stop(self) -> None:
        self._service.unsubscribe(self._on_market_event)

    def set_filter(self, value: str) -> None:
        self._filter = value or "ALL"
        self.refresh()

    def set_sort(self, value: str) -> None:
        self._sort = value or "Alphabetical"
        self.refresh()

    def refresh(self) -> None:
        try:
            rows = self._service.get_positions()
            rows = self._service.filter_positions(rows, self._filter)
            rows = self._service.sort_positions(rows, self._sort)
            self.positionsUpdated.emit(rows)
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    def exit_position(self, symbol: str) -> None:
        self.errorOccurred.emit(f"Exit Position queued for {symbol}")

    def reverse_position(self, symbol: str) -> None:
        self.errorOccurred.emit(f"Reverse Position queued for {symbol}")

    def add_quantity(self, symbol: str, qty: int) -> None:
        self.errorOccurred.emit(f"Add Quantity queued for {symbol} x{qty}")

    def square_off(self, symbol: str) -> None:
        self.errorOccurred.emit(f"Square Off queued for {symbol}")

    def _on_market_event(self, event: MarketDataEvent) -> None:
        if event.event_type == MarketEventType.TICK:
            self.refresh()
