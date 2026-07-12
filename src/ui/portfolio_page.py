from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from src.core.translation import t
from src.marketdata.model import MarketDataEvent, MarketEventType
from src.marketdata.service import market_data_service


class PortfolioPage(QWidget):
    """Portfolio page with holdings table and double-click symbol events."""

    symbol_double_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        market_data_service.subscribe(self._on_market_event)
        self._load_holdings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(t("portfolio.title"))
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                t("portfolio.col.symbol"),
                t("portfolio.col.company"),
                t("portfolio.col.qty"),
                t("portfolio.col.avg_price"),
                t("portfolio.col.ltp"),
                t("portfolio.col.pnl"),
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
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.table)

    def _load_holdings(self) -> None:
        positions = market_data_service.get_portfolio_positions()
        self.table.setRowCount(len(positions))
        for row, item in enumerate(positions):
            values = (item.symbol, item.company, item.quantity, item.average_price, item.ltp, item.pnl_percent)
            for col, value in enumerate(values):
                text = f"{value:,.2f}" if isinstance(value, float) else str(value)
                widget_item = QTableWidgetItem(text)
                if col == 5:
                    widget_item.setForeground(Qt.GlobalColor.green if float(value) >= 0 else Qt.GlobalColor.red)
                self.table.setItem(row, col, widget_item)

    def _on_market_event(self, event: MarketDataEvent) -> None:
        if event.event_type == MarketEventType.TICK:
            self._load_holdings()

    def closeEvent(self, event) -> None:  # noqa: N802
        market_data_service.unsubscribe(self._on_market_event)
        super().closeEvent(event)

    def _load_mock_holdings(self) -> None:
        # Backward compatibility shim for older callers.
        self._load_holdings()

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        symbol_item = self.table.item(item.row(), 0)
        if symbol_item is not None:
            self.symbol_double_clicked.emit(symbol_item.text())
