from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from src.brokers import BrokerConnectionError, broker_manager


_ORDER_TYPES = {
    "MARKET",
    "LIMIT",
    "SL",
    "SL-M",
    "BRACKET ORDER",
    "COVER ORDER",
}
_PRODUCT_TYPES = {"CNC", "MIS", "NRML"}
_SIDES = {"BUY", "SELL"}
_VALIDITIES = {"DAY", "IOC"}
_VARIETIES = {"REGULAR", "AMO"}


class BrokerOrdersBackend(Protocol):
    def place_order(self, **kwargs) -> dict[str, Any]:
        ...

    def modify_order(self, **kwargs) -> dict[str, Any]:
        ...

    def cancel_order(self, **kwargs) -> dict[str, Any]:
        ...

    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        ...

    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        ...


@dataclass(slots=True)
class OrderServiceError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


class OrderService:
    """Normalized order/trade service over broker manager with retry + error mapping."""

    def __init__(self, backend: BrokerOrdersBackend | None = None, max_retries: int = 1) -> None:
        self._backend = backend or broker_manager
        self._max_retries = max(0, int(max_retries))

    def place_order(
        self,
        *,
        exchange: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float = 0.0,
        trigger_price: float = 0.0,
        order_type: str = "MARKET",
        product: str = "CNC",
        validity: str = "DAY",
        variety: str = "REGULAR",
        lot_size: int = 1,
        auto_price: bool = False,
        ltp: float = 0.0,
    ) -> dict[str, Any]:
        clean_exchange = self._clean_exchange(exchange)
        clean_symbol = self._clean_symbol(symbol)
        clean_side = self._clean_side(side)
        clean_order_type = self._clean_order_type(order_type)
        clean_product = self._clean_product(product)
        clean_validity = self._clean_validity(validity)
        clean_variety = self._clean_variety(variety)
        clean_quantity = self._clean_quantity(quantity)
        clean_price = self._float_value(price)
        clean_trigger = self._float_value(trigger_price)
        clean_lot_size = max(1, int(lot_size or 1))

        if auto_price and clean_price <= 0:
            clean_price = self._float_value(ltp)

        payload = {
            "exchange": clean_exchange,
            "symbol": clean_symbol,
            "side": clean_side,
            "quantity": clean_quantity,
            "price": clean_price,
            "trigger_price": clean_trigger,
            "order_type": clean_order_type,
            "product": clean_product,
            "validity": clean_validity,
            "variety": clean_variety,
            "lot_size": clean_lot_size,
            "auto_price": bool(auto_price),
        }

        raw = self._with_retry(self._backend.place_order, **payload)
        return self._normalize_action_result(raw, action="place", fallback_order_id=clean_symbol)

    def modify_order(
        self,
        *,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
    ) -> dict[str, Any]:
        clean_order_id = self._clean_order_id(order_id)
        payload: dict[str, Any] = {"order_id": clean_order_id}
        if quantity is not None:
            payload["quantity"] = self._clean_quantity(quantity)
        if price is not None:
            payload["price"] = self._float_value(price)
        if trigger_price is not None:
            payload["trigger_price"] = self._float_value(trigger_price)
        if validity is not None:
            payload["validity"] = self._clean_validity(validity)

        raw = self._with_retry(self._backend.modify_order, **payload)
        return self._normalize_action_result(raw, action="modify", fallback_order_id=clean_order_id)

    def cancel_order(self, *, order_id: str) -> dict[str, Any]:
        clean_order_id = self._clean_order_id(order_id)
        raw = self._with_retry(self._backend.cancel_order, order_id=clean_order_id)
        return self._normalize_action_result(raw, action="cancel", fallback_order_id=clean_order_id)

    def get_order_book(self) -> list[dict[str, Any]]:
        rows = self._with_retry(self._backend.get_order_book)
        normalized = [self._normalize_order_row(row) for row in list(rows or [])]
        normalized.sort(key=lambda row: row["sort_time"], reverse=True)
        for row in normalized:
            row.pop("sort_time", None)
        return normalized

    def get_trade_book(self) -> list[dict[str, Any]]:
        rows = self._with_retry(self._backend.get_trade_book)
        normalized = [self._normalize_trade_row(row) for row in list(rows or [])]
        normalized.sort(key=lambda row: row["sort_time"], reverse=True)
        for row in normalized:
            row.pop("sort_time", None)
        return normalized

    def _with_retry(self, func, **kwargs):
        attempt = 0
        while True:
            try:
                return func(**kwargs)
            except TimeoutError as exc:
                if attempt < self._max_retries:
                    attempt += 1
                    continue
                raise OrderServiceError("timeout", "Network timeout while calling broker") from exc
            except Exception as exc:
                mapped = self._map_error(exc)
                if mapped.code == "timeout" and attempt < self._max_retries:
                    attempt += 1
                    continue
                raise mapped from exc

    @staticmethod
    def _map_error(exc: Exception) -> OrderServiceError:
        message = str(exc or "Broker error").strip() or "Broker error"
        lowered = message.lower()

        if "unauthorized" in lowered or "401" in lowered or "not authorized" in lowered:
            return OrderServiceError("unauthorized", "Unauthorized request to broker")
        if "session expired" in lowered or "token expired" in lowered or "invalid session" in lowered:
            return OrderServiceError("session_expired", "Session expired. Please login again")
        if "timeout" in lowered or "timed out" in lowered:
            return OrderServiceError("timeout", "Network timeout while calling broker")
        if isinstance(exc, (ConnectionError, BrokerConnectionError)) or "network" in lowered or "connection" in lowered:
            return OrderServiceError("network_failure", "Network failure while calling broker")
        return OrderServiceError("broker_error", f"Broker error: {message}")

    @staticmethod
    def _normalize_action_result(raw: Any, *, action: str, fallback_order_id: str) -> dict[str, Any]:
        payload = dict(raw or {})
        order_id = str(
            payload.get("order_id")
            or payload.get("OrderID")
            or payload.get("orderId")
            or payload.get("ExchOrderID")
            or payload.get("RemoteOrderID")
            or fallback_order_id
        )
        status_raw = str(payload.get("status") or payload.get("Status") or payload.get("message") or payload.get("Message") or "")
        status = OrderService._normalize_status(status_raw.strip().upper() or ({"place": "PENDING", "modify": "OPEN", "cancel": "CANCELLED"}.get(action, "OPEN")))
        ok = status not in {"FAILED", "REJECTED", "ERROR"}
        message = str(payload.get("message") or payload.get("Message") or status.title())
        return {
            "ok": ok,
            "order_id": order_id,
            "status": status,
            "message": message,
            "raw": payload,
        }

    def _normalize_order_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row or {})
        quantity = self._int_value(payload.get("quantity") or payload.get("Qty") or payload.get("OrderQty"))
        executed_qty = self._int_value(payload.get("executed_qty") or payload.get("ExecutedQty") or payload.get("filled_qty") or payload.get("TradedQty"))
        pending_qty = self._int_value(payload.get("pending_qty") or payload.get("PendingQty") or payload.get("remaining_qty"))
        if pending_qty <= 0:
            pending_qty = max(0, quantity - executed_qty)

        order_time = self._coerce_datetime(
            payload.get("time")
            or payload.get("Time")
            or payload.get("order_time")
            or payload.get("OrderTime")
            or payload.get("BrokerOrderTime")
        )
        side = self._normalize_side(payload.get("side") or payload.get("buy_sell") or payload.get("BuySell") or payload.get("Type"))

        return {
            "order_id": str(payload.get("order_id") or payload.get("OrderID") or payload.get("orderId") or payload.get("ExchOrderID") or ""),
            "symbol": self._clean_symbol(payload.get("symbol") or payload.get("ScripName") or payload.get("trading_symbol") or ""),
            "side": side,
            "quantity": quantity,
            "executed_qty": executed_qty,
            "pending_qty": pending_qty,
            "price": self._float_value(payload.get("price") or payload.get("Price") or payload.get("rate") or payload.get("LimitPrice")),
            "status": self._normalize_status(str(payload.get("status") or payload.get("Status") or "UNKNOWN").upper()),
            "time": order_time.strftime("%H:%M:%S") if order_time else "--",
            "raw": payload,
            "sort_time": order_time or datetime.min,
        }

    def _normalize_trade_row(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row or {})
        trade_time = self._coerce_datetime(payload.get("trade_time") or payload.get("TradeTime") or payload.get("time") or payload.get("Time"))
        return {
            "trade_id": str(payload.get("trade_id") or payload.get("TradeID") or payload.get("tradeId") or ""),
            "order_id": str(payload.get("order_id") or payload.get("OrderID") or payload.get("orderId") or ""),
            "symbol": self._clean_symbol(payload.get("symbol") or payload.get("ScripName") or payload.get("trading_symbol") or ""),
            "side": self._normalize_side(payload.get("side") or payload.get("buy_sell") or payload.get("BuySell") or payload.get("Type")),
            "price": self._float_value(payload.get("price") or payload.get("Price") or payload.get("rate") or payload.get("TradePrice")),
            "quantity": self._int_value(payload.get("quantity") or payload.get("Qty") or payload.get("TradeQty")),
            "exchange": self._clean_exchange(payload.get("exchange") or payload.get("Exchange") or "NSE"),
            "trade_time": trade_time.strftime("%H:%M:%S") if trade_time else "--",
            "raw": payload,
            "sort_time": trade_time or datetime.min,
        }

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            text = value.strip()
            for parser in (
                lambda s: datetime.fromisoformat(s),
                lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
                lambda s: datetime.strptime(s, "%d-%m-%Y %H:%M:%S"),
                lambda s: datetime.strptime(s, "%H:%M:%S"),
            ):
                try:
                    return parser(text)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _normalize_side(value: Any) -> str:
        text = str(value or "").strip().upper()
        if text in {"B", "BUY"}:
            return "BUY"
        if text in {"S", "SELL"}:
            return "SELL"
        return text or "BUY"

    @staticmethod
    def _clean_exchange(exchange: Any) -> str:
        text = str(exchange or "NSE").strip().upper()
        return text or "NSE"

    @staticmethod
    def _clean_symbol(symbol: Any) -> str:
        return str(symbol or "").strip().upper()

    @staticmethod
    def _clean_side(side: Any) -> str:
        text = str(side or "BUY").strip().upper()
        text = "BUY" if text == "B" else "SELL" if text == "S" else text
        if text not in _SIDES:
            raise OrderServiceError("validation_error", "Side must be BUY or SELL")
        return text

    @staticmethod
    def _clean_order_type(order_type: Any) -> str:
        text = str(order_type or "MARKET").strip().upper()
        if text == "BRACKET":
            text = "BRACKET ORDER"
        if text == "COVER":
            text = "COVER ORDER"
        if text not in _ORDER_TYPES:
            raise OrderServiceError("validation_error", "Unsupported order type")
        return text

    @staticmethod
    def _clean_product(product: Any) -> str:
        text = str(product or "CNC").strip().upper()
        if text not in _PRODUCT_TYPES:
            raise OrderServiceError("validation_error", "Unsupported product type")
        return text

    @staticmethod
    def _clean_validity(validity: Any) -> str:
        text = str(validity or "DAY").strip().upper()
        if text not in _VALIDITIES:
            raise OrderServiceError("validation_error", "Unsupported validity")
        return text or "DAY"

    @staticmethod
    def _clean_variety(variety: Any) -> str:
        text = str(variety or "REGULAR").strip().upper()
        if text not in _VARIETIES:
            raise OrderServiceError("validation_error", "Unsupported variety")
        return text

    @staticmethod
    def _clean_quantity(quantity: Any) -> int:
        value = int(quantity or 0)
        if value <= 0:
            raise OrderServiceError("validation_error", "Quantity must be greater than zero")
        return value

    @staticmethod
    def _clean_order_id(order_id: Any) -> str:
        text = str(order_id or "").strip()
        if not text:
            raise OrderServiceError("validation_error", "Order ID is required")
        return text

    @staticmethod
    def _float_value(value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _int_value(value: Any) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    @staticmethod
    def _normalize_status(status: str) -> str:
        text = str(status or "").strip().upper()
        if text in {"PLACED", "PENDING", "PUT ORDER REQ RECEIVED", "REQUESTED"}:
            return "PENDING"
        if text in {"OPEN", "TRIGGER PENDING", "MODIFIED"}:
            return "OPEN"
        if text in {"COMPLETE", "EXECUTED", "FILLED", "SUCCESS"}:
            return "EXECUTED"
        if text in {"REJECTED", "FAILED", "ERROR"}:
            return "REJECTED"
        if text in {"CANCELLED", "CANCELED"}:
            return "CANCELLED"
        if text in {"PARTIAL", "PARTIALLY FILLED", "PARTIAL FILLED"}:
            return "PARTIAL FILLED"
        return text or "PENDING"
