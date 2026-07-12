from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class NavigationMenu(QWidget):
    """Professional left-side navigation panel."""

    page_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("navigation_menu")
        self.menu_items = [
            ("route.dashboard", "Dashboard"),
            ("route.market_workspace", "Market Workspace"),
            ("route.market_watch", "Market Watch"),
            ("route.watchlist", "Watchlist"),
            ("route.scanner", "Scanner"),
            ("route.charts", "Charts"),
            ("route.orders", "Orders"),
            ("route.positions", "Positions"),
            ("route.holdings", "Holdings"),
            ("route.portfolio", "Portfolio"),
            ("route.strategy", "Strategy"),
            ("route.settings", "Settings"),
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.menu_tree = QTreeWidget()
        self.menu_tree.setHeaderHidden(True)
        self.menu_tree.setAlternatingRowColors(True)
        self.menu_tree.setIndentation(16)
        self.menu_tree.setExpandsOnDoubleClick(False)
        self.menu_tree.setStyleSheet(
            "QTreeWidget { background: #111827; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; }"
            "QTreeWidget::item { padding: 8px 10px; border-radius: 6px; }"
            "QTreeWidget::item:selected { background: #38bdf8; color: #0f172a; }"
        )

        for route, label in self.menu_items:
            item = QTreeWidgetItem([label])
            item.setData(0, 1, route)
            self.menu_tree.addTopLevelItem(item)

        self.menu_tree.setCurrentItem(self.menu_tree.topLevelItem(0))

        self.menu_tree.itemSelectionChanged.connect(self._notify_selection)
        layout.addWidget(self.menu_tree)

    def _notify_selection(self) -> None:
        selected_items = self.menu_tree.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        route = item.data(0, 1)
        if route:
            self.page_selected.emit(route)

    def update_translations(self) -> None:
        return
