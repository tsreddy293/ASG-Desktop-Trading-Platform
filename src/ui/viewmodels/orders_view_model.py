from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.services.order_service import OrderService, OrderServiceError


class OrdersViewModel(QObject):
    ordersUpdated = Signal(list)
    tradesUpdated = Signal(list)
    orderPlaced = Signal(dict)
    orderModified = Signal(dict)
    orderCancelled = Signal(dict)
    errorOccurred = Signal(str)

    def __init__(self, service: OrderService | None = None) -> None:
        super().__init__()
        self._service = service or OrderService()

    def refresh_orders(self) -> None:
        try:
            rows = self._service.get_order_book()
            self.ordersUpdated.emit(rows)
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
            result = self._service.place_order(**payload)
            self.orderPlaced.emit(result)
            self.refresh_orders()
        except OrderServiceError as exc:
            self.errorOccurred.emit(str(exc))

    def modify_order(self, *, order_id: str, quantity: int | None = None, price: float | None = None, trigger_price: float | None = None, validity: str | None = None) -> None:
        try:
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
