from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import MarketDepthPanelViewModel


class MarketDepthPanel(QWidget):
    def __init__(self, viewmodel: MarketDepthPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or MarketDepthPanelViewModel()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Bid Qty", "Bid", "Ask", "Ask Qty"])
        layout.addWidget(self.table)

        self._vm.depthUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("bid_qty", 0))))
            self.table.setItem(i, 1, QTableWidgetItem(f"{float(row.get('bid', 0.0)):,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{float(row.get('ask', 0.0)):,.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("ask_qty", 0))))
