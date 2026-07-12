from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

from src.ui.workspace.viewmodels.workspace_viewmodels import OrderPanelViewModel


class OrderPanel(QWidget):
    def __init__(self, viewmodel: OrderPanelViewModel | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = viewmodel or OrderPanelViewModel()
        self._build_ui()
        self._vm.orderIntentUpdated.connect(self._on_intent)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("Order Panel")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        self.exchange = QComboBox()
        self.exchange.addItems(["NSE", "BSE"])
        self.side = QComboBox()
        self.side.addItems(["BUY", "SELL"])
        self.qty = QSpinBox()
        self.qty.setRange(1, 1000000)
        self.price = QDoubleSpinBox()
        self.price.setRange(0.0, 1000000.0)
        self.price.setDecimals(2)
        self.order_type = QComboBox()
        self.order_type.addItems(["MARKET", "LIMIT", "SL", "SL-M"])
        self.product = QComboBox()
        self.product.addItems(["CNC", "MIS", "NRML"])

        form.addRow("Exchange", self.exchange)
        form.addRow("Side", self.side)
        form.addRow("Quantity", self.qty)
        form.addRow("Price", self.price)
        form.addRow("Order Type", self.order_type)
        form.addRow("Product", self.product)
        layout.addLayout(form)

        self.buy_btn = QPushButton("BUY")
        self.sell_btn = QPushButton("SELL")
        self.msg = QLabel("No order intent")
        layout.addWidget(self.buy_btn)
        layout.addWidget(self.sell_btn)
        layout.addWidget(self.msg)
        layout.addStretch()

        self.buy_btn.clicked.connect(lambda: self._emit("BUY"))
        self.sell_btn.clicked.connect(lambda: self._emit("SELL"))

    def _emit(self, side: str) -> None:
        self._vm.emit_order_intent(
            {
                "exchange": self.exchange.currentText(),
                "side": side,
                "qty": self.qty.value(),
                "price": self.price.value(),
                "order_type": self.order_type.currentText(),
                "product": self.product.currentText(),
            }
        )

    def _on_intent(self, payload: dict) -> None:
        self.msg.setText(f"Intent: {payload.get('side', '')} {payload.get('qty', 0)}")
