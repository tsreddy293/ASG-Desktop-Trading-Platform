from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.market.adapters.base import LiveMarketRow
from src.market.market_data_service import MarketDataService
from src.core.translation import t
from src.ui.chart_window import ChartWindow
from src.ui.live_market_controller import LiveMarketController


class LiveMarketPage(QWidget):
    """Live market MVC view that renders only service-driven data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row_index_by_symbol: dict[str, int] = {}
        self._service = MarketDataService()
        self._controller = LiveMarketController(self._service, self)
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(int(self._service.refresh_interval_seconds * 1000))
        self._timer.timeout.connect(self._controller.refresh)
        self._timer.start()
        self._controller.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel(t("live_market.title"))
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")

        self.exchange_selector = QComboBox()
        self.exchange_selector.addItems(["NSE", "BSE"])
        self.exchange_selector.setCurrentText(self._service.get_exchange())
        self.exchange_selector.currentTextChanged.connect(lambda _: self._controller.refresh())

        self.symbol_search = QLineEdit()
        self.symbol_search.setPlaceholderText(t("live_market.search_placeholder"))
        self.symbol_search.textChanged.connect(lambda _: self._controller.refresh())

        self.refresh_button = QPushButton(t("live_market.refresh"))
        self.refresh_button.setStyleSheet(
            "background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 8px 12px;"
        )
        self.refresh_button.clicked.connect(self._controller.refresh)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel(t("live_market.exchange")))
        header_layout.addWidget(self.exchange_selector)
        header_layout.addWidget(self.symbol_search)
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        state_layout = QHBoxLayout()
        self.loading_label = QLabel(t("live_market.loading_idle"))
        self.loading_label.setStyleSheet("color: #94a3b8;")
        self.reconnect_label = QLabel(t("live_market.connection_connected"))
        self.reconnect_label.setStyleSheet("color: #22c55e;")
        self.last_updated_label = QLabel(t("live_market.last_updated", value="--"))
        self.last_updated_label.setStyleSheet("color: #94a3b8;")
        state_layout.addWidget(self.loading_label)
        state_layout.addSpacing(16)
        state_layout.addWidget(self.reconnect_label)
        state_layout.addStretch()
        state_layout.addWidget(self.last_updated_label)
        layout.addLayout(state_layout)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                t("live_market.col.symbol"),
                t("live_market.col.company"),
                t("live_market.col.ltp"),
                t("live_market.col.open"),
                t("live_market.col.close"),
                t("live_market.col.bid"),
                t("live_market.col.ask"),
                t("live_market.col.change"),
                t("live_market.col.volume"),
                t("live_market.col.high"),
                t("live_market.col.low"),
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
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._open_chart_from_row)
        layout.addWidget(self.table)

    def selected_exchange(self) -> str:
        return self.exchange_selector.currentText()

    def search_text(self) -> str:
        return self.symbol_search.text()

    def has_rows(self) -> bool:
        return bool(self._row_index_by_symbol)

    def replace_rows(self, rows: list[LiveMarketRow]) -> None:
        self.table.setRowCount(0)
        self._row_index_by_symbol.clear()
        for row in rows:
            self._append_row(row)

    def patch_rows(self, rows: list[LiveMarketRow], changed_symbols: list[str]) -> None:
        row_map = {row.symbol: row for row in rows}
        for symbol in changed_symbols:
            row = row_map.get(symbol)
            if row is None:
                continue
            if symbol not in self._row_index_by_symbol:
                self._append_row(row)
            else:
                self._write_row(self._row_index_by_symbol[symbol], row)

    def remove_rows(self, removed_symbols: list[str]) -> None:
        for symbol in removed_symbols:
            if symbol not in self._row_index_by_symbol:
                continue
            index = self._row_index_by_symbol[symbol]
            self.table.removeRow(index)
            self._reindex_rows()

    def set_loading_state(self, is_loading: bool) -> None:
        self.loading_label.setText(t("live_market.loading_fetching") if is_loading else t("live_market.loading_idle"))
        self.loading_label.setStyleSheet("color: #f59e0b;" if is_loading else "color: #94a3b8;")

    def set_reconnect_state(self, reconnecting: bool, error: str | None) -> None:
        if reconnecting:
            message = error or t("live_market.connection_reconnecting")
            self.reconnect_label.setText(message)
            self.reconnect_label.setStyleSheet("color: #ef4444;")
        else:
            self.reconnect_label.setText(t("live_market.connection_connected"))
            self.reconnect_label.setStyleSheet("color: #22c55e;")

    def set_last_updated(self, timestamp: datetime | None) -> None:
        display = LiveMarketController.format_timestamp(timestamp)
        self.last_updated_label.setText(t("live_market.last_updated", value=display))

    def _append_row(self, row: LiveMarketRow) -> None:
        index = self.table.rowCount()
        self.table.insertRow(index)
        self._row_index_by_symbol[row.symbol] = index
        self._write_row(index, row)

    def _write_row(self, row_index: int, row: LiveMarketRow) -> None:
        self.table.setItem(row_index, 0, QTableWidgetItem(row.symbol))
        self.table.setItem(row_index, 1, QTableWidgetItem(row.company))
        self.table.setItem(row_index, 2, QTableWidgetItem(f"{row.ltp:,.2f}"))
        self.table.setItem(row_index, 3, QTableWidgetItem(f"{row.open:,.2f}"))
        self.table.setItem(row_index, 4, QTableWidgetItem(f"{row.close:,.2f}"))
        self.table.setItem(row_index, 5, QTableWidgetItem(f"{row.bid:,.2f}"))
        self.table.setItem(row_index, 6, QTableWidgetItem(f"{row.ask:,.2f}"))
        self.table.setItem(row_index, 7, QTableWidgetItem(f"{row.change_percent:+.2f}%"))
        self.table.setItem(row_index, 8, QTableWidgetItem(f"{row.volume:,}"))
        self.table.setItem(row_index, 9, QTableWidgetItem(f"{row.high:,.2f}"))
        self.table.setItem(row_index, 10, QTableWidgetItem(f"{row.low:,.2f}"))

        if row.change_percent > 0:
            self.table.item(row_index, 7).setForeground(Qt.GlobalColor.green)
        elif row.change_percent < 0:
            self.table.item(row_index, 7).setForeground(Qt.GlobalColor.red)
        else:
            self.table.item(row_index, 7).setForeground(Qt.GlobalColor.white)

    def _reindex_rows(self) -> None:
        self._row_index_by_symbol = {}
        for row_index in range(self.table.rowCount()):
            symbol_item = self.table.item(row_index, 0)
            if symbol_item is not None:
                self._row_index_by_symbol[symbol_item.text()] = row_index

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        symbol_item = self.table.item(row, 0)
        if symbol_item is None:
            return
        symbol = symbol_item.text()
        menu = QMenu(self)
        chart_action = menu.addAction(t("live_market.ctx.open_chart"))
        alert_action = menu.addAction(t("live_market.ctx.set_alert"))
        action = menu.exec(self.table.mapToGlobal(position))
        if action == chart_action:
            self._open_chart(symbol)
        elif action == alert_action:
            QMessageBox.information(self, t("alert.title"), t("alert.configured", symbol=symbol))

    def _open_chart_from_row(self, row: int, column: int) -> None:
        symbol_item = self.table.item(row, 0)
        if symbol_item is not None:
            main_window = self.window()
            if hasattr(main_window, "open_ai_analysis"):
                main_window.open_ai_analysis(symbol_item.text(), self.selected_exchange())
            else:
                self._open_chart(symbol_item.text())

    def _open_chart(self, symbol: str) -> None:
        chart_window = ChartWindow(symbol, self)
        chart_window.exec()
