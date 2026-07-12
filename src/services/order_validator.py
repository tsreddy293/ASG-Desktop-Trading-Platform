from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.services.order_service import OrderServiceError


@dataclass(slots=True)
class ValidationContext:
    available_funds: float = 1_000_000.0
    max_quantity: int = 100_000
    freeze_quantity: int = 1_800


class OrderValidator:
    """Validates order payloads for risk and exchange rules before broker submission."""

    _VALID_EXCHANGES = {"NSE", "BSE"}

    def validate_place(self, payload: dict[str, Any], context: ValidationContext | None = None) -> None:
        ctx = context or ValidationContext()
        self._validate_common(payload, ctx)

        qty = int(payload.get("quantity", 0) or 0)
        lot_size = int(payload.get("lot_size", 1) or 1)
        if lot_size <= 0:
            raise OrderServiceError("validation_error", "Lot size must be greater than zero")
        if qty % lot_size != 0:
            raise OrderServiceError("validation_error", "Quantity must align with lot size")

        if qty > ctx.max_quantity:
            raise OrderServiceError("validation_error", f"Quantity exceeds maximum allowed ({ctx.max_quantity})")
        if qty > ctx.freeze_quantity:
            raise OrderServiceError("validation_error", f"Quantity exceeds freeze quantity ({ctx.freeze_quantity})")

        price = float(payload.get("price", 0.0) or 0.0)
        auto_price = bool(payload.get("auto_price", False))
        if auto_price and price <= 0:
            ltp = float(payload.get("ltp", 0.0) or 0.0)
            if ltp > 0:
                price = ltp

        required_margin = float(payload.get("required_margin", 0.0) or 0.0)
        if required_margin <= 0:
            implied = price if price > 0 else float(payload.get("ltp", 0.0) or 0.0)
            required_margin = max(0.0, qty * implied * 0.20)

        if required_margin > ctx.available_funds:
            raise OrderServiceError("validation_error", "Insufficient funds / margin")

    def validate_modify(self, payload: dict[str, Any], context: ValidationContext | None = None) -> None:
        ctx = context or ValidationContext()
        qty = payload.get("quantity")
        if qty is not None:
            quantity = int(qty or 0)
            if quantity <= 0:
                raise OrderServiceError("validation_error", "Quantity must be greater than zero")
            if quantity > ctx.max_quantity:
                raise OrderServiceError("validation_error", f"Quantity exceeds maximum allowed ({ctx.max_quantity})")
            if quantity > ctx.freeze_quantity:
                raise OrderServiceError("validation_error", f"Quantity exceeds freeze quantity ({ctx.freeze_quantity})")

        trigger = payload.get("trigger_price")
        if trigger is not None and float(trigger or 0.0) < 0:
            raise OrderServiceError("validation_error", "Trigger price cannot be negative")

        price = payload.get("price")
        if price is not None and float(price or 0.0) < 0:
            raise OrderServiceError("validation_error", "Price cannot be negative")

    def _validate_common(self, payload: dict[str, Any], _ctx: ValidationContext) -> None:
        exchange = str(payload.get("exchange", "")).strip().upper()
        if exchange not in self._VALID_EXCHANGES:
            raise OrderServiceError("validation_error", "Exchange validation failed")

        symbol = str(payload.get("symbol", "")).strip().upper()
        if not symbol:
            raise OrderServiceError("validation_error", "Symbol is required")

        quantity = int(payload.get("quantity", 0) or 0)
        if quantity <= 0:
            raise OrderServiceError("validation_error", "Quantity must be greater than zero")
