from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from src.services.order_service import OrderService, OrderServiceError
from src.services.order_validator import OrderValidator, ValidationContext


class OrderViewModel(QObject):
    ordersUpdated = Signal(list)
    tradesUpdated = Signal(list)
    orderPlaced = Signal(dict)
    orderModified = Signal(dict)
    orderCancelled = Signal(dict)
    errorOccurred = Signal(str)

    def __init__(self, service: OrderService | None = None, validator: OrderValidator | None = None) -> None:
        super().__init__()
        self._service = service or OrderService()
        self._validator = validator or OrderValidator()
        self._context = ValidationContext()
        self._orders_cache: list[dict] = []
        self._search_query = ""
        self._status_filter = "ALL"

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.refresh_orders)

    def refresh_orders(self) -> None:
        try:
            rows = self._service.get_order_book()
            self._orders_cache = rows
            self.ordersUpdated.emit(self._filtered_orders(rows))
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def refresh_trades(self) -> None:
        try:
            rows = self._service.get_trade_book()
            self.tradesUpdated.emit(rows)
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def refresh_all(self) -> None:
        self.refresh_orders()
        self.refresh_trades()

    def place_order(self, payload: dict) -> None:
        try:
            self._validator.validate_place(payload, self._context)
            result = self._service.place_order(**payload)
            self.orderPlaced.emit(result)
            self.refresh_orders()
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def modify_order(self, *, order_id: str, quantity: int | None = None, price: float | None = None, trigger_price: float | None = None, validity: str | None = None) -> None:
        try:
            self._validator.validate_modify(
                {
                    "order_id": order_id,
                    "quantity": quantity,
                    "price": price,
                    "trigger_price": trigger_price,
                    "validity": validity,
                },
                self._context,
            )
            result = self._service.modify_order(
                order_id=order_id,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                validity=validity,
            )
            self.orderModified.emit(result)
            self.refresh_orders()
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def cancel_order(self, order_id: str) -> None:
        try:
            result = self._service.cancel_order(order_id=order_id)
            self.orderCancelled.emit(result)
            self.refresh_orders()
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def set_search_query(self, query: str) -> None:
        self._search_query = str(query or "").strip().upper()
        self.ordersUpdated.emit(self._filtered_orders(self._orders_cache))

    def set_status_filter(self, status: str) -> None:
        self._status_filter = str(status or "ALL").strip().upper() or "ALL"
        self.ordersUpdated.emit(self._filtered_orders(self._orders_cache))

    def start_live_updates(self) -> None:
        self._refresh_timer.start()
        self.refresh_orders()

    def stop_live_updates(self) -> None:
        self._refresh_timer.stop()

    def update_limits(self, *, available_funds: float | None = None, max_quantity: int | None = None, freeze_quantity: int | None = None) -> None:
        self._context = ValidationContext(
            available_funds=float(available_funds if available_funds is not None else self._context.available_funds),
            max_quantity=int(max_quantity if max_quantity is not None else self._context.max_quantity),
            freeze_quantity=int(freeze_quantity if freeze_quantity is not None else self._context.freeze_quantity),
        )

    def _filtered_orders(self, rows: list[dict]) -> list[dict]:
        out = list(rows)
        if self._search_query:
            needle = self._search_query
            out = [
                row
                for row in out
                if needle in str(row.get("symbol", "")).upper() or needle in str(row.get("order_id", "")).upper()
            ]
        if self._status_filter != "ALL":
            out = [row for row in out if str(row.get("status", "")).upper() == self._status_filter]
        return out


OrdersViewModel = OrderViewModel
