from __future__ import annotations

from collections.abc import Callable

from src.core.logger import app_logger
from src.core.translation import t
from src.market.watchlist_service import WatchListService
from src.scanner.model import ScannerFilters, ScannerRow
from src.scanner.service import ScannerService


class ScannerController:
    """Controller layer for AI scanner MVC interactions."""

    def __init__(
        self,
        view,
        service: ScannerService | None = None,
        watchlist_service: WatchListService | None = None,
        on_open_chart: Callable[[str], None] | None = None,
        on_open_analysis: Callable[[str], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        self._view = view
        self._service = service or ScannerService()
        self._watchlist_service = watchlist_service or WatchListService()
        self._on_open_chart = on_open_chart
        self._on_open_analysis = on_open_analysis
        self._on_navigate = on_navigate
        self._rows_by_symbol: dict[str, ScannerRow] = {}

        self._view.scan_requested.connect(self.refresh_scan)
        self._view.row_open_requested.connect(self._open_analysis)
        self._view.context_action_requested.connect(self.handle_context_action)

    def refresh_scan(self) -> None:
        filters = self._view.current_filters()
        rows, summary = self._service.scan(filters)
        self._rows_by_symbol = {row.symbol: row for row in rows}
        self._view.populate_results(rows)
        self._view.update_scan_status(summary)
        app_logger.info(f"AI Scanner refreshed: qualified={summary.stocks_qualified} scanned={summary.stocks_scanned}")

    def handle_context_action(self, action: str, symbol: str) -> None:
        action_map = {
            t("scanner.ctx.add_watchlist"): "add_watchlist",
            t("scanner.ctx.open_chart"): "open_chart",
            t("scanner.ctx.ai_analysis"): "ai_analysis",
            t("scanner.ctx.market_depth"): "market_depth",
            t("scanner.ctx.option_chain"): "option_chain",
            "Add to Watch List": "add_watchlist",
            "Open Chart": "open_chart",
            "AI Analysis": "ai_analysis",
            "Market Depth": "market_depth",
            "Option Chain": "option_chain",
        }
        normalized_action = action_map.get(action, action)

        row = self._rows_by_symbol.get(symbol)
        if row is None:
            return

        if normalized_action == "add_watchlist":
            self._watchlist_service.add_symbol(row.symbol, row.company, "NSE", row.ltp, "Neutral")
            self._view.show_info(t("menu.market.watchlist"), t("watchlist.added_message", symbol=row.symbol))
            return

        if normalized_action == "open_chart":
            self._open_chart(symbol)
            return

        if normalized_action == "ai_analysis":
            self._open_analysis(symbol)
            return

        if normalized_action == "market_depth":
            self._navigate("route.market_depth")
            return

        if normalized_action == "option_chain":
            self._navigate("route.option_chain")

    def _open_chart(self, symbol: str) -> None:
        if self._on_open_chart:
            self._on_open_chart(symbol)
        else:
            self._view.open_chart(symbol)

    def _open_analysis(self, symbol: str) -> None:
        if self._on_open_analysis:
            self._on_open_analysis(symbol)
        else:
            self._view.show_info(t("menu.ai.analysis"), t("scanner.msg.ai_analysis_not_connected", symbol=symbol))

    def _navigate(self, page_name: str) -> None:
        if self._on_navigate:
            self._on_navigate(page_name)
