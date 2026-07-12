from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QSplitter, QVBoxLayout, QWidget

from src.ui.live_quote_panel import LiveQuotePanel
from src.ui.viewmodels.dashboard_view_model import DashboardViewModel


class DashboardPage(QWidget):
    """Professional dashboard with live index cards and system panes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = DashboardViewModel()
        self._activity_items: deque[str] = deque(maxlen=80)
        self._log_items: deque[str] = deque(maxlen=120)
        self._build_ui()
        self._wire_events()

        self._timer = QTimer(self)
        self._timer.setInterval(self._view_model.refresh_seconds * 1000)
        self._timer.timeout.connect(self._view_model.refresh_indices)
        self._timer.start()
        self._view_model.refresh_indices()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #f8fafc;")
        root.addWidget(title)

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)
        self._cards: dict[str, tuple[QLabel, QLabel]] = {}

        for idx, name in enumerate(["NIFTY", "BANKNIFTY", "SENSEX", "VIX"]):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: #111827; border: 1px solid #334155; border-radius: 12px; }"
                "QLabel { color: #f8fafc; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(4)

            title_label = QLabel(name)
            title_label.setStyleSheet("font-size: 14px; color: #cbd5e1; font-weight: 600;")
            value_label = QLabel("--")
            value_label.setStyleSheet("font-size: 24px; font-weight: 800;")
            change_label = QLabel("--")
            change_label.setStyleSheet("font-size: 13px; color: #94a3b8;")

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addWidget(change_label)
            cards_layout.addWidget(card, idx // 2, idx % 2)
            self._cards[name] = (value_label, change_label)

        root.addLayout(cards_layout)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        left_pane = self._pane("Recent Activity")
        self.recent_activity = QListWidget()
        left_pane.layout().addWidget(self.recent_activity)

        center_pane = self._pane("System Logs")
        self.system_logs = QListWidget()
        center_pane.layout().addWidget(self.system_logs)

        right_pane = self._pane("Connection Status")
        right_layout = right_pane.layout()
        self.connection_badge = QLabel("Connecting...")
        self.connection_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #f59e0b;")
        right_layout.addWidget(self.connection_badge)

        self.live_quote_panel = LiveQuotePanel(self._view_model.get_quote, self)
        right_layout.addWidget(self.live_quote_panel)

        splitter.addWidget(left_pane)
        splitter.addWidget(center_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([280, 360, 420])

        root.addWidget(splitter)

    def _wire_events(self) -> None:
        self._view_model.indices_updated.connect(self._on_indices_updated)
        self._view_model.status_updated.connect(self._on_status_updated)
        self._view_model.activity_added.connect(self._append_activity)
        self._view_model.log_added.connect(self._append_log)

    def _on_indices_updated(self, payload: dict) -> None:
        for name, (value_label, change_label) in self._cards.items():
            row = payload.get(name, {})
            ltp_raw = row.get("ltp")
            change_raw = row.get("change_percent")
            if ltp_raw is None:
                value_label.setText("--")
            else:
                value_label.setText(f"{float(ltp_raw):,.2f}")

            if change_raw is None:
                change_label.setText("--")
                change_label.setStyleSheet("font-size: 13px; color: #94a3b8;")
                continue

            change_percent = float(change_raw)
            change_label.setText(f"{change_percent:+.2f}%")
            if change_percent > 0:
                change_label.setStyleSheet("font-size: 13px; color: #22c55e; font-weight: 700;")
            elif change_percent < 0:
                change_label.setStyleSheet("font-size: 13px; color: #ef4444; font-weight: 700;")
            else:
                change_label.setStyleSheet("font-size: 13px; color: #94a3b8;")

    def _on_status_updated(self, status: str) -> None:
        if status == "Connected":
            self.connection_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #22c55e;")
        elif status == "Session unavailable":
            self.connection_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #ef4444;")
        else:
            self.connection_badge.setStyleSheet("font-size: 14px; font-weight: 700; color: #f59e0b;")
        self.connection_badge.setText(status)

    def _append_activity(self, message: str) -> None:
        self._activity_items.appendleft(message)
        self.recent_activity.clear()
        self.recent_activity.addItems(list(self._activity_items))

    def _append_log(self, message: str) -> None:
        self._log_items.appendleft(message)
        self.system_logs.clear()
        self.system_logs.addItems(list(self._log_items))

    @staticmethod
    def _pane(title: str) -> QFrame:
        pane = QFrame()
        pane.setStyleSheet(
            "QFrame { background: #111827; border: 1px solid #334155; border-radius: 10px; }"
            "QLabel { color: #e2e8f0; }"
            "QListWidget { background: #0b1220; border: 1px solid #334155; border-radius: 8px; color: #cbd5e1; }"
        )
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)
        return pane
