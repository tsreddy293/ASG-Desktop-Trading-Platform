from __future__ import annotations

from src.ui.workspace.viewmodels.workspace_viewmodels import (
    AIScannerPanelViewModel,
    ChartPanelViewModel,
    HoldingsPanelViewModel,
    MarketDepthPanelViewModel,
    OptionChainPanelViewModel,
    OrderPanelViewModel,
    OrdersPanelViewModel,
    PositionsPanelViewModel,
    WatchlistPanelViewModel,
)


class _FakeWorkspaceService:
    def get_watchlist(self) -> list[str]:
        return ["SBIN", "TCS"]

    def get_chart_state(self) -> dict:
        return {"symbol": "SBIN", "timeframe": "15m", "chart_type": "Candlestick", "status": "Connected"}

    def get_positions(self) -> list[dict]:
        return [{"symbol": "SBIN", "qty": 1}]

    def get_orders(self) -> list[dict]:
        return [{"order_id": "OID-1", "symbol": "SBIN"}]

    def get_holdings(self) -> list[dict]:
        return [{"symbol": "INFY", "qty": 2}]

    def get_market_depth(self) -> list[dict]:
        return [{"bid_qty": 10, "bid": 100.0, "ask": 100.2, "ask_qty": 8}]

    def get_option_chain(self) -> list[dict]:
        return [{"strike": 25000, "ce_ltp": 100.0, "pe_ltp": 120.0, "pcr": 1.1}]

    def get_ai_scanner(self) -> list[dict]:
        return [{"symbol": "SBIN", "signal": "Momentum", "confidence": "88%", "time": "10:00:00"}]


def test_workspace_watchlist_and_chart_viewmodels_emit_updates() -> None:
    service = _FakeWorkspaceService()

    watch_vm = WatchlistPanelViewModel(service=service)
    seen_symbols = []
    watch_vm.symbolsUpdated.connect(seen_symbols.append)
    watch_vm.refresh()
    assert seen_symbols[-1] == ["SBIN", "TCS"]

    chart_vm = ChartPanelViewModel(service=service)
    seen_chart = []
    chart_vm.chartStateUpdated.connect(seen_chart.append)
    chart_vm.refresh()
    chart_vm.set_symbol("hdfcbank")
    chart_vm.set_timeframe("1H")
    assert seen_chart[-1]["symbol"] == "HDFCBANK"
    assert seen_chart[-1]["timeframe"] == "1H"


def test_workspace_order_panel_viewmodel_emits_order_intent() -> None:
    vm = OrderPanelViewModel(service=_FakeWorkspaceService())
    seen = []
    vm.orderIntentUpdated.connect(seen.append)

    vm.emit_order_intent({"side": "BUY", "qty": 5})

    assert seen[-1]["side"] == "BUY"
    assert seen[-1]["qty"] == 5


def test_workspace_bottom_panel_viewmodels_emit_rows() -> None:
    service = _FakeWorkspaceService()

    positions_vm = PositionsPanelViewModel(service=service)
    orders_vm = OrdersPanelViewModel(service=service)
    holdings_vm = HoldingsPanelViewModel(service=service)
    depth_vm = MarketDepthPanelViewModel(service=service)
    chain_vm = OptionChainPanelViewModel(service=service)
    scanner_vm = AIScannerPanelViewModel(service=service)

    seen_positions = []
    seen_orders = []
    seen_holdings = []
    seen_depth = []
    seen_chain = []
    seen_scanner = []

    positions_vm.positionsUpdated.connect(seen_positions.append)
    orders_vm.ordersUpdated.connect(seen_orders.append)
    holdings_vm.holdingsUpdated.connect(seen_holdings.append)
    depth_vm.depthUpdated.connect(seen_depth.append)
    chain_vm.chainUpdated.connect(seen_chain.append)
    scanner_vm.scannerUpdated.connect(seen_scanner.append)

    positions_vm.refresh()
    orders_vm.refresh()
    holdings_vm.refresh()
    depth_vm.refresh()
    chain_vm.refresh()
    scanner_vm.refresh()

    assert seen_positions[-1][0]["symbol"] == "SBIN"
    assert seen_orders[-1][0]["order_id"] == "OID-1"
    assert seen_holdings[-1][0]["symbol"] == "INFY"
    assert seen_depth[-1][0]["bid_qty"] == 10
    assert seen_chain[-1][0]["strike"] == 25000
    assert seen_scanner[-1][0]["signal"] == "Momentum"
