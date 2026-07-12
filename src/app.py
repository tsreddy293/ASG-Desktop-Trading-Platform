from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.core.database import database_manager
from src.core.logger import app_logger
from src.core.translation import t
from src.marketdata.controller import MarketDataController
from src.ui.main_window import MainWindow
from src.ui.splash_screen import SplashScreen


class ASGApplication:
    """Application bootstrapper for AI Stock Guardian."""

    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.market_data_controller = MarketDataController()
        self.app.aboutToQuit.connect(self._shutdown_services)
        self._setup_environment()

    def _setup_environment(self) -> None:
        app_logger.info("Application starting")
        database_manager.initialize()
        app_logger.info("Database initialized")

    def run(self) -> int:
        splash = SplashScreen()
        splash.show()
        splash.update_status(t("splash.loading_config"), 25)
        app_logger.info("Configuration loaded")
        splash.update_status(t("splash.loading_database"), 60)
        app_logger.info("Database ready")
        splash.update_status(t("splash.loading_ui"), 85)
        self.window = MainWindow(self.app)

        def launch() -> None:
            splash.update_status(t("splash.launching"), 100)
            splash.close()
            self.window.show()
            self.market_data_controller.start()
            app_logger.info("Market data engine started")
            app_logger.info("Main window launched")

        QTimer.singleShot(3000, launch)
        return self.app.exec()

    def _shutdown_services(self) -> None:
        self.market_data_controller.stop()
        app_logger.info("Market data engine stopped")


def create_app() -> ASGApplication:
    return ASGApplication()
