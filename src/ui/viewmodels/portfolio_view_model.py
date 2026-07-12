from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.marketdata.model import MarketDataEvent, MarketEventType
from src.services.portfolio_service import PortfolioService


class PortfolioViewModel(QObject):
    summaryUpdated = Signal(dict)
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
            summary = self._service.get_summary()
            self.summaryUpdated.emit(
                {
                    "available_cash": summary.available_cash,
                    "margin_used": summary.margin_used,
                    "total_investment": summary.total_investment,
                    "current_value": summary.current_value,
                    "todays_profit": summary.todays_profit,
                    "overall_profit": summary.overall_profit,
                    "updated_at": summary.updated_at,
                }
            )
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    def _on_market_event(self, event: MarketDataEvent) -> None:
        if event.event_type == MarketEventType.TICK:
            self.refresh()
