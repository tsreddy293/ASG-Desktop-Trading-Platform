from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
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

from src.ui.viewmodels.order_view_model import OrderViewModel


class OrderPage(QWidget):
    """Professional order management page with validation-aware controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = OrderViewModel()
        self._build_ui()
        self._wire_events()
        self._setup_shortcuts()
        self._view_model.start_live_updates()
        self._view_model.refresh_trades()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        title = QLabel("Order Management")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #f8fafc;")
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

        self.tabs.addTab(self.place_tab, "Order Entry")
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

        quantity_row = QHBoxLayout()
        self.qty_minus_button = QPushButton("-")
        self.qty_plus_button = QPushButton("+")
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 100_000)
        self.quantity_input.setValue(1)
        self.lot_size_input = QSpinBox()
        self.lot_size_input.setRange(1, 10_000)
        self.lot_size_input.setValue(1)
        self.max_qty_label = QLabel("Max Qty: 100000")
        self.max_qty_label.setStyleSheet("color: #94a3b8;")

        quantity_row.addWidget(self.qty_minus_button)
        quantity_row.addWidget(self.quantity_input)
        quantity_row.addWidget(self.qty_plus_button)
        quantity_row.addWidget(QLabel("Lot"))
        quantity_row.addWidget(self.lot_size_input)
        quantity_row.addWidget(self.max_qty_label)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.0, 10_000_000.0)
        self.price_input.setDecimals(2)
        self.price_input.setValue(0.0)

        self.trigger_price_input = QDoubleSpinBox()
        self.trigger_price_input.setRange(0.0, 10_000_000.0)
        self.trigger_price_input.setDecimals(2)
        self.trigger_price_input.setValue(0.0)

        self.auto_price_check = QCheckBox("Auto Price")

        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["MARKET", "LIMIT", "SL", "SL-M", "BRACKET ORDER", "COVER ORDER"])

        self.product_combo = QComboBox()
        self.product_combo.addItems(["CNC", "MIS", "NRML"])

        self.variety_combo = QComboBox()
        self.variety_combo.addItems(["REGULAR", "AMO"])

        self.validity_combo = QComboBox()
        self.validity_combo.addItems(["DAY", "IOC"])

        self.available_funds_input = QDoubleSpinBox()
        self.available_funds_input.setRange(0.0, 1_000_000_000.0)
        self.available_funds_input.setDecimals(2)
        self.available_funds_input.setValue(1_000_000.0)

        form.addRow("Exchange", self.exchange_combo)
        form.addRow("Symbol", self.symbol_input)
        form.addRow("Buy/Sell", self.side_combo)
        form.addRow("Quantity", quantity_row)
        form.addRow("Limit Price", self.price_input)
        form.addRow("Trigger Price", self.trigger_price_input)
        form.addRow("Auto Price", self.auto_price_check)
        form.addRow("Order Type", self.order_type_combo)
        form.addRow("Product", self.product_combo)
        form.addRow("Variety", self.variety_combo)
        form.addRow("Validity", self.validity_combo)
        form.addRow("Funds", self.available_funds_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.buy_button = QPushButton("BUY  [Ctrl+B]")
        self.buy_button.setStyleSheet("background: #16a34a; color: #052e16; font-weight: 800; border-radius: 8px; padding: 12px 16px;")
        self.sell_button = QPushButton("SELL [Ctrl+S]")
        self.sell_button.setStyleSheet("background: #dc2626; color: #450a0a; font-weight: 800; border-radius: 8px; padding: 12px 16px;")
        self.reset_button = QPushButton("RESET [Esc]")
        self.reset_button.setStyleSheet("background: #334155; color: #e2e8f0; border-radius: 8px; padding: 12px 16px;")

        buttons.addWidget(self.buy_button)
        buttons.addWidget(self.sell_button)
        buttons.addWidget(self.reset_button)
        buttons.addStretch()

        layout.addLayout(buttons)
        layout.addStretch()

    def _build_order_book_tab(self) -> None:
        layout = QVBoxLayout(self.order_book_tab)

        filters = QHBoxLayout()
        self.order_search_input = QLineEdit()
        self.order_search_input.setPlaceholderText("Search order id or symbol")
        self.order_status_filter = QComboBox()
        self.order_status_filter.addItems(["ALL", "PENDING", "OPEN", "EXECUTED", "REJECTED", "CANCELLED", "PARTIAL FILLED"])
        self.refresh_orders_button = QPushButton("Refresh")
        filters.addWidget(self.order_search_input)
        filters.addWidget(self.order_status_filter)
        filters.addWidget(self.refresh_orders_button)
        layout.addLayout(filters)

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
        actions.addWidget(self.modify_button)
        actions.addWidget(self.cancel_button)
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
        self.qty_plus_button.clicked.connect(self._increment_qty)
        self.qty_minus_button.clicked.connect(self._decrement_qty)
        self.lot_size_input.valueChanged.connect(self._align_quantity_to_lot)
        self.auto_price_check.toggled.connect(self._apply_auto_price)

        self.buy_button.clicked.connect(lambda: self._submit_order("BUY"))
        self.sell_button.clicked.connect(lambda: self._submit_order("SELL"))
        self.reset_button.clicked.connect(self._reset_form)

        self.modify_button.clicked.connect(self._modify_selected_order)
        self.cancel_button.clicked.connect(self._cancel_selected_order)
        self.refresh_orders_button.clicked.connect(self._view_model.refresh_orders)
        self.refresh_trades_button.clicked.connect(self._view_model.refresh_trades)

        self.order_search_input.textChanged.connect(self._view_model.set_search_query)
        self.order_status_filter.currentTextChanged.connect(self._view_model.set_status_filter)

        self._view_model.ordersUpdated.connect(self._render_orders)
        self._view_model.tradesUpdated.connect(self._render_trades)
        self._view_model.orderPlaced.connect(self._on_order_placed)
        self._view_model.orderModified.connect(self._on_order_modified)
        self._view_model.orderCancelled.connect(self._on_order_cancelled)
        self._view_model.errorOccurred.connect(self._on_error)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+B"), self, activated=lambda: self._submit_order("BUY"))
        QShortcut(QKeySequence("Ctrl+S"), self, activated=lambda: self._submit_order("SELL"))
        QShortcut(QKeySequence("Escape"), self, activated=self._reset_form)

    def refresh_data(self) -> None:
        self._view_model.refresh_all()

    def _on_order_type_changed(self, order_type: str) -> None:
        kind = order_type.upper()
        if kind == "MARKET":
            self.price_input.setEnabled(False)
            self.trigger_price_input.setEnabled(False)
            self.price_input.setValue(0.0)
            self.trigger_price_input.setValue(0.0)
        elif kind == "LIMIT":
            self.price_input.setEnabled(True)
            self.trigger_price_input.setEnabled(False)
            self.trigger_price_input.setValue(0.0)
        else:
            self.price_input.setEnabled(True)
            self.trigger_price_input.setEnabled(True)

    def _increment_qty(self) -> None:
        step = self.lot_size_input.value()
        self.quantity_input.setValue(self.quantity_input.value() + step)

    def _decrement_qty(self) -> None:
        step = self.lot_size_input.value()
        self.quantity_input.setValue(max(self.quantity_input.minimum(), self.quantity_input.value() - step))

    def _align_quantity_to_lot(self) -> None:
        lot = self.lot_size_input.value()
        qty = self.quantity_input.value()
        aligned = max(lot, (qty // lot) * lot)
        self.quantity_input.setValue(aligned)

    def _apply_auto_price(self, enabled: bool) -> None:
        if enabled and self.price_input.value() <= 0:
            self.price_input.setValue(1.0)

    def _submit_order(self, side: str) -> None:
        self._view_model.update_limits(available_funds=self.available_funds_input.value())

        payload = {
            "exchange": self.exchange_combo.currentText(),
            "symbol": self.symbol_input.text().strip().upper(),
            "side": side,
            "quantity": self.quantity_input.value(),
            "lot_size": self.lot_size_input.value(),
            "price": self.price_input.value(),
            "trigger_price": self.trigger_price_input.value(),
            "order_type": self.order_type_combo.currentText(),
            "product": self.product_combo.currentText(),
            "validity": self.validity_combo.currentText(),
            "variety": self.variety_combo.currentText(),
            "auto_price": self.auto_price_check.isChecked(),
            "ltp": self.price_input.value(),
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
        trigger, ok_trigger = QInputDialog.getDouble(self, "Modify Order", "Trigger", min=0.0, decimals=2)
        if not ok_trigger:
            return

        self._view_model.modify_order(order_id=order_id, quantity=quantity, price=price, trigger_price=trigger)

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
        self.lot_size_input.setValue(1)
        self.price_input.setValue(0.0)
        self.trigger_price_input.setValue(0.0)
        self.order_type_combo.setCurrentText("MARKET")
        self.product_combo.setCurrentText("CNC")
        self.variety_combo.setCurrentText("REGULAR")
        self.validity_combo.setCurrentText("DAY")
        self.auto_price_check.setChecked(False)

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

    def closeEvent(self, event) -> None:  # noqa: N802
        self._view_model.stop_live_updates()
        super().closeEvent(event)


OrdersPage = OrderPage
