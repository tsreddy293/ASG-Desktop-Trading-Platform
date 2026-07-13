from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
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

from src.market.market_data_service import MarketDataService
from src.core.translation import t


class OptionChainPage(QWidget):
    """Option chain page with modular service-backed dummy data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = MarketDataService()
        self._build_ui()
        self._load_underlyings()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_data)
        self._timer.start()
        self.refresh_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel(t("option_chain.title"))
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        self.refresh_button = QPushButton(t("option_chain.refresh"))
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

        self.underlying_selector = QComboBox()
        self.underlying_selector.currentTextChanged.connect(self._on_underlying_changed)
        self.expiry_selector = QComboBox()
        self.expiry_selector.currentTextChanged.connect(lambda _: self.refresh_data())

        self.spot_price_value = QLabel("--")
        self.atm_strike_value = QLabel("--")
        self.pcr_value = QLabel("--")
        self.iv_value = QLabel("--")
        self.last_update_value = QLabel("--")

        self._style_value_label(self.spot_price_value)
        self._style_value_label(self.atm_strike_value)
        self._style_value_label(self.pcr_value)
        self._style_value_label(self.iv_value)
        self._style_value_label(self.last_update_value)

        context_layout.addWidget(QLabel(t("option_chain.underlying")), 0, 0)
        context_layout.addWidget(self.underlying_selector, 0, 1)
        context_layout.addWidget(QLabel(t("option_chain.expiry")), 0, 2)
        context_layout.addWidget(self.expiry_selector, 0, 3)
        context_layout.addWidget(QLabel(t("option_chain.spot_price")), 1, 0)
        context_layout.addWidget(self.spot_price_value, 1, 1)
        context_layout.addWidget(QLabel(t("option_chain.atm_strike")), 1, 2)
        context_layout.addWidget(self.atm_strike_value, 1, 3)
        context_layout.addWidget(QLabel(t("option_chain.pcr")), 2, 0)
        context_layout.addWidget(self.pcr_value, 2, 1)
        context_layout.addWidget(QLabel(t("option_chain.iv")), 2, 2)
        context_layout.addWidget(self.iv_value, 2, 3)
        context_layout.addWidget(QLabel(t("option_chain.last_update")), 3, 0)
        context_layout.addWidget(self.last_update_value, 3, 1)

        layout.addWidget(context_panel)

        self.table = QTableWidget(0, 17)
        self.table.setHorizontalHeaderLabels(
            [
                t("option_chain.col.strike"),
                t("option_chain.col.ce_ltp"),
                t("option_chain.col.ce_oi"),
                t("option_chain.col.ce_chg_oi"),
                t("option_chain.col.pe_oi"),
                t("option_chain.col.pe_chg_oi"),
                t("option_chain.col.pe_ltp"),
                t("option_chain.iv"),
                t("option_chain.pcr"),
                "CE Bid",
                "CE Ask",
                "CE Vol",
                "PE Bid",
                "PE Ask",
                "PE Vol",
                "CE Delta",
                "PE Delta",
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
        layout.addWidget(self.table)

    def refresh_data(self) -> None:
        underlying = self.underlying_selector.currentText() or "NIFTY"
        expiry = self.expiry_selector.currentText() or ""
        snapshot = self._service.get_option_chain_snapshot(underlying, expiry)

        if snapshot.expiries and not self.expiry_selector.currentText():
            self._load_expiries(underlying)
            expiry = self.expiry_selector.currentText() or (snapshot.expiries[0] if snapshot.expiries else "")
            snapshot = self._service.get_option_chain_snapshot(underlying, expiry)

        self.spot_price_value.setText(f"{snapshot.spot_price:,.2f}")
        self.atm_strike_value.setText(f"{snapshot.atm_strike:,}")
        self.pcr_value.setText(f"{snapshot.pcr:.2f}")
        self.iv_value.setText(f"{snapshot.iv:.1f}%")
        self.last_update_value.setText(self._format_time(snapshot.last_updated))

        self.table.setRowCount(len(snapshot.rows))
        for row_index, row in enumerate(snapshot.rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(f"{row.strike_price:,.0f}"))
            self.table.setItem(row_index, 1, QTableWidgetItem(f"{row.ce_ltp:,.2f}"))
            self.table.setItem(row_index, 2, QTableWidgetItem(f"{row.ce_oi:,}"))
            self.table.setItem(row_index, 3, QTableWidgetItem(f"{row.ce_change_oi:+,}"))
            self.table.setItem(row_index, 4, QTableWidgetItem(f"{row.pe_oi:,}"))
            self.table.setItem(row_index, 5, QTableWidgetItem(f"{row.pe_change_oi:+,}"))
            self.table.setItem(row_index, 6, QTableWidgetItem(f"{row.pe_ltp:,.2f}"))
            self.table.setItem(row_index, 7, QTableWidgetItem(f"{row.iv:.2f}%"))
            self.table.setItem(row_index, 8, QTableWidgetItem(f"{row.pcr:.2f}"))
            self.table.setItem(row_index, 9, QTableWidgetItem(f"{row.ce_bid:,.2f}"))
            self.table.setItem(row_index, 10, QTableWidgetItem(f"{row.ce_ask:,.2f}"))
            self.table.setItem(row_index, 11, QTableWidgetItem(f"{row.ce_volume:,}"))
            self.table.setItem(row_index, 12, QTableWidgetItem(f"{row.pe_bid:,.2f}"))
            self.table.setItem(row_index, 13, QTableWidgetItem(f"{row.pe_ask:,.2f}"))
            self.table.setItem(row_index, 14, QTableWidgetItem(f"{row.pe_volume:,}"))
            self.table.setItem(row_index, 15, QTableWidgetItem(f"{row.ce_delta:.4f}"))
            self.table.setItem(row_index, 16, QTableWidgetItem(f"{row.pe_delta:.4f}"))

            if row.strike_price == snapshot.atm_strike:
                for column in range(self.table.columnCount()):
                    self.table.item(row_index, column).setBackground(Qt.GlobalColor.darkCyan)

    def _load_underlyings(self) -> None:
        underlyings = self._service.get_option_chain_underlyings()
        self.underlying_selector.clear()
        self.underlying_selector.addItems(underlyings)
        self._load_expiries(underlyings[0] if underlyings else "NIFTY")

    def _load_expiries(self, underlying: str) -> None:
        expiries = self._service.get_option_chain_expiries(underlying)
        self.expiry_selector.blockSignals(True)
        self.expiry_selector.clear()
        self.expiry_selector.addItems(expiries)
        self.expiry_selector.blockSignals(False)

    def _on_underlying_changed(self, underlying: str) -> None:
        self._load_expiries(underlying)
        self.refresh_data()

    @staticmethod
    def _style_value_label(label: QLabel) -> None:
        label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")

    @staticmethod
    def _format_time(timestamp: datetime) -> str:
        return timestamp.astimezone().strftime("%H:%M:%S")
