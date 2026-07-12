from __future__ import annotations

import pytest

from src.services.order_service import OrderServiceError
from src.services.order_validator import OrderValidator, ValidationContext


def test_order_validator_accepts_valid_order() -> None:
    validator = OrderValidator()
    ctx = ValidationContext(available_funds=100_000.0, max_quantity=10_000, freeze_quantity=2_000)

    validator.validate_place(
        {
            "exchange": "NSE",
            "symbol": "SBIN",
            "quantity": 100,
            "lot_size": 10,
            "price": 800.0,
            "required_margin": 5000.0,
        },
        ctx,
    )


def test_order_validator_rejects_invalid_exchange_and_funds() -> None:
    validator = OrderValidator()
    ctx = ValidationContext(available_funds=1000.0, max_quantity=1000, freeze_quantity=500)

    with pytest.raises(OrderServiceError):
        validator.validate_place(
            {
                "exchange": "MCX",
                "symbol": "SBIN",
                "quantity": 10,
                "lot_size": 1,
                "price": 100.0,
            },
            ctx,
        )

    with pytest.raises(OrderServiceError):
        validator.validate_place(
            {
                "exchange": "NSE",
                "symbol": "SBIN",
                "quantity": 100,
                "lot_size": 1,
                "price": 1000.0,
                "required_margin": 10_000.0,
            },
            ctx,
        )


def test_order_validator_rejects_freeze_and_lot_violations() -> None:
    validator = OrderValidator()
    ctx = ValidationContext(available_funds=1_000_000.0, max_quantity=10_000, freeze_quantity=100)

    with pytest.raises(OrderServiceError):
        validator.validate_place(
            {
                "exchange": "NSE",
                "symbol": "SBIN",
                "quantity": 101,
                "lot_size": 1,
                "price": 100.0,
            },
            ctx,
        )

    with pytest.raises(OrderServiceError):
        validator.validate_place(
            {
                "exchange": "NSE",
                "symbol": "SBIN",
                "quantity": 55,
                "lot_size": 10,
                "price": 100.0,
            },
            ctx,
        )
