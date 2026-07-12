from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QFrame, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from src.ui.market_watch.models import MarketDepthSnapshot, QuoteDetails


class QuoteDetailsDialog(QDialog):
    def __init__(self, details: QuoteDetails, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Quote Details - {details.symbol}")
        self.resize(420, 380)
        self.setStyleSheet(
            "QDialog { background: #0f172a; color: #f8fafc; }"
            "QLabel { color: #e2e8f0; }"
        )

        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("LTP", QLabel(self._fmt_float(details.ltp)))
        form.addRow("Open", QLabel(self._fmt_float(details.open)))
        form.addRow("High", QLabel(self._fmt_float(details.high)))
        form.addRow("Low", QLabel(self._fmt_float(details.low)))
        form.addRow("Close", QLabel(self._fmt_float(details.close)))
        form.addRow("Upper Circuit", QLabel(self._fmt_float(details.upper_circuit)))
        form.addRow("Lower Circuit", QLabel(self._fmt_float(details.lower_circuit)))
        form.addRow("52 Week High", QLabel(self._fmt_float(details.week_52_high)))
        form.addRow("52 Week Low", QLabel(self._fmt_float(details.week_52_low)))
        form.addRow("Volume", QLabel(self._fmt_int(details.volume)))
        form.addRow("Bid", QLabel(self._fmt_float(details.bid)))
        form.addRow("Ask", QLabel(self._fmt_float(details.ask)))
        form.addRow("Last Trade Time", QLabel(self._fmt_time(details.last_trade_time)))

        layout.addLayout(form)

    @staticmethod
    def _fmt_float(value: float | None) -> str:
        return "--" if value is None else f"{value:,.2f}"

    @staticmethod
    def _fmt_int(value: int | None) -> str:
        return "--" if value is None else f"{value:,}"

    @staticmethod
    def _fmt_time(value) -> str:
        return value.astimezone().strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "astimezone") else "--"


class MarketDepthPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }"
            "QLabel { color: #f8fafc; }"
            "QTableWidget { background: #0b1220; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }"
            "QHeaderView::section { background: #1f2937; color: #f8fafc; border: 1px solid #334155; padding: 6px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Market Depth")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        self.symbol_label = QLabel("Symbol: --")
        self.updated_label = QLabel("Updated: --")
        layout.addWidget(self.symbol_label)
        layout.addWidget(self.updated_label)

        self.table = QTableWidget(5, 4)
        self.table.setHorizontalHeaderLabels(["Bid Qty", "Bid Price", "Ask Price", "Ask Qty"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

    def clear(self) -> None:
        self.symbol_label.setText("Symbol: --")
        self.updated_label.setText("Updated: --")
        for row in range(5):
            for col in range(4):
                self.table.setItem(row, col, QTableWidgetItem("--"))

    def update_snapshot(self, snapshot: MarketDepthSnapshot | None) -> None:
        if snapshot is None:
            self.clear()
            return

        self.symbol_label.setText(f"Symbol: {snapshot.symbol}")
        stamp = snapshot.timestamp.astimezone().strftime("%H:%M:%S") if hasattr(snapshot.timestamp, "astimezone") else "--"
        self.updated_label.setText(f"Updated: {stamp}")

        levels = list(snapshot.levels)[:5]
        for row in range(5):
            level = levels[row] if row < len(levels) else None
            if level is None:
                values = ["--", "--", "--", "--"]
            else:
                values = [
                    f"{level.bid_qty:,}",
                    f"{level.bid_price:,.2f}",
                    f"{level.ask_price:,.2f}",
                    f"{level.ask_qty:,}",
                ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
