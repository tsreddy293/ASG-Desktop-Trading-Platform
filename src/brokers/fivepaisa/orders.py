from __future__ import annotations

from typing import Any

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.login import FivePaisaLoginService


class FivePaisaOrderService:
    """5paisa order/trade APIs wrapper."""

    def __init__(self, login_service: FivePaisaLoginService) -> None:
        self._login_service = login_service

    def place_order(self, **kwargs) -> dict[str, Any]:
        client = self._login_service.client()
        try:
            return client.place_order(**kwargs)
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def modify_order(self, **kwargs) -> dict[str, Any]:
        client = self._login_service.client()
        try:
            return client.modify_order(**kwargs)
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def cancel_order(self, **kwargs) -> dict[str, Any]:
        client = self._login_service.client()
        try:
            return client.cancel_order(**kwargs)
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        client = self._login_service.client()
        try:
            return list(client.order_book() or [])
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        client = self._login_service.client()
        try:
            return list(client.trade_book() or [])
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc
