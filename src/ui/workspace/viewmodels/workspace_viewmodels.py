from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.ui.workspace.services.workspace_service import WorkspaceService


class WatchlistPanelViewModel(QObject):
    symbolsUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.symbolsUpdated.emit(self._service.get_watchlist())


class ChartPanelViewModel(QObject):
    chartStateUpdated = Signal(dict)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()
        self._state = self._service.get_chart_state()

    def refresh(self) -> None:
        self.chartStateUpdated.emit(dict(self._state))

    def set_symbol(self, symbol: str) -> None:
        self._state["symbol"] = (symbol or "SBIN").strip().upper() or "SBIN"
        self.chartStateUpdated.emit(dict(self._state))

    def set_timeframe(self, timeframe: str) -> None:
        self._state["timeframe"] = timeframe or "15m"
        self.chartStateUpdated.emit(dict(self._state))


class OrderPanelViewModel(QObject):
    orderIntentUpdated = Signal(dict)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def emit_order_intent(self, payload: dict) -> None:
        self.orderIntentUpdated.emit(dict(payload))


class PositionsPanelViewModel(QObject):
    positionsUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.positionsUpdated.emit(self._service.get_positions())


class OrdersPanelViewModel(QObject):
    ordersUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.ordersUpdated.emit(self._service.get_orders())


class HoldingsPanelViewModel(QObject):
    holdingsUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.holdingsUpdated.emit(self._service.get_holdings())


class MarketDepthPanelViewModel(QObject):
    depthUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.depthUpdated.emit(self._service.get_market_depth())


class OptionChainPanelViewModel(QObject):
    chainUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.chainUpdated.emit(self._service.get_option_chain())


class AIScannerPanelViewModel(QObject):
    scannerUpdated = Signal(list)

    def __init__(self, service: WorkspaceService | None = None) -> None:
        super().__init__()
        self._service = service or WorkspaceService()

    def refresh(self) -> None:
        self.scannerUpdated.emit(self._service.get_ai_scanner())
