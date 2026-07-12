from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.viewmodels.holdings_view_model import HoldingsViewModel


class HoldingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = HoldingsViewModel()
        self._build_ui()
        self._wire_events()
        self._vm.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Holdings")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Symbol",
            "Type",
            "Qty",
            "Average Cost",
            "LTP",
            "Current Value",
            "Day Change",
            "Total Profit",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.status)

    def _wire_events(self) -> None:
        self._vm.holdingsUpdated.connect(self._render)
        self._vm.errorOccurred.connect(self._on_info)

    def _render(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row.symbol,
                row.holding_type,
                row.quantity,
                row.average_cost,
                row.ltp,
                row.current_value,
                row.day_change,
                row.total_profit,
            ]
            for c, value in enumerate(values):
                txt = f"{value:,.2f}" if isinstance(value, float) else str(value)
                item = QTableWidgetItem(txt)
                if c in {6, 7}:
                    pnl = float(value)
                    if pnl > 0:
                        item.setForeground(Qt.GlobalColor.green)
                    elif pnl < 0:
                        item.setForeground(Qt.GlobalColor.red)
                    else:
                        item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(i, c, item)

    def _on_info(self, text: str) -> None:
        self.status.setText(text)

    def refresh_data(self) -> None:
        self._vm.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._vm.stop()
        super().closeEvent(event)
