from __future__ import annotations

from src.services.order_service import OrderServiceError
from src.ui.viewmodels.orders_view_model import OrdersViewModel


class _FakeOrderService:
    def __init__(self) -> None:
        self.fail = False

    def place_order(self, **kwargs):
        if self.fail:
            raise OrderServiceError("broker_error", "place failed")
        return {"order_id": "OID-1", "status": "PLACED", "ok": True, "message": "ok"}

    def modify_order(self, **kwargs):
        if self.fail:
            raise OrderServiceError("broker_error", "modify failed")
        return {"order_id": kwargs.get("order_id", "OID-1"), "status": "MODIFIED", "ok": True, "message": "ok"}

    def cancel_order(self, **kwargs):
        if self.fail:
            raise OrderServiceError("broker_error", "cancel failed")
        return {"order_id": kwargs.get("order_id", "OID-1"), "status": "CANCELLED", "ok": True, "message": "ok"}

    def get_order_book(self):
        if self.fail:
            raise OrderServiceError("broker_error", "order book failed")
        return [{"order_id": "OID-1"}]

    def get_trade_book(self):
        if self.fail:
            raise OrderServiceError("broker_error", "trade book failed")
        return [{"trade_id": "TR-1"}]


def test_orders_viewmodel_emits_update_and_action_signals() -> None:
    service = _FakeOrderService()
    vm = OrdersViewModel(service=service)

    seen_orders = []
    seen_trades = []
    seen_placed = []
    seen_modified = []
    seen_cancelled = []

    vm.ordersUpdated.connect(seen_orders.append)
    vm.tradesUpdated.connect(seen_trades.append)
    vm.orderPlaced.connect(seen_placed.append)
    vm.orderModified.connect(seen_modified.append)
    vm.orderCancelled.connect(seen_cancelled.append)

    vm.refresh_orders()
    vm.refresh_trades()
    vm.place_order({"exchange": "NSE", "symbol": "SBIN", "side": "BUY", "quantity": 1, "order_type": "MARKET", "product": "CNC"})
    vm.modify_order(order_id="OID-1", quantity=2, price=801.5)
    vm.cancel_order("OID-1")

    vm.set_search_query("SBI")
    vm.set_status_filter("PENDING")

    assert len(seen_orders) >= 1
    assert len(seen_trades) >= 1
    assert seen_placed[-1]["status"] == "PLACED"
    assert seen_modified[-1]["status"] == "MODIFIED"
    assert seen_cancelled[-1]["status"] == "CANCELLED"


def test_orders_viewmodel_emits_error_signal_on_failure() -> None:
    service = _FakeOrderService()
    service.fail = True
    vm = OrdersViewModel(service=service)

    errors = []
    vm.errorOccurred.connect(errors.append)

    vm.refresh_orders()
    vm.place_order({"exchange": "NSE", "symbol": "SBIN", "side": "BUY", "quantity": 1, "order_type": "MARKET", "product": "CNC"})
    vm.modify_order(order_id="OID-1", quantity=1, price=100.0)
    vm.cancel_order("OID-1")

    assert len(errors) >= 4


def test_orders_viewmodel_validation_error_emitted() -> None:
    service = _FakeOrderService()
    vm = OrdersViewModel(service=service)

    errors = []
    vm.errorOccurred.connect(errors.append)

    vm.place_order({"exchange": "NSE", "symbol": "SBIN", "side": "BUY", "quantity": 0, "order_type": "MARKET", "product": "CNC"})

    assert errors
