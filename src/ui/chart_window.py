from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from src.chart.controller import ChartController
from src.chart.view import ChartView
from src.core.translation import t


class ChartWindow(QDialog):
    """Reusable chart window powered by chart MVC module."""

    def __init__(self, symbol: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.symbol = symbol
        self.setWindowTitle(t("chart.window_title", symbol=symbol))
        self.resize(1120, 720)
        self.setMinimumSize(920, 620)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.chart_view = ChartView(self)
        self.chart_controller = ChartController(self.chart_view)
        layout.addWidget(self.chart_view)
        self.chart_controller.set_symbol(self.symbol, "NSE")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.chart_controller.stop()
        super().closeEvent(event)
