from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from src.analysis.controller import AIAnalysisController
from src.core.config import config
from src.core.constants import WINDOW_HEIGHT, WINDOW_WIDTH
from src.core.translation import t
from src.scanner.controller import ScannerController
from src.ui.ai_analysis_view import AIAnalysisView
from src.ui.ai_scanner_page import AIScannerPage
from src.ui.charts_page import ChartsPage
from src.ui.chart_window import ChartWindow
from src.ui.dashboard_page import DashboardPage
from src.ui.market_watch_page import MarketWatchPage
from src.ui.menu import NavigationMenu
from src.ui.holdings_page import HoldingsPage
from src.ui.orders_page import OrdersPage
from src.ui.portfolio_summary_page import PortfolioSummaryPage
from src.ui.positions_page import PositionsPage
from src.ui.statusbar import AppStatusBar
from src.ui.styles import AppStyles
from src.ui.toolbar import MainToolbar
from src.ui.watchlist_page import WatchListPage
from src.ui.workspace import ProfessionalMarketWorkspacePage


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, app: QApplication | None = None) -> None:
        super().__init__()
        self.app = app
        self.setWindowTitle(t("window.title", app_name=config.get("app_name", "AI Stock Guardian"), version=config.get("version", "0.2.0")))
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._build_ui()

    def _build_ui(self) -> None:
        self.toolbar = MainToolbar(self)
        self.toolbar.refresh_requested.connect(self._refresh_current_page)
        self.toolbar.symbol_search_requested.connect(self._on_symbol_search)
        self.addToolBar(self.toolbar)

        self.status_bar = AppStatusBar(self)
        self.setStatusBar(self.status_bar)

        container = QWidget(self)
        container.setObjectName("main_container")
        container_layout = QGridLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(12)

        self.navigation = NavigationMenu(self)
        self.navigation.setFixedWidth(240)
        self.navigation.page_selected.connect(self._switch_page)
        container_layout.addWidget(self.navigation, 0, 0, 1, 1)

        self.pages = QStackedWidget(self)
        self.dashboard_page = DashboardPage(self)
        self.market_workspace_page = ProfessionalMarketWorkspacePage(self)
        self.market_watch_page = MarketWatchPage(self)
        self.watchlist_page = WatchListPage(self)
        self.portfolio_page = PortfolioSummaryPage(self)
        self.ai_analysis_page = AIAnalysisView(self)
        self.ai_analysis_controller = AIAnalysisController(self.ai_analysis_page)
        self.charts_page = ChartsPage(self)
        self.ai_scanner_page = AIScannerPage(self)
        self.ai_scanner_controller = ScannerController(
            view=self.ai_scanner_page,
            on_open_analysis=self.open_ai_analysis,
            on_open_chart=self.open_chart,
            on_navigate=self._switch_page,
        )
        self.ai_scanner_controller.refresh_scan()

        self.orders_page = OrdersPage(self)
        self.positions_page = PositionsPage(self)
        self.holdings_page = HoldingsPage(self)
        self.strategy_page = self._build_stub_page("Strategy")
        self.settings_page = self._build_stub_page("Settings")

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.market_workspace_page)
        self.pages.addWidget(self.market_watch_page)
        self.pages.addWidget(self.watchlist_page)
        self.pages.addWidget(self.ai_scanner_page)
        self.pages.addWidget(self.orders_page)
        self.pages.addWidget(self.positions_page)
        self.pages.addWidget(self.holdings_page)
        self.pages.addWidget(self.portfolio_page)
        self.pages.addWidget(self.strategy_page)
        self.pages.addWidget(self.settings_page)

        self.pages.addWidget(self.ai_analysis_page)
        self.pages.addWidget(self.charts_page)
        container_layout.addWidget(self.pages, 0, 1, 1, 1)
        self.setCentralWidget(container)

        self.setStyleSheet(
            "QMainWindow { background: #0f172a; color: #f8fafc; }"
            "QWidget { color: #f8fafc; }"
            "QLabel { color: #f8fafc; }"
        )

        AppStyles.apply_theme(self.app or QApplication.instance())

    def _build_stub_page(self, title: str) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        subtitle = QLabel("Module ready for production integration")
        subtitle.setStyleSheet("font-size: 14px; color: #94a3b8;")
        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addStretch()
        return widget

    def _switch_page(self, page_name: str) -> None:
        page_map = {
            "route.dashboard": self.dashboard_page,
            "route.market_workspace": self.market_workspace_page,
            "route.market_watch": self.market_watch_page,
            "route.watchlist": self.watchlist_page,
            "route.scanner": self.ai_scanner_page,
            "route.charts": self.charts_page,
            "route.orders": self.orders_page,
            "route.positions": self.positions_page,
            "route.holdings": self.holdings_page,
            "route.portfolio": self.portfolio_page,
            "route.strategy": self.strategy_page,
            "route.settings": self.settings_page,

            "route.ai_analysis": self.ai_analysis_page,
            "route.charts": self.charts_page,
        }
        widget = page_map.get(page_name, self.dashboard_page)
        self.pages.setCurrentWidget(widget)

        if widget is self.dashboard_page:
            self.toolbar.set_connection_status("Connected")
        elif widget in {self.market_workspace_page, self.market_watch_page, self.watchlist_page}:
            self.toolbar.set_connection_status("Connected")
        else:
            self.toolbar.set_connection_status("Ready")

    def open_ai_analysis(self, symbol: str, exchange: str = "NSE", sector: str | None = None) -> None:
        self.ai_analysis_controller.load_symbol(symbol=symbol, exchange=exchange, sector=sector)
        self.pages.setCurrentWidget(self.ai_analysis_page)

    def open_chart(self, symbol: str, exchange: str = "NSE") -> None:
        chart_window = ChartWindow(symbol, self)
        chart_window.exec()

    def _refresh_current_page(self) -> None:
        page = self.pages.currentWidget()
        if hasattr(page, "refresh_data"):
            page.refresh_data()

    def _on_symbol_search(self, symbol: str) -> None:
        page = self.pages.currentWidget()
        panel = getattr(page, "live_quote_panel", None)
        if panel is None:
            self._switch_page("route.market_watch")
            panel = getattr(self.market_watch_page, "live_quote_panel", None)

        if panel is not None:
            panel.symbol_input.setText(symbol)
            panel.refresh_quote()
