from __future__ import annotations

from typing import Any

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.login import FivePaisaLoginService


class FivePaisaPortfolioService:
    """5paisa portfolio/profile APIs wrapper."""

    def __init__(self, login_service: FivePaisaLoginService) -> None:
        self._login_service = login_service

    def get_profile(self) -> dict[str, Any]:
        client = self._login_service.client()
        try:
            return dict(client.get_user_info() or {})
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def get_positions(self, **kwargs) -> list[dict[str, Any]]:
        client = self._login_service.client()
        try:
            return list(client.positions() or [])
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def get_holdings(self, **kwargs) -> list[dict[str, Any]]:
        client = self._login_service.client()
        try:
            return list(client.holdings() or [])
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc

    def get_funds(self, **kwargs) -> dict[str, Any]:
        client = self._login_service.client()
        try:
            return dict(client.margin() or {})
        except Exception as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc
