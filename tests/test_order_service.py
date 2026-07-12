from __future__ import annotations

import pytest

from src.brokers import BrokerConnectionError
from src.services.order_service import OrderService, OrderServiceError


class _FakeBroker:
    def __init__(self) -> None:
        self.place_calls = 0
        self.modify_calls = 0
        self.cancel_calls = 0
        self.order_book_calls = 0
        self.trade_book_calls = 0

        self.fail_place_once_timeout = False
        self.raise_error: Exception | None = None

    def place_order(self, **kwargs):
        self.place_calls += 1
        if self.fail_place_once_timeout and self.place_calls == 1:
            raise TimeoutError("timed out")
        if self.raise_error is not None:
            raise self.raise_error
        return {"OrderID": "OID-1", "Message": "Order accepted", "Status": "Success"}

    def modify_order(self, **kwargs):
        self.modify_calls += 1
        if self.raise_error is not None:
            raise self.raise_error
        return {"order_id": kwargs.get("order_id", "OID-1"), "status": "Modified", "message": "Updated"}

    def cancel_order(self, **kwargs):
        self.cancel_calls += 1
        if self.raise_error is not None:
            raise self.raise_error
        return {"order_id": kwargs.get("order_id", "OID-1"), "status": "Cancelled", "message": "Cancelled"}

    def get_order_book(self, **kwargs):
        self.order_book_calls += 1
        if self.raise_error is not None:
            raise self.raise_error
        return [
            {
                "OrderID": "OID-2",
                "ScripName": "SBIN",
                "BuySell": "B",
                "OrderQty": 10,
                "ExecutedQty": 4,
                "Price": 820.5,
                "Status": "OPEN",
                "Time": "09:20:00",
            },
            {
                "OrderID": "OID-1",
                "ScripName": "HDFCBANK",
                "BuySell": "S",
                "OrderQty": 3,
                "ExecutedQty": 3,
                "Price": 1699.0,
                "Status": "COMPLETE",
                "Time": "09:10:00",
            },
        ]

    def get_trade_book(self, **kwargs):
        self.trade_book_calls += 1
        if self.raise_error is not None:
            raise self.raise_error
        return [
            {
                "TradeID": "T-11",
                "OrderID": "OID-2",
                "ScripName": "SBIN",
                "BuySell": "B",
                "TradePrice": 820.5,
                "TradeQty": 4,
                "Exchange": "NSE",
                "TradeTime": "09:21:00",
            }
        ]


def test_order_service_place_modify_cancel_and_books() -> None:
    backend = _FakeBroker()
    service = OrderService(backend=backend)

    placed = service.place_order(
        exchange="NSE",
        symbol="SBIN",
        side="BUY",
        quantity=2,
        price=0,
        trigger_price=0,
        order_type="MARKET",
        product="CNC",
        validity="DAY",
    )
    assert placed["ok"] is True
    assert placed["order_id"] == "OID-1"

    modified = service.modify_order(order_id="OID-1", quantity=5, price=821.2)
    assert modified["order_id"] == "OID-1"
    assert modified["status"] == "MODIFIED"

    cancelled = service.cancel_order(order_id="OID-1")
    assert cancelled["order_id"] == "OID-1"
    assert cancelled["status"] == "CANCELLED"

    orders = service.get_order_book()
    assert len(orders) == 2
    assert orders[0]["order_id"] == "OID-2"
    assert orders[0]["pending_qty"] == 6

    trades = service.get_trade_book()
    assert len(trades) == 1
    assert trades[0]["trade_id"] == "T-11"
    assert trades[0]["side"] == "BUY"


def test_order_service_retries_once_on_timeout() -> None:
    backend = _FakeBroker()
    backend.fail_place_once_timeout = True
    service = OrderService(backend=backend, max_retries=1)

    result = service.place_order(
        exchange="NSE",
        symbol="SBIN",
        side="BUY",
        quantity=1,
        order_type="MARKET",
        product="MIS",
    )

    assert result["ok"] is True
    assert backend.place_calls == 2


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (RuntimeError("Unauthorized access"), "unauthorized"),
        (RuntimeError("Session expired"), "session_expired"),
        (BrokerConnectionError("Broker connection unavailable."), "network_failure"),
        (RuntimeError("Some unknown upstream error"), "broker_error"),
    ],
)
def test_order_service_maps_errors(error: Exception, code: str) -> None:
    backend = _FakeBroker()
    backend.raise_error = error
    service = OrderService(backend=backend)

    with pytest.raises(OrderServiceError) as exc_info:
        service.get_order_book()

    assert exc_info.value.code == code
