from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QSizePolicy, QToolBar, QWidget

from src.core.config import config


class MainToolbar(QToolBar):
    """Primary toolbar for the main window."""

    refresh_requested = Signal()
    symbol_search_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMovable(False)
        self.setStyleSheet("QToolBar { background: #111827; border: none; padding: 6px; }")

        self.connection_status = QLabel("Connection: Connecting")
        self.connection_status.setStyleSheet("color: #f59e0b; font-weight: 700;")
        self.addWidget(self.connection_status)

        self.addSeparator()

        user = str(config.get("broker_username", "Trader") or "Trader")
        self.user_label = QLabel(f"User: {user}")
        self.user_label.setStyleSheet("color: #cbd5e1;")
        self.addWidget(self.user_label)

        self.addSeparator()

        self.exchange_status = QLabel("Exchange: NSE Open")
        self.exchange_status.setStyleSheet("color: #22c55e; font-weight: 600;")
        self.addWidget(self.exchange_status)

        self.addSeparator()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("background: #38bdf8; color: #0f172a; border-radius: 6px; padding: 6px 10px;")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.addWidget(self.refresh_button)

        self.search_symbol = QLineEdit()
        self.search_symbol.setPlaceholderText("Search Symbol")
        self.search_symbol.setFixedWidth(220)
        self.search_symbol.returnPressed.connect(self._emit_search)
        self.addWidget(self.search_symbol)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        self.session_hint = QLabel("Live session required")
        self.session_hint.setStyleSheet("color: #94a3b8;")
        self.addWidget(self.session_hint)

    def _emit_search(self) -> None:
        symbol = self.search_symbol.text().strip().upper()
        if symbol:
            self.symbol_search_requested.emit(symbol)

    def set_connection_status(self, status: str) -> None:
        text = f"Connection: {status}"
        self.connection_status.setText(text)
        if status.lower().startswith("connected"):
            self.connection_status.setStyleSheet("color: #22c55e; font-weight: 700;")
        elif status.lower().startswith("session") or status.lower().startswith("disconnected"):
            self.connection_status.setStyleSheet("color: #ef4444; font-weight: 700;")
        else:
            self.connection_status.setStyleSheet("color: #f59e0b; font-weight: 700;")

    def set_exchange_status(self, status: str) -> None:
        self.exchange_status.setText(f"Exchange: {status}")
