from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.market_watch.models import MarketWatchState
from src.ui.market_watch.view_model import MarketWatchViewModel
from src.ui.market_watch.widgets import MarketDepthPanel, QuoteDetailsDialog


class MarketWatchPage(QWidget):
    """Professional Market Watch workspace backed by MarketDataService only."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = MarketWatchViewModel()
        self._selected_symbol: str | None = None
        self._build_ui()
        self._wire_events()
        self._view_model.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("Market Watch")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Symbol")
        self.search_input.setFixedWidth(220)

        self.add_button = QPushButton("Add Symbol")
        self.remove_button = QPushButton("Remove Symbol")
        self.pin_button = QPushButton("Pin Symbol")
        self.refresh_button = QPushButton("Refresh")
        self.auto_refresh = QCheckBox("Auto Refresh 2s")
        self.auto_refresh.setChecked(True)

        self.refresh_button.setStyleSheet(
            "background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 8px 12px;"
        )

        self.connection_label = QLabel("Disconnected")
        self.connection_label.setStyleSheet("color: #ef4444; font-weight: 700;")
        self.last_updated_label = QLabel("Last Updated: --")
        self.last_updated_label.setStyleSheet("color: #94a3b8;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(self.add_button)
        header_layout.addWidget(self.remove_button)
        header_layout.addWidget(self.pin_button)
        header_layout.addWidget(self.auto_refresh)
        header_layout.addWidget(self.connection_label)
        header_layout.addWidget(self.last_updated_label)
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Symbol",
                "LTP",
                "Change",
                "Change %",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Pinned",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet(
            "QTableWidget { background: #111827; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }"
            "QHeaderView::section { background: #1f2937; color: #f8fafc; padding: 8px; border: 1px solid #334155; }"
            "QTableWidget::item:selected { background: #38bdf8; color: #0f172a; }"
        )
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)

        self.depth_panel = MarketDepthPanel(self)

        splitter.addWidget(self.table)
        splitter.addWidget(self.depth_panel)
        splitter.setSizes([920, 360])
        layout.addWidget(splitter)

    def _wire_events(self) -> None:
        self.search_input.textChanged.connect(self._on_search_changed)
        self.add_button.clicked.connect(self._on_add_symbol)
        self.remove_button.clicked.connect(self._on_remove_symbol)
        self.pin_button.clicked.connect(self._on_pin_symbol)
        self.refresh_button.clicked.connect(self._view_model.refresh)
        self.auto_refresh.toggled.connect(self._view_model.set_auto_refresh)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._open_quote_details)
        self.table.customContextMenuRequested.connect(self._open_context_menu)

        self._view_model.state_changed.connect(self._on_state_changed)
        self._view_model.symbols_changed.connect(lambda _symbols: None)

    def refresh_data(self) -> None:
        self._view_model.refresh()

    def _on_search_changed(self, value: str) -> None:
        self._view_model.set_search_text(value)
        self._view_model.refresh()

    def _on_add_symbol(self) -> None:
        symbol, ok = QInputDialog.getText(self, "Add Symbol", "Enter symbol")
        if ok and symbol.strip():
            self._view_model.add_symbol(symbol)
            self._view_model.refresh()

    def _on_remove_symbol(self) -> None:
        symbol = self._selected_symbol
        if not symbol:
            QMessageBox.information(self, "Remove Symbol", "Select a symbol to remove")
            return
        self._view_model.remove_symbol(symbol)
        self._view_model.refresh()

    def _on_pin_symbol(self) -> None:
        symbol = self._selected_symbol
        if not symbol:
            QMessageBox.information(self, "Pin Symbol", "Select a symbol to pin")
            return
        self._view_model.toggle_pin(symbol)
        self._view_model.refresh()

    def _on_selection_changed(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        symbol_item = self.table.item(row, 0)
        if symbol_item is None:
            return
        symbol = symbol_item.text().strip().upper()
        self._selected_symbol = symbol
        self._view_model.set_selected_symbol(symbol)
        self._view_model.refresh()

    def _open_quote_details(self, item: QTableWidgetItem) -> None:
        row = item.row()
        symbol_item = self.table.item(row, 0)
        if symbol_item is None:
            return
        details = self._view_model.quote_details(symbol_item.text())
        QuoteDetailsDialog(details, self).exec()

    def _open_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        symbol_item = self.table.item(row, 0)
        if symbol_item is None:
            return
        symbol = symbol_item.text().strip().upper()

        menu = QMenu(self)
        pin_action = menu.addAction("Pin/Unpin")
        remove_action = menu.addAction("Remove")
        details_action = menu.addAction("Quote Details")
        action = menu.exec(self.table.mapToGlobal(position))

        if action == pin_action:
            self._view_model.toggle_pin(symbol)
            self._view_model.refresh()
        elif action == remove_action:
            self._view_model.remove_symbol(symbol)
            self._view_model.refresh()
        elif action == details_action:
            QuoteDetailsDialog(self._view_model.quote_details(symbol), self).exec()

    def _on_state_changed(self, state: MarketWatchState) -> None:
        self.connection_label.setText("Connected" if state.connected else "Disconnected")
        self.connection_label.setStyleSheet("color: #22c55e; font-weight: 700;" if state.connected else "color: #ef4444; font-weight: 700;")
        self.last_updated_label.setText(f"Last Updated: {self._fmt_time(state.last_updated)}")

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(state.quotes))
        for row, quote in enumerate(state.quotes):
            self.table.setItem(row, 0, QTableWidgetItem(quote.symbol))
            self.table.setItem(row, 1, QTableWidgetItem(f"{quote.ltp:,.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{quote.change:+.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{quote.change_percent:+.2f}%"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{quote.open:,.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{quote.high:,.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{quote.low:,.2f}"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{quote.close:,.2f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{quote.volume:,}"))
            self.table.setItem(row, 9, QTableWidgetItem("Yes" if self._view_model.is_pinned(quote.symbol) else "No"))

            if quote.change_percent > 0:
                self.table.item(row, 3).setForeground(Qt.GlobalColor.green)
            elif quote.change_percent < 0:
                self.table.item(row, 3).setForeground(Qt.GlobalColor.red)

        self.table.setSortingEnabled(True)
        self.depth_panel.update_snapshot(state.depth)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._view_model.stop()
        super().closeEvent(event)

    @staticmethod
    def _fmt_time(value: datetime | None) -> str:
        if value is None:
            return "--"
        return value.astimezone().strftime("%H:%M:%S")
