from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.market.service import MarketWatchService
from src.core.translation import t


class MarketDepthPage(QWidget):
    """Market depth page showing top 5 buy and sell orders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = MarketWatchService()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_data)
        self._load_symbols()
        self._on_refresh_mode_changed(t("market_depth.mode.auto"))
        self.refresh_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel(t("market_depth.title"))
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        self.refresh_button = QPushButton(t("market_depth.refresh"))
        self.refresh_button.setStyleSheet(
            "background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 8px 12px;"
        )
        self.refresh_button.clicked.connect(self.refresh_data)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        context_panel = QFrame(self)
        context_panel.setStyleSheet(
            "QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }"
            "QLabel { color: #cbd5e1; }"
            "QComboBox { background: #0b1220; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; color: #f8fafc; }"
        )
        context_layout = QGridLayout(context_panel)
        context_layout.setContentsMargins(14, 12, 14, 12)
        context_layout.setHorizontalSpacing(20)
        context_layout.setVerticalSpacing(10)

        self.symbol_selector = QComboBox()
        self.symbol_selector.currentTextChanged.connect(lambda _: self.refresh_data())

        self.exchange_value = QLabel("--")
        self.ltp_value = QLabel("--")
        self.change_value = QLabel("--")
        self.bid_value = QLabel("--")
        self.ask_value = QLabel("--")
        self.spread_value = QLabel("--")
        self.volume_value = QLabel("--")
        self.last_update_value = QLabel("--")

        self.refresh_mode_selector = QComboBox()
        self.refresh_mode_selector.addItems([t("market_depth.mode.auto"), t("market_depth.mode.manual")])
        self.refresh_mode_selector.currentTextChanged.connect(self._on_refresh_mode_changed)

        for label in [
            self.exchange_value,
            self.ltp_value,
            self.change_value,
            self.bid_value,
            self.ask_value,
            self.spread_value,
            self.volume_value,
            self.last_update_value,
        ]:
            label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")

        context_layout.addWidget(QLabel(t("market_depth.stock")), 0, 0)
        context_layout.addWidget(self.symbol_selector, 0, 1)
        context_layout.addWidget(QLabel(t("market_depth.exchange")), 0, 2)
        context_layout.addWidget(self.exchange_value, 0, 3)
        context_layout.addWidget(QLabel(t("market_depth.ltp")), 1, 0)
        context_layout.addWidget(self.ltp_value, 1, 1)
        context_layout.addWidget(QLabel(t("market_depth.change")), 1, 2)
        context_layout.addWidget(self.change_value, 1, 3)
        context_layout.addWidget(QLabel(t("market_depth.bid")), 2, 0)
        context_layout.addWidget(self.bid_value, 2, 1)
        context_layout.addWidget(QLabel(t("market_depth.ask")), 2, 2)
        context_layout.addWidget(self.ask_value, 2, 3)
        context_layout.addWidget(QLabel(t("market_depth.spread")), 3, 0)
        context_layout.addWidget(self.spread_value, 3, 1)
        context_layout.addWidget(QLabel(t("market_depth.volume")), 3, 2)
        context_layout.addWidget(self.volume_value, 3, 3)
        context_layout.addWidget(QLabel(t("market_depth.last_update")), 4, 0)
        context_layout.addWidget(self.last_update_value, 4, 1)
        context_layout.addWidget(QLabel(t("market_depth.refresh_mode")), 4, 2)
        context_layout.addWidget(self.refresh_mode_selector, 4, 3)

        layout.addWidget(context_panel)

        tables_layout = QGridLayout()
        tables_layout.setHorizontalSpacing(12)

        buy_label = QLabel(t("market_depth.top_buy"))
        buy_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #cbd5e1;")
        sell_label = QLabel(t("market_depth.top_sell"))
        sell_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #cbd5e1;")

        self.buy_table = self._create_depth_table()
        self.sell_table = self._create_depth_table()

        tables_layout.addWidget(buy_label, 0, 0)
        tables_layout.addWidget(sell_label, 0, 1)
        tables_layout.addWidget(self.buy_table, 1, 0)
        tables_layout.addWidget(self.sell_table, 1, 1)

        layout.addLayout(tables_layout)

    def _create_depth_table(self) -> QTableWidget:
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels([t("market_depth.col.price"), t("market_depth.col.quantity"), t("market_depth.col.orders")])
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setStyleSheet(
            "QTableWidget { background: #111827; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }"
            "QHeaderView::section { background: #1f2937; color: #f8fafc; padding: 8px; border: 1px solid #334155; }"
            "QTableWidget::item:selected { background: #38bdf8; color: #0f172a; }"
        )
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def refresh_data(self) -> None:
        symbol = self.symbol_selector.currentText() or "SBIN"
        snapshot = self._service.get_market_depth_snapshot(symbol, exchange="NSE")

        self.exchange_value.setText(snapshot.exchange)
        self.ltp_value.setText(f"{t('market_depth.currency_prefix')} {snapshot.ltp:,.2f}")
        self.change_value.setText(f"{snapshot.change_percent:+.2f}%")
        self.bid_value.setText(f"{t('market_depth.currency_prefix')} {snapshot.bid:,.2f}")
        self.ask_value.setText(f"{t('market_depth.currency_prefix')} {snapshot.ask:,.2f}")
        self.spread_value.setText(f"{t('market_depth.currency_prefix')} {snapshot.spread:,.2f}")
        self.volume_value.setText(self._format_volume(snapshot.volume))
        self.last_update_value.setText(self._format_time(snapshot.last_updated))

        self._populate_orders(self.buy_table, snapshot.buy_orders)
        self._populate_orders(self.sell_table, snapshot.sell_orders)

    def _load_symbols(self) -> None:
        symbols = self._service.get_market_depth_symbols()
        self.symbol_selector.clear()
        self.symbol_selector.addItems(symbols)

    def _on_refresh_mode_changed(self, mode: str) -> None:
        if mode == t("market_depth.mode.auto"):
            self._timer.start()
        else:
            self._timer.stop()

    @staticmethod
    def _populate_orders(table: QTableWidget, orders) -> None:
        table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            table.setItem(row, 0, QTableWidgetItem(f"{order.price:,.2f}"))
            table.setItem(row, 1, QTableWidgetItem(f"{order.quantity:,}"))
            table.setItem(row, 2, QTableWidgetItem(f"{order.orders}"))

    @staticmethod
    def _format_volume(volume: int) -> str:
        return f"{volume / 1_000_000:.1f}M"

    @staticmethod
    def _format_time(timestamp: datetime) -> str:
        return timestamp.astimezone().strftime("%H:%M:%S")
