from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import HoldingsPanelViewModel


class HoldingsPanel(QWidget):
    def __init__(self, viewmodel: HoldingsPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or HoldingsPanelViewModel()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Symbol", "Qty", "Avg", "LTP"])
        layout.addWidget(self.table)

        self._vm.holdingsUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("symbol", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("qty", 0))))
            self.table.setItem(i, 2, QTableWidgetItem(f"{float(row.get('avg', 0.0)):,.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{float(row.get('ltp', 0.0)):,.2f}"))
