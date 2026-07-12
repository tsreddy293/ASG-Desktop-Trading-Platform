from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import WatchlistPanelViewModel


class WatchlistPanel(QWidget):
    def __init__(self, viewmodel: WatchlistPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or WatchlistPanelViewModel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel("Watchlist")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.list_widget = QListWidget(self)
        layout.addWidget(title)
        layout.addWidget(self.list_widget)

        self._vm.symbolsUpdated.connect(self._render)
        self._vm.refresh()

    def _render(self, rows: list[str]) -> None:
        self.list_widget.clear()
        self.list_widget.addItems(rows)
