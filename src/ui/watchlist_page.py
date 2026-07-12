from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.market.watchlist_service import WatchListService
from src.ui.live_quote_panel import LiveQuotePanel
from src.ui.viewmodels.dashboard_view_model import DashboardViewModel


class WatchListPage(QWidget):
    """Watch list page with DB management and live prices via MarketDataService."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = DashboardViewModel()
        self._service = WatchListService()
        self._build_ui()
        self._load_data()
        self._timer = QTimer(self)
        self._timer.setInterval(self._view_model.refresh_seconds * 1000)
        self._timer.timeout.connect(self._load_data)
        self._timer.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Watchlist")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.search_box = QComboBox()
        self.search_box.setEditable(True)
        self.search_box.setInsertPolicy(QComboBox.NoInsert)
        self.search_box.setPlaceholderText("Search symbol or company")
        self.search_box.setMinimumWidth(320)
        self.search_box.lineEdit().textChanged.connect(self._filter_rows)
        self.search_box.setCompleter(QCompleter([]))
        controls.addWidget(self.search_box)

        self.add_button = QPushButton("Add Stock")
        self.add_button.clicked.connect(self._add_stock)
        self.add_button.setStyleSheet("background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 8px 12px;")
        controls.addWidget(self.add_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_data)
        self.refresh_button.setStyleSheet("background: #0ea5e9; color: #082f49; border-radius: 6px; padding: 8px 12px;")
        controls.addWidget(self.refresh_button)

        self.connection_label = QLabel("Connecting...")
        self.connection_label.setStyleSheet("color: #f59e0b;")
        controls.addWidget(self.connection_label)
        controls.addStretch()

        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        table_panel = QFrame()
        table_panel.setStyleSheet("QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(10, 10, 10, 10)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Symbol",
                "Company",
                "Exchange",
                "Live Price",
                "Change %",
                "Volume",
                "AI Rating",
                "Risk",
                "Favorite",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet(
            "QTableWidget { background: #111827; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }"
            "QHeaderView::section { background: #1f2937; color: #f8fafc; padding: 8px; border: 1px solid #334155; }"
            "QTableWidget::item:selected { background: #38bdf8; color: #0f172a; }"
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellClicked.connect(self._handle_favorite_click)
        table_layout.addWidget(self.table)

        self.live_quote_panel = LiveQuotePanel(self._view_model.get_quote, self)

        splitter.addWidget(table_panel)
        splitter.addWidget(self.live_quote_panel)
        splitter.setSizes([920, 340])
        layout.addWidget(splitter)

    def _load_data(self) -> None:
        entries = self._service.list_entries()
        symbols = [entry.symbol for entry in entries]
        quote_rows = self._view_model.get_quotes(symbols)
        quote_by_symbol = {str(row.get("symbol", "")).upper(): row for row in quote_rows}

        self.connection_label.setText("Connected" if quote_rows else "Session unavailable")
        self.connection_label.setStyleSheet("color: #22c55e;" if quote_rows else "color: #ef4444;")

        self._populate_table(entries, quote_by_symbol)
        self._populate_autocomplete(entries)

    def _populate_table(self, entries: list, quote_by_symbol: dict[str, dict]) -> None:
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            quote = quote_by_symbol.get(entry.symbol.upper(), {})
            live_price = float(quote.get("ltp", entry.live_price) or entry.live_price)
            change_percent = float(quote.get("change_percent", 0.0) or 0.0)
            volume = int(quote.get("volume", 0) or 0)

            self.table.setItem(row, 0, QTableWidgetItem(entry.symbol))
            self.table.setItem(row, 1, QTableWidgetItem(entry.company))
            self.table.setItem(row, 2, QTableWidgetItem(entry.exchange))
            self.table.setItem(row, 3, QTableWidgetItem(f"{live_price:,.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{change_percent:+.2f}%"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{volume:,}"))
            self.table.setItem(row, 6, QTableWidgetItem(entry.ai_rating))
            self.table.setItem(row, 7, QTableWidgetItem(entry.risk))

            favorite_item = QTableWidgetItem("★" if entry.favorite else "☆")
            favorite_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            favorite_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            self.table.setItem(row, 8, favorite_item)
            self.table.item(row, 8).setFlags(self.table.item(row, 8).flags() | Qt.ItemFlag.ItemIsSelectable)
            self.table.item(row, 8).setToolTip("Toggle favorite")

            if change_percent > 0:
                self.table.item(row, 4).setForeground(Qt.GlobalColor.green)
            elif change_percent < 0:
                self.table.item(row, 4).setForeground(Qt.GlobalColor.red)

            self.table.item(row, 8).setForeground(Qt.GlobalColor.yellow if entry.favorite else Qt.GlobalColor.white)

    def _populate_autocomplete(self, entries: list) -> None:
        self.search_box.clear()
        values = sorted(set(self._service.get_suggestions()) | {entry.symbol for entry in entries} | {entry.company for entry in entries})
        self.search_box.addItems(values)
        completer = QCompleter(values)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_box.setCompleter(completer)

    def _filter_rows(self, query: str) -> None:
        if not query:
            self._load_data()
            return
        entries = self._service.search(query)
        self._populate_table(entries)

    def _add_stock(self) -> None:
        query = self.search_box.currentText().strip()
        if not query:
            QMessageBox.information(self, "Watchlist", "Enter symbol or company name")
            return
        symbol, company = self._service.resolve_selection(query)
        entry = self._service.add_symbol(symbol, company, 'NSE', 0.0, 'Neutral')
        QMessageBox.information(self, "Watchlist", f"Added {entry.symbol}")
        self._load_data()

    def _delete_entry(self, entry_id: int) -> None:
        self._service.delete_entry(entry_id)
        self._load_data()

    def _handle_favorite_click(self, row: int, column: int) -> None:
        if column != 8:
            return
        item = self.table.item(row, column)
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        self._service.toggle_favorite(entry_id)
        self._load_data()
