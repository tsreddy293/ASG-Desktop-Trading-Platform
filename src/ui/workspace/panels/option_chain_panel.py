from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import OptionChainPanelViewModel


class OptionChainPanel(QWidget):
    def __init__(self, viewmodel: OptionChainPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or OptionChainPanelViewModel()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Strike", "CE LTP", "PE LTP", "PCR"])
        layout.addWidget(self.table)

        self._vm.chainUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("strike", 0))))
            self.table.setItem(i, 1, QTableWidgetItem(f"{float(row.get('ce_ltp', 0.0)):,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{float(row.get('pe_ltp', 0.0)):,.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{float(row.get('pcr', 0.0)):,.2f}"))
