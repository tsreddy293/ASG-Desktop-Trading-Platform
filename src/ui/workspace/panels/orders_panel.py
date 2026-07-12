from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import OrdersPanelViewModel


class OrdersPanel(QWidget):
    def __init__(self, viewmodel: OrdersPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or OrdersPanelViewModel()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Order ID", "Symbol", "Side", "Qty", "Status"])
        layout.addWidget(self.table)

        self._vm.ordersUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("order_id", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("symbol", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("side", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("qty", 0))))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("status", ""))))
