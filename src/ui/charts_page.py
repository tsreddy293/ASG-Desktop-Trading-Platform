from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.chart.controller import ChartController
from src.chart.view import ChartView


class ChartsPage(QWidget):
    """Embedded charts workspace page that reuses the chart component."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.chart_view = ChartView(self)
        self.chart_controller = ChartController(self.chart_view)
        layout.addWidget(self.chart_view)
        self.chart_controller.set_symbol("SBIN", "NSE")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.chart_controller.stop()
        super().closeEvent(event)
