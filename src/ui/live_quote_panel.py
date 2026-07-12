from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class LiveQuotePanel(QFrame):
    """Reusable live quote panel fed only by a market data callback."""

    def __init__(self, fetch_quote_callback, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fetch_quote = fetch_quote_callback
        self.setObjectName("live_quote_panel")
        self.setStyleSheet(
            "QFrame#live_quote_panel { background: #111827; border: 1px solid #334155; border-radius: 10px; }"
            "QLabel { color: #e2e8f0; }"
            "QLineEdit { background: #0b1220; border: 1px solid #334155; border-radius: 6px; padding: 6px; color: #f8fafc; }"
            "QPushButton { background: #0ea5e9; color: #082f49; border-radius: 6px; padding: 6px 10px; font-weight: 700; }"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Live Quote Panel")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        root.addWidget(title)

        search_row = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Search symbol (e.g. HDFCBANK)")
        self.symbol_input.returnPressed.connect(self.refresh_quote)

        self.refresh_button = QPushButton("Get Quote")
        self.refresh_button.clicked.connect(self.refresh_quote)

        search_row.addWidget(self.symbol_input)
        search_row.addWidget(self.refresh_button)
        root.addLayout(search_row)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft)

        self.symbol_value = QLabel("--")
        self.ltp_value = QLabel("--")
        self.change_value = QLabel("--")
        self.bid_ask_value = QLabel("--")
        self.volume_value = QLabel("--")
        self.updated_value = QLabel("--")

        form.addRow("Symbol", self.symbol_value)
        form.addRow("LTP", self.ltp_value)
        form.addRow("Change", self.change_value)
        form.addRow("Bid / Ask", self.bid_ask_value)
        form.addRow("Volume", self.volume_value)
        form.addRow("Updated", self.updated_value)
        root.addLayout(form)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94a3b8;")
        root.addWidget(self.status_label)

    def refresh_quote(self) -> None:
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            self.status_label.setText("Enter a symbol")
            return

        quote = self._fetch_quote(symbol)
        if not quote:
            self.status_label.setText("Session unavailable")
            return

        self.symbol_value.setText(str(quote.get("symbol", symbol)))
        self.ltp_value.setText(f"{float(quote.get('ltp', 0.0) or 0.0):,.2f}")

        change_percent = float(quote.get("change_percent", 0.0) or 0.0)
        self.change_value.setText(f"{change_percent:+.2f}%")
        if change_percent > 0:
            self.change_value.setStyleSheet("color: #22c55e; font-weight: 700;")
        elif change_percent < 0:
            self.change_value.setStyleSheet("color: #ef4444; font-weight: 700;")
        else:
            self.change_value.setStyleSheet("color: #e2e8f0; font-weight: 700;")

        bid = float(quote.get("bid", 0.0) or 0.0)
        ask = float(quote.get("ask", 0.0) or 0.0)
        self.bid_ask_value.setText(f"{bid:,.2f} / {ask:,.2f}")
        self.volume_value.setText(f"{int(quote.get('volume', 0) or 0):,}")

        timestamp = quote.get("timestamp")
        if hasattr(timestamp, "astimezone"):
            display = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        else:
            display = "--"
        self.updated_value.setText(display)
        self.status_label.setText("Connected")
