from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication

from src.ui.market_watch.models import QuoteDetails
from src.ui.market_watch.service import MarketWatchBackgroundService
from src.ui.market_watch.view_model import MarketWatchViewModel
from src.ui.market_watch.widgets import MarketDepthPanel, QuoteDetailsDialog


class _Backend:
    def __init__(self) -> None:
        self.quote_calls = 0
        self.depth_calls = 0

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        self.quote_calls += 1
        rows = []
        for index, symbol in enumerate(symbols):
            rows.append(
                {
                    "symbol": symbol,
                    "ltp": 100.0 + index,
                    "close": 99.0 + index,
                    "open": 98.0 + index,
                    "high": 101.0 + index,
                    "low": 97.0 + index,
                    "volume": 10000 + index,
                    "bid": 99.8 + index,
                    "ask": 100.2 + index,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
        return rows

    def get_market_depth(self, symbol: str) -> dict:
        self.depth_calls += 1
        return {
            "buy_levels": [
                {"quantity": 1000 - i * 10, "price": 99.8 - i * 0.05, "orders": 2 + i} for i in range(5)
            ],
            "sell_levels": [
                {"quantity": 900 - i * 8, "price": 100.2 + i * 0.05, "orders": 1 + i} for i in range(5)
            ],
            "timestamp": datetime.now(timezone.utc),
        }

    def get_quote(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "ltp": 120.5,
            "open": 118.0,
            "high": 121.2,
            "low": 117.6,
            "close": 119.1,
            "volume": 42000,
            "bid": 120.4,
            "ask": 120.6,
            "timestamp": datetime.now(timezone.utc),
            "change": 1.4,
            "change_percent": 1.18,
        }


def test_market_watch_background_service_single_refresh_flow() -> None:
    backend = _Backend()
    service = MarketWatchBackgroundService(backend=backend, interval_ms=2000)
    service.set_symbols(["HDFCBANK", "SBIN"])
    service.set_selected_symbol("HDFCBANK")

    emitted = []
    service.state_updated.connect(emitted.append)

    service.refresh_once()

    assert len(emitted) == 1
    state = emitted[0]
    assert state.connected is True
    assert len(state.quotes) == 2
    assert state.depth is not None
    assert backend.quote_calls == 1
    assert backend.depth_calls == 1


def test_market_watch_view_model_add_remove_pin_and_search() -> None:
    backend = _Backend()
    vm = MarketWatchViewModel(backend=backend)

    vm.add_symbol("INFY")
    vm.toggle_pin("INFY")
    vm.set_search_text("INF")

    visible = vm.visible_symbols()
    assert visible[0] == "INFY"
    assert vm.is_pinned("INFY") is True

    vm.remove_symbol("INFY")
    assert "INFY" not in vm.visible_symbols()


def test_market_watch_view_model_quote_details_fields() -> None:
    backend = _Backend()
    vm = MarketWatchViewModel(backend=backend)

    details = vm.quote_details("HDFCBANK")

    assert details.symbol == "HDFCBANK"
    assert details.ltp is not None
    assert details.open is not None
    assert details.high is not None
    assert details.low is not None
    assert details.close is not None
    assert details.volume is not None
    assert details.bid is not None
    assert details.ask is not None


def test_market_depth_panel_updates_5_levels() -> None:
    app = QApplication.instance() or QApplication([])
    panel = MarketDepthPanel()

    backend = _Backend()
    state_service = MarketWatchBackgroundService(backend=backend, interval_ms=2000)
    state_service.set_symbols(["HDFCBANK"])
    state_service.set_selected_symbol("HDFCBANK")

    emitted = []
    state_service.state_updated.connect(emitted.append)
    state_service.refresh_once()

    assert emitted
    panel.update_snapshot(emitted[0].depth)

    assert panel.table.rowCount() == 5
    assert panel.table.item(0, 0).text() != "--"
    assert panel.table.item(0, 2).text() != "--"

    panel.close()
    app.quit()


def test_quote_details_dialog_renders_required_fields() -> None:
    app = QApplication.instance() or QApplication([])
    details = QuoteDetails(
        symbol="HDFCBANK",
        ltp=120.5,
        open=118.0,
        high=121.2,
        low=117.6,
        close=119.1,
        upper_circuit=None,
        lower_circuit=None,
        week_52_high=None,
        week_52_low=None,
        volume=42000,
        bid=120.4,
        ask=120.6,
        last_trade_time=datetime.now(timezone.utc),
    )
    dialog = QuoteDetailsDialog(details)

    assert dialog.windowTitle().startswith("Quote Details")

    dialog.close()
    app.quit()
