from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BrokerError(Exception):
    """Base exception for broker-related errors."""


class BrokerConnectionError(BrokerError):
    """Raised when broker connection or auth is unavailable."""


class BaseBroker(ABC):
    """Abstract broker contract for all integrations."""

    name: str

    @abstractmethod
    def login(self) -> None:
        ...

    @abstractmethod
    def logout(self) -> None:
        ...

    @abstractmethod
    def is_logged_in(self) -> bool:
        ...

    @abstractmethod
    def get_profile(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_quote(self, symbol: str, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_quotes(self, symbols: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_option_chain(self, symbol: str, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_market_depth(self, symbol: str, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_historical_data(self, symbol: str, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def place_order(self, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def modify_order(self, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def cancel_order(self, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_order_book(self, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_trade_book(self, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_positions(self, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_holdings(self, **kwargs) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_funds(self, **kwargs) -> dict[str, Any]:
        ...
