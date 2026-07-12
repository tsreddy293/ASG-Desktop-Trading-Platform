from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import AIScannerPanelViewModel


class AIScannerPanel(QWidget):
    def __init__(self, viewmodel: AIScannerPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or AIScannerPanelViewModel()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Symbol", "Signal", "Confidence", "Time"])
        layout.addWidget(self.table)

        self._vm.scannerUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("symbol", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("signal", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("confidence", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("time", ""))))
