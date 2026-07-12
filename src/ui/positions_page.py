from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.viewmodels.positions_view_model import PositionsViewModel


class PositionsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = PositionsViewModel()
        self._build_ui()
        self._wire_events()
        self._vm.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Positions")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["ALL", "Open Positions", "Closed Positions", "Intraday", "Delivery", "F&O", "Equity"])
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Alphabetical", "Highest Profit", "Highest Loss", "Exchange"])
        filters.addWidget(self.filter_combo)
        filters.addWidget(self.sort_combo)
        filters.addStretch()
        layout.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Symbol", "Net Qty", "Avg Price", "LTP", "MTM", "Realized P&L", "Unrealized P&L", "Exchange"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.exit_btn = QPushButton("Exit Position")
        self.reverse_btn = QPushButton("Reverse Position")
        self.add_btn = QPushButton("Add Quantity")
        self.square_btn = QPushButton("Square Off")
        actions.addWidget(self.exit_btn)
        actions.addWidget(self.reverse_btn)
        actions.addWidget(self.add_btn)
        actions.addWidget(self.square_btn)
        actions.addStretch()
        layout.addLayout(actions)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.status)

    def _wire_events(self) -> None:
        self.filter_combo.currentTextChanged.connect(self._vm.set_filter)
        self.sort_combo.currentTextChanged.connect(self._vm.set_sort)
        self._vm.positionsUpdated.connect(self._render)
        self._vm.errorOccurred.connect(self._on_info)

        self.exit_btn.clicked.connect(lambda: self._action(self._vm.exit_position))
        self.reverse_btn.clicked.connect(lambda: self._action(self._vm.reverse_position))
        self.add_btn.clicked.connect(self._add_qty)
        self.square_btn.clicked.connect(lambda: self._action(self._vm.square_off))

    def _selected_symbol(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return item.text().strip() if item is not None else ""

    def _action(self, fn) -> None:
        symbol = self._selected_symbol()
        if not symbol:
            return
        fn(symbol)

    def _add_qty(self) -> None:
        symbol = self._selected_symbol()
        if not symbol:
            return
        self._vm.add_quantity(symbol, 1)

    def _render(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row.symbol,
                row.quantity,
                row.average_price,
                row.ltp,
                row.mtm,
                row.realized_pnl,
                row.unrealized_pnl,
                row.exchange,
            ]
            for c, value in enumerate(values):
                txt = f"{value:,.2f}" if isinstance(value, float) else str(value)
                item = QTableWidgetItem(txt)
                if c in {4, 5, 6}:
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
