from __future__ import annotations

from datetime import datetime

from src.core.logger import app_logger
from src.market.market_data_service import MarketDataResult, MarketDataService


class LiveMarketController:
    """Controller for Live Market MVC flow."""

    def __init__(self, service: MarketDataService, view) -> None:
        self._service = service
        self._view = view

    def refresh(self) -> None:
        self._service.set_exchange(self._view.selected_exchange())
        self._service.set_symbol_query(self._view.search_text())

        self._view.set_loading_state(True)
        result = self._service.refresh_live_market()
        self._apply_result(result)

    def _apply_result(self, result: MarketDataResult) -> None:
        if result.full_reload or not self._view.has_rows():
            self._view.replace_rows(result.rows)
        else:
            self._view.patch_rows(result.rows, result.changed_symbols)
            if result.removed_symbols:
                self._view.remove_rows(result.removed_symbols)

        self._view.set_loading_state(result.loading)
        self._view.set_reconnect_state(result.reconnecting, result.error)
        self._view.set_last_updated(result.last_updated)
        app_logger.debug("Live Market controller applied refresh result")

    @staticmethod
    def format_timestamp(value: datetime | None) -> str:
        if value is None:
            return "--"
        return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")
