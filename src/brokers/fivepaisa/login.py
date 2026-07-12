from __future__ import annotations

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.core.logger import app_logger


class FivePaisaLoginService:
    """Compatibility login service backed by new XStream client/session flow."""

    def __init__(self) -> None:
        self._broker_client = FivePaisaBrokerClient()
        self._client = None

    def login(self) -> None:
        # Auto-authenticates via OAuth callback flow when no valid session exists.
        self._broker_client.ensure_authenticated()
        app_logger.info("5paisa session validated")

    def logout(self) -> None:
        self._broker_client.logout()
        self._client = None

    def is_logged_in(self) -> bool:
        return self._broker_client.is_authenticated()

    def login_url(self) -> str:
        return self._broker_client.generate_login_url()

    def authenticate_callback(self, callback_url: str) -> None:
        self._broker_client.authenticate_from_callback(callback_url)

    def client(self):
        raise BrokerConnectionError("Broker connection unavailable.")
