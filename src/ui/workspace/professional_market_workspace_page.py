from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.ui.workspace.panels.ai_scanner_panel import AIScannerPanel
from src.ui.workspace.panels.chart_panel import ChartPanel
from src.ui.workspace.panels.holdings_panel import HoldingsPanel
from src.ui.workspace.panels.market_depth_panel import MarketDepthPanel
from src.ui.workspace.panels.option_chain_panel import OptionChainPanel
from src.ui.workspace.panels.order_panel import OrderPanel
from src.ui.workspace.panels.orders_panel import OrdersPanel
from src.ui.workspace.panels.positions_panel import PositionsPanel
from src.ui.workspace.panels.watchlist_panel import WatchlistPanel


class ProfessionalMarketWorkspacePage(QWidget):
    """Professional market workspace with dock-style layout and independent panels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.menu_bar = QMenuBar(self)
        workspace_menu = self.menu_bar.addMenu("Workspace")
        view_menu = self.menu_bar.addMenu("View")
        tools_menu = self.menu_bar.addMenu("Tools")
        workspace_menu.addAction(QAction("New Layout", self))
        workspace_menu.addAction(QAction("Save Layout", self))
        view_menu.addAction(QAction("Reset Panels", self))
        tools_menu.addAction(QAction("Quick Order", self))
        root.addWidget(self.menu_bar)

        self.toolbar = QToolBar("Workspace", self)
        self.toolbar.setMovable(False)
        self.toolbar.addWidget(QLabel("Market Workspace"))
        self.toolbar.addSeparator()
        self.toolbar.addWidget(QPushButton("Sync"))
        self.toolbar.addWidget(QPushButton("Layouts"))
        self.toolbar.addWidget(QPushButton("Alerts"))
        root.addWidget(self.toolbar)

        vertical = QSplitter(Qt.Orientation.Vertical, self)
        top_split = QSplitter(Qt.Orientation.Horizontal, vertical)

        self.left_watchlist = WatchlistPanel(parent=self)
        self.center_chart = ChartPanel(parent=self)
        self.right_order = OrderPanel(parent=self)

        top_split.addWidget(self.left_watchlist)
        top_split.addWidget(self.center_chart)
        top_split.addWidget(self.right_order)
        top_split.setSizes([280, 880, 320])

        self.bottom_tabs = QTabWidget(self)
        self.positions_panel = PositionsPanel(parent=self)
        self.orders_panel = OrdersPanel(parent=self)
        self.holdings_panel = HoldingsPanel(parent=self)
        self.market_depth_panel = MarketDepthPanel(parent=self)
        self.option_chain_panel = OptionChainPanel(parent=self)
        self.ai_scanner_panel = AIScannerPanel(parent=self)

        self.bottom_tabs.addTab(self.positions_panel, "Positions")
        self.bottom_tabs.addTab(self.orders_panel, "Orders")
        self.bottom_tabs.addTab(self.holdings_panel, "Holdings")
        self.bottom_tabs.addTab(self.market_depth_panel, "Market Depth")
        self.bottom_tabs.addTab(self.option_chain_panel, "Option Chain")
        self.bottom_tabs.addTab(self.ai_scanner_panel, "AI Scanner")

        vertical.addWidget(top_split)
        vertical.addWidget(self.bottom_tabs)
        vertical.setSizes([620, 260])

        root.addWidget(vertical, 1)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Workspace Ready")
        self.status_label.setStyleSheet("color: #94a3b8;")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(QLabel("Broker: FivePaisa"))
        root.addLayout(status_row)

    def refresh_data(self) -> None:
        self.status_label.setText("Workspace Refreshed")
