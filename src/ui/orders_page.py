from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.viewmodels.orders_view_model import OrdersViewModel


class OrdersPage(QWidget):
    """Orders module page with place order, order book and trade book."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = OrdersViewModel()
        self._build_ui()
        self._wire_events()
        self._view_model.refresh_all()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        title = QLabel("Orders")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f8fafc;")
        root.addWidget(title)

        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #334155; background: #111827; border-radius: 8px; }"
            "QTabBar::tab { background: #1f2937; color: #cbd5e1; padding: 8px 12px; border-top-left-radius: 6px; border-top-right-radius: 6px; }"
            "QTabBar::tab:selected { background: #38bdf8; color: #0f172a; }"
        )

        self.place_tab = QWidget(self)
        self.order_book_tab = QWidget(self)
        self.trade_book_tab = QWidget(self)

        self.tabs.addTab(self.place_tab, "Place Order")
        self.tabs.addTab(self.order_book_tab, "Order Book")
        self.tabs.addTab(self.trade_book_tab, "Trade Book")

        root.addWidget(self.tabs)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #94a3b8;")
        root.addWidget(self.status_label)

        self._build_place_tab()
        self._build_order_book_tab()
        self._build_trade_book_tab()

    def _build_place_tab(self) -> None:
        layout = QVBoxLayout(self.place_tab)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["NSE", "BSE"])

        self.symbol_input = QLineEdit("SBIN")
        self.symbol_input.setPlaceholderText("Enter symbol")

        self.side_combo = QComboBox()
        self.side_combo.addItems(["BUY", "SELL"])

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 10_000_000)
        self.quantity_input.setValue(1)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.0, 10_000_000.0)
        self.price_input.setDecimals(2)
        self.price_input.setValue(0.0)

        self.trigger_price_input = QDoubleSpinBox()
        self.trigger_price_input.setRange(0.0, 10_000_000.0)
        self.trigger_price_input.setDecimals(2)
        self.trigger_price_input.setValue(0.0)

        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT", "SL", "SL-M"])

        self.product_combo = QComboBox()
        self.product_combo.addItems(["CNC", "MIS", "NRML"])

        self.validity_combo = QComboBox()
        self.validity_combo.addItems(["DAY", "IOC"])

        form.addRow("Exchange", self.exchange_combo)
        form.addRow("Symbol", self.symbol_input)
        form.addRow("Buy/Sell", self.side_combo)
        form.addRow("Quantity", self.quantity_input)
        form.addRow("Price", self.price_input)
        form.addRow("Trigger Price", self.trigger_price_input)
        form.addRow("Order Type", self.order_type_combo)
        form.addRow("Product", self.product_combo)
        form.addRow("Validity", self.validity_combo)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.buy_button = QPushButton("BUY")
        self.buy_button.setStyleSheet("background: #22c55e; color: #052e16; font-weight: 700; border-radius: 6px; padding: 8px 12px;")
        self.sell_button = QPushButton("SELL")
        self.sell_button.setStyleSheet("background: #ef4444; color: #450a0a; font-weight: 700; border-radius: 6px; padding: 8px 12px;")
        self.reset_button = QPushButton("RESET")

        buttons.addWidget(self.buy_button)
        buttons.addWidget(self.sell_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        layout.addStretch()

    def _build_order_book_tab(self) -> None:
        layout = QVBoxLayout(self.order_book_tab)

        self.order_table = QTableWidget(0, 9)
        self.order_table.setHorizontalHeaderLabels(
            [
                "Order ID",
                "Symbol",
                "Buy/Sell",
                "Quantity",
                "Executed Qty",
                "Pending Qty",
                "Price",
                "Status",
                "Time",
            ]
        )
        self.order_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.order_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.order_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.order_table.setAlternatingRowColors(True)

        layout.addWidget(self.order_table)

        actions = QHBoxLayout()
        self.modify_button = QPushButton("Modify")
        self.cancel_button = QPushButton("Cancel")
        self.refresh_orders_button = QPushButton("Refresh")

        actions.addWidget(self.modify_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.refresh_orders_button)
        actions.addStretch()
        layout.addLayout(actions)

    def _build_trade_book_tab(self) -> None:
        layout = QVBoxLayout(self.trade_book_tab)

        self.trade_table = QTableWidget(0, 8)
        self.trade_table.setHorizontalHeaderLabels(
            [
                "Trade ID",
                "Order ID",
                "Symbol",
                "Buy/Sell",
                "Price",
                "Quantity",
                "Exchange",
                "Trade Time",
            ]
        )
        self.trade_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.trade_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.trade_table.setAlternatingRowColors(True)

        layout.addWidget(self.trade_table)

        actions = QHBoxLayout()
        self.refresh_trades_button = QPushButton("Refresh")
        actions.addWidget(self.refresh_trades_button)
        actions.addStretch()
        layout.addLayout(actions)

    def _wire_events(self) -> None:
        self.order_type_combo.currentTextChanged.connect(self._on_order_type_changed)
        self.buy_button.clicked.connect(lambda: self._submit_order("BUY"))
        self.sell_button.clicked.connect(lambda: self._submit_order("SELL"))
        self.reset_button.clicked.connect(self._reset_form)

        self.modify_button.clicked.connect(self._modify_selected_order)
        self.cancel_button.clicked.connect(self._cancel_selected_order)
        self.refresh_orders_button.clicked.connect(self._view_model.refresh_orders)
        self.refresh_trades_button.clicked.connect(self._view_model.refresh_trades)

        self._view_model.ordersUpdated.connect(self._render_orders)
        self._view_model.tradesUpdated.connect(self._render_trades)
        self._view_model.orderPlaced.connect(self._on_order_placed)
        self._view_model.orderModified.connect(self._on_order_modified)
        self._view_model.orderCancelled.connect(self._on_order_cancelled)
        self._view_model.errorOccurred.connect(self._on_error)

    def refresh_data(self) -> None:
        self._view_model.refresh_all()

    def _on_order_type_changed(self, order_type: str) -> None:
        kind = order_type.upper()
        if kind == "MARKET":
            self.price_input.setEnabled(False)
            self.trigger_price_input.setEnabled(False)
            self.price_input.setValue(0.0)
            self.trigger_price_input.setValue(0.0)
        elif kind in {"LIMIT"}:
            self.price_input.setEnabled(True)
            self.trigger_price_input.setEnabled(False)
            self.trigger_price_input.setValue(0.0)
        else:
            self.price_input.setEnabled(True)
            self.trigger_price_input.setEnabled(True)

    def _submit_order(self, side: str) -> None:
        payload = {
            "exchange": self.exchange_combo.currentText(),
            "symbol": self.symbol_input.text().strip().upper(),
            "side": side,
            "quantity": self.quantity_input.value(),
            "price": self.price_input.value(),
            "trigger_price": self.trigger_price_input.value(),
            "order_type": self.order_type_combo.currentText(),
            "product": self.product_combo.currentText(),
            "validity": self.validity_combo.currentText(),
        }
        self._view_model.place_order(payload)

    def _selected_order_id(self) -> str:
        row = self.order_table.currentRow()
        if row < 0:
            return ""
        item = self.order_table.item(row, 0)
        return item.text().strip() if item is not None else ""

    def _modify_selected_order(self) -> None:
        order_id = self._selected_order_id()
        if not order_id:
            QMessageBox.information(self, "Modify Order", "Select an order first")
            return

        quantity, ok_qty = QInputDialog.getInt(self, "Modify Order", "Quantity", min=1, value=1)
        if not ok_qty:
            return
        price, ok_price = QInputDialog.getDouble(self, "Modify Order", "Price", min=0.0, decimals=2)
        if not ok_price:
            return

        self._view_model.modify_order(order_id=order_id, quantity=quantity, price=price)

    def _cancel_selected_order(self) -> None:
        order_id = self._selected_order_id()
        if not order_id:
            QMessageBox.information(self, "Cancel Order", "Select an order first")
            return
        self._view_model.cancel_order(order_id)

    def _render_orders(self, rows: list[dict]) -> None:
        self.order_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.order_table.setItem(row_index, 0, QTableWidgetItem(str(row.get("order_id", ""))))
            self.order_table.setItem(row_index, 1, QTableWidgetItem(str(row.get("symbol", ""))))
            self.order_table.setItem(row_index, 2, QTableWidgetItem(str(row.get("side", ""))))
            self.order_table.setItem(row_index, 3, QTableWidgetItem(str(row.get("quantity", 0))))
            self.order_table.setItem(row_index, 4, QTableWidgetItem(str(row.get("executed_qty", 0))))
            self.order_table.setItem(row_index, 5, QTableWidgetItem(str(row.get("pending_qty", 0))))
            self.order_table.setItem(row_index, 6, QTableWidgetItem(f"{float(row.get('price', 0.0)):,.2f}"))
            self.order_table.setItem(row_index, 7, QTableWidgetItem(str(row.get("status", ""))))
            self.order_table.setItem(row_index, 8, QTableWidgetItem(str(row.get("time", "--"))))

    def _render_trades(self, rows: list[dict]) -> None:
        self.trade_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.trade_table.setItem(row_index, 0, QTableWidgetItem(str(row.get("trade_id", ""))))
            self.trade_table.setItem(row_index, 1, QTableWidgetItem(str(row.get("order_id", ""))))
            self.trade_table.setItem(row_index, 2, QTableWidgetItem(str(row.get("symbol", ""))))
            self.trade_table.setItem(row_index, 3, QTableWidgetItem(str(row.get("side", ""))))
            self.trade_table.setItem(row_index, 4, QTableWidgetItem(f"{float(row.get('price', 0.0)):,.2f}"))
            self.trade_table.setItem(row_index, 5, QTableWidgetItem(str(row.get("quantity", 0))))
            self.trade_table.setItem(row_index, 6, QTableWidgetItem(str(row.get("exchange", ""))))
            self.trade_table.setItem(row_index, 7, QTableWidgetItem(str(row.get("trade_time", "--"))))

    def _reset_form(self) -> None:
        self.exchange_combo.setCurrentText("NSE")
        self.symbol_input.setText("")
        self.side_combo.setCurrentText("BUY")
        self.quantity_input.setValue(1)
        self.price_input.setValue(0.0)
        self.trigger_price_input.setValue(0.0)
        self.order_type_combo.setCurrentText("MARKET")
        self.product_combo.setCurrentText("CNC")
        self.validity_combo.setCurrentText("DAY")

    def _on_order_placed(self, result: dict) -> None:
        self.status_label.setText(f"Order placed: {result.get('order_id', '')} ({result.get('status', '')})")
        self.status_label.setStyleSheet("color: #22c55e;")

    def _on_order_modified(self, result: dict) -> None:
        self.status_label.setText(f"Order modified: {result.get('order_id', '')} ({result.get('status', '')})")
        self.status_label.setStyleSheet("color: #22c55e;")

    def _on_order_cancelled(self, result: dict) -> None:
        self.status_label.setText(f"Order cancelled: {result.get('order_id', '')} ({result.get('status', '')})")
        self.status_label.setStyleSheet("color: #22c55e;")

    def _on_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #ef4444;")
