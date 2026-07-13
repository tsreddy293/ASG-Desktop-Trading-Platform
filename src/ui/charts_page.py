from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.chart.controller import ChartController
from src.chart.view import ChartView


class ChartsPage(QWidget):
    """Embedded charts workspace page that reuses the chart component."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._initial_symbol_loaded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.chart_view = ChartView(self)
        self.chart_controller = ChartController(self.chart_view)
        layout.addWidget(self.chart_view)

        self._initial_symbol_timer = QTimer(self)
        self._initial_symbol_timer.setSingleShot(True)
        self._initial_symbol_timer.timeout.connect(self._attempt_initial_symbol_load)
        self._initial_symbol_timer.start(0)

    def _attempt_initial_symbol_load(self) -> None:
        if self._initial_symbol_loaded:
            return
        if not self._is_broker_ready():
            self._initial_symbol_timer.start(250)
            return

        self._initial_symbol_loaded = True
        self._initial_symbol_timer.stop()
        self.chart_controller.set_symbol("SBIN", "NSE")

    def _is_broker_ready(self) -> bool:
        try:
            broker_client = self.chart_controller._viewmodel._refresh_service._chart_service._market_service._login_service._broker_client
            return broker_client.session_manager.is_connected() and not broker_client.authentication_in_progress()
        except Exception:
            return False

    def closeEvent(self, event: QCloseEvent) -> None:
        self._initial_symbol_timer.stop()
        self.chart_controller.stop()
        super().closeEvent(event)
