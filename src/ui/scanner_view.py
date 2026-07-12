from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
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
    QComboBox,
)

from src.scanner.model import ScannerFilters, ScannerRow, ScannerSummary
from src.core.translation import t
from src.ui.chart_window import ChartWindow


class ScannerView(QWidget):
    """Professional institutional-style AI Scanner view."""

    scan_requested = Signal()
    row_open_requested = Signal(str)
    context_action_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(t("scanner.title"))
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        filter_panel = QFrame(self)
        filter_panel.setStyleSheet(
            "QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }"
            "QLabel { color: #cbd5e1; }"
            "QComboBox, QLineEdit { background: #0b1220; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; color: #f8fafc; }"
        )
        filter_layout = QGridLayout(filter_panel)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setHorizontalSpacing(14)
        filter_layout.setVerticalSpacing(10)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["NSE", "BSE"])

        self.segment_combo = QComboBox()
        self.segment_combo.addItems(["Cash", "F&O"])

        self.market_cap_combo = QComboBox()
        self.market_cap_combo.addItems(["All", "Large Cap", "Mid Cap", "Small Cap"])

        self.sector_combo = QComboBox()
        self.sector_combo.addItems(["All", "Banking", "IT", "Energy", "FMCG", "Infrastructure", "Financial Services"])

        self.min_volume_input = QLineEdit("0")
        self.min_price_input = QLineEdit("0")
        self.max_price_input = QLineEdit("100000")

        self.scanner_button_group = QButtonGroup(self)
        scanner_button_layout = QHBoxLayout()
        scanner_button_layout.setContentsMargins(0, 0, 0, 0)
        scanner_button_layout.setSpacing(8)
        self.scanner_buttons: dict[str, QPushButton] = {}
        for scanner_name in ["Intraday", "Swing", "Delivery"]:
            button = QPushButton(scanner_name)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { background: #1f2937; color: #cbd5e1; border-radius: 6px; padding: 6px 10px; border: 1px solid #334155; }"
                "QPushButton:checked { background: #38bdf8; color: #0f172a; border: 1px solid #38bdf8; }"
            )
            self.scanner_button_group.addButton(button)
            scanner_button_layout.addWidget(button)
            self.scanner_buttons[scanner_name] = button
        self.scanner_buttons["Intraday"].setChecked(True)

        self.refresh_button = QPushButton(t("scanner.refresh"))
        self.refresh_button.setStyleSheet("background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 8px 12px;")
        self.refresh_button.clicked.connect(self.scan_requested.emit)

        filter_layout.addWidget(QLabel(t("scanner.exchange")), 0, 0)
        filter_layout.addWidget(self.exchange_combo, 0, 1)
        filter_layout.addWidget(QLabel(t("scanner.segment")), 0, 2)
        filter_layout.addWidget(self.segment_combo, 0, 3)
        filter_layout.addWidget(QLabel(t("scanner.scanner")), 0, 4)
        filter_layout.addLayout(scanner_button_layout, 0, 5, 1, 2)

        filter_layout.addWidget(QLabel(t("scanner.market_cap")), 1, 0)
        filter_layout.addWidget(self.market_cap_combo, 1, 1)
        filter_layout.addWidget(QLabel(t("scanner.sector")), 1, 2)
        filter_layout.addWidget(self.sector_combo, 1, 3)
        filter_layout.addWidget(QLabel(t("scanner.min_volume")), 1, 4)
        filter_layout.addWidget(self.min_volume_input, 1, 5)

        filter_layout.addWidget(QLabel(t("scanner.min_price")), 2, 0)
        filter_layout.addWidget(self.min_price_input, 2, 1)
        filter_layout.addWidget(QLabel(t("scanner.max_price")), 2, 2)
        filter_layout.addWidget(self.max_price_input, 2, 3)
        filter_layout.addWidget(self.refresh_button, 2, 6)

        layout.addWidget(filter_panel)

        self.table = QTableWidget(0, 17)
        self.table.setHorizontalHeaderLabels([
            t("scanner.col.symbol"),
            t("scanner.col.company"),
            t("scanner.col.sector"),
            t("scanner.col.ltp"),
            t("scanner.col.change"),
            t("scanner.col.volume"),
            t("scanner.col.delivery"),
            t("scanner.col.rsi"),
            t("scanner.col.macd"),
            t("scanner.col.ema_trend"),
            t("scanner.col.vwap_position"),
            t("scanner.col.ai_score"),
            t("scanner.col.signal"),
            t("scanner.col.confidence"),
            t("scanner.col.risk"),
            t("scanner.col.target"),
            t("scanner.col.stop_loss"),
        ])
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemDoubleClicked.connect(self._open_selected_chart)
        self.table.setStyleSheet(
            "QTableWidget { background: #111827; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }"
            "QHeaderView::section { background: #1f2937; color: #f8fafc; padding: 7px; border: 1px solid #334155; }"
            "QTableWidget::item:selected { background: #38bdf8; color: #0f172a; }"
        )
        layout.addWidget(self.table)

        status_panel = QFrame(self)
        status_panel.setStyleSheet("QFrame { background: #0b1220; border: 1px solid #334155; border-radius: 8px; }")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(10, 8, 10, 8)

        self.stocks_scanned_label = QLabel(t("scanner.status.scanned", value=0))
        self.stocks_qualified_label = QLabel(t("scanner.status.qualified", value=0))
        self.scan_time_label = QLabel(t("scanner.status.scan_time", value="0.000s"))
        self.last_updated_label = QLabel(t("scanner.status.last_updated", value="--"))
        for lbl in [self.stocks_scanned_label, self.stocks_qualified_label, self.scan_time_label, self.last_updated_label]:
            lbl.setStyleSheet("color: #94a3b8;")
            status_layout.addWidget(lbl)
            status_layout.addSpacing(12)
        status_layout.addStretch()

        layout.addWidget(status_panel)

    def current_filters(self) -> ScannerFilters:
        scanner_mode = "Intraday"
        for name, button in self.scanner_buttons.items():
            if button.isChecked():
                scanner_mode = name
                break

        return ScannerFilters(
            exchange=self.exchange_combo.currentText(),
            segment=self.segment_combo.currentText(),
            scanner=scanner_mode,
            market_cap=self.market_cap_combo.currentText(),
            sector=self.sector_combo.currentText(),
            minimum_volume=self._to_int(self.min_volume_input.text(), 0),
            minimum_price=self._to_float(self.min_price_input.text(), 0.0),
            maximum_price=self._to_float(self.max_price_input.text(), 100000.0),
        )

    def populate_results(self, rows: list[ScannerRow]) -> None:
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._set_item(row_index, 0, row.symbol)
            self._set_item(row_index, 1, row.company)
            self._set_item(row_index, 2, row.sector)
            self._set_numeric_item(row_index, 3, row.ltp, f"{row.ltp:,.2f}")
            self._set_numeric_item(row_index, 4, row.change_percent, f"{row.change_percent:+.2f}%")
            self._set_numeric_item(row_index, 5, row.volume, f"{row.volume:,}")
            self._set_numeric_item(row_index, 6, row.delivery_percent, f"{row.delivery_percent:.1f}%")
            self._set_numeric_item(row_index, 7, row.rsi, f"{row.rsi:.1f}")
            self._set_numeric_item(row_index, 8, row.macd, f"{row.macd:+.2f}")
            self._set_item(row_index, 9, row.ema_trend)
            self._set_item(row_index, 10, row.vwap_position)
            self._set_numeric_item(row_index, 11, row.ai_score, f"{row.ai_score}")
            translated_signal = self._translate_signal(row.signal)
            self._set_item(row_index, 12, translated_signal)
            self._set_numeric_item(row_index, 13, row.confidence_percent, f"{row.confidence_percent:.1f}%")
            self._set_item(row_index, 14, row.risk)
            self._set_numeric_item(row_index, 15, row.target, f"{row.target:,.2f}")
            self._set_numeric_item(row_index, 16, row.stop_loss, f"{row.stop_loss:,.2f}")

            signal_item = self.table.item(row_index, 12)
            if row.signal in {"BUY", "STRONG BUY"}:
                signal_item.setForeground(Qt.GlobalColor.green)
            elif row.signal in {"SELL", "STRONG SELL"}:
                signal_item.setForeground(Qt.GlobalColor.red)
            else:
                signal_item.setForeground(Qt.GlobalColor.yellow)

            self.table.item(row_index, 0).setData(Qt.ItemDataRole.UserRole, row.symbol)

    def update_scan_status(self, summary: ScannerSummary) -> None:
        self.stocks_scanned_label.setText(t("scanner.status.scanned", value=summary.stocks_scanned))
        self.stocks_qualified_label.setText(t("scanner.status.qualified", value=summary.stocks_qualified))
        self.scan_time_label.setText(t("scanner.status.scan_time", value=f"{summary.scan_time_seconds:.3f}s"))
        self.last_updated_label.setText(t("scanner.status.last_updated", value=self._format_time(summary.last_updated)))

    def open_chart(self, symbol: str) -> None:
        chart = ChartWindow(symbol, self)
        chart.exec()

    def show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)

    def _open_selected_chart(self, item: QTableWidgetItem) -> None:
        symbol_item = self.table.item(item.row(), 0)
        if symbol_item is None:
            return
        symbol = symbol_item.data(Qt.ItemDataRole.UserRole) or symbol_item.text()
        self.row_open_requested.emit(symbol)

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        symbol_item = self.table.item(row, 0)
        if symbol_item is None:
            return
        symbol = symbol_item.data(Qt.ItemDataRole.UserRole) or symbol_item.text()

        menu = QMenu(self)
        actions = [
            t("scanner.ctx.add_watchlist"),
            t("scanner.ctx.open_chart"),
            t("scanner.ctx.ai_analysis"),
            t("scanner.ctx.market_depth"),
            t("scanner.ctx.option_chain"),
        ]
        action_map = {label: menu.addAction(label) for label in actions}
        selected = menu.exec(self.table.mapToGlobal(position))
        for label, action in action_map.items():
            if selected == action:
                self.context_action_requested.emit(label, symbol)
                return

    @staticmethod
    def _translate_signal(signal: str) -> str:
        key_map = {
            "STRONG BUY": "ai.signal.strong_buy",
            "BUY": "ai.signal.buy",
            "HOLD": "ai.signal.hold",
            "SELL": "ai.signal.sell",
            "STRONG SELL": "ai.signal.strong_sell",
            "NO DATA": "ai.signal.no_data",
        }
        return t(key_map.get(signal, "ai.signal.hold"))

    def _set_item(self, row: int, col: int, text: str) -> None:
        self.table.setItem(row, col, QTableWidgetItem(text))

    def _set_numeric_item(self, row: int, col: int, value: float | int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.EditRole, value)
        self.table.setItem(row, col, item)

    @staticmethod
    def _to_int(value: str, default: int) -> int:
        try:
            return int(float(value.strip() or default))
        except ValueError:
            return default

    @staticmethod
    def _to_float(value: str, default: float) -> float:
        try:
            return float(value.strip() or default)
        except ValueError:
            return default

    @staticmethod
    def _format_time(timestamp: datetime) -> str:
        return timestamp.astimezone().strftime("%H:%M:%S")
