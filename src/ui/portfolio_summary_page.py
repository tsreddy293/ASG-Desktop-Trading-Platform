from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from src.ui.viewmodels.portfolio_view_model import PortfolioViewModel


class PortfolioSummaryPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = PortfolioViewModel()
        self._build_ui()
        self._wire_events()
        self._vm.start()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Portfolio")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        grid = QGridLayout()
        self._cards: dict[str, QLabel] = {}
        labels = [
            ("available_cash", "Available Cash"),
            ("margin_used", "Margin Used"),
            ("total_investment", "Total Investment"),
            ("current_value", "Current Value"),
            ("todays_profit", "Today's Profit"),
            ("overall_profit", "Overall Profit"),
        ]

        for idx, (key, text) in enumerate(labels):
            heading = QLabel(text)
            heading.setStyleSheet("color: #94a3b8;")
            value = QLabel("0.00")
            value.setStyleSheet("font-size: 22px; font-weight: 700;")
            row = idx // 2
            col = (idx % 2) * 2
            grid.addWidget(heading, row * 2, col)
            grid.addWidget(value, row * 2 + 1, col)
            self._cards[key] = value

        layout.addLayout(grid)

        self.updated = QLabel("Updated: --")
        self.updated.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.updated)

    def _wire_events(self) -> None:
        self._vm.summaryUpdated.connect(self._render)
        self._vm.errorOccurred.connect(self.updated.setText)

    def _render(self, summary: dict) -> None:
        for key, label in self._cards.items():
            value = float(summary.get(key, 0.0) or 0.0)
            label.setText(f"{value:,.2f}")
            if key in {"todays_profit", "overall_profit"}:
                if value > 0:
                    label.setStyleSheet("font-size: 22px; font-weight: 700; color: #22c55e;")
                elif value < 0:
                    label.setStyleSheet("font-size: 22px; font-weight: 700; color: #ef4444;")
                else:
                    label.setStyleSheet("font-size: 22px; font-weight: 700; color: #94a3b8;")

        updated_at = summary.get("updated_at")
        if isinstance(updated_at, datetime):
            self.updated.setText(f"Updated: {updated_at.astimezone().strftime('%H:%M:%S')}")

    def refresh_data(self) -> None:
        self._vm.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._vm.stop()
        super().closeEvent(event)
