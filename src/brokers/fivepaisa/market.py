from __future__ import annotations

from typing import Any

from src.brokers.base_broker import BrokerNotLoggedIn
from src.brokers.fivepaisa.login import FivePaisaLoginService
from src.brokers.fivepaisa.market_data_service import MarketDataService


class FivePaisaMarketService:
    """5paisa market data wrapper."""

    def __init__(self, login_service: FivePaisaLoginService) -> None:
        self._login_service = login_service
        self._market_data = MarketDataService(broker_client=login_service._broker_client)

    @staticmethod
    def _default_symbols() -> list[str]:
        raw = __import__("os").getenv("FIVEPAISA_WATCH_SYMBOLS", "SBIN,RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK")
        return [item.strip().upper() for item in raw.split(",") if item.strip()]

    def get_quote(self, symbol: str, exchange: str = "NSE", **kwargs) -> dict[str, Any]:
        self._require_authenticated()
        return self._market_data.get_quote(symbol)

    def get_quotes(self, symbols: list[str] | None = None, exchange: str = "NSE", **kwargs) -> list[dict[str, Any]]:
        self._require_authenticated()
        if symbols is None:
            return self._market_data.get_watchlist_quotes()
        return self._market_data.get_quotes(symbols)

    def get_ohlc(self, symbol: str, timeframe: str, exchange: str = "NSE") -> dict[str, Any]:
        self._require_authenticated()
        return self._market_data.get_ohlc(symbol, timeframe=timeframe, exchange=exchange)

    def get_option_chain(self, symbol: str, **kwargs) -> dict[str, Any]:
        self._require_authenticated()
        expiry = str(kwargs.get("expiry", "") or "").strip()
        return self._market_data.get_option_chain(symbol, expiry=expiry or None)

    def get_market_depth(self, symbol: str, exchange: str = "NSE", **kwargs) -> dict[str, Any]:
        self._require_authenticated()
        return self._market_data.get_market_depth(symbol)

    def get_historical_data(self, symbol: str, **kwargs) -> list[dict[str, Any]]:
        self._require_authenticated()
        timeframe = str(kwargs.get("timeframe", "15 Minute") or "15 Minute")
        from_date = str(kwargs.get("from_date", "") or "")
        to_date = str(kwargs.get("to_date", "") or "")
        return self._market_data.get_historical_candles(symbol, timeframe, from_date, to_date)

    def _require_authenticated(self) -> None:
        try:
            broker_client = self._login_service._broker_client
            session_manager = broker_client.session_manager
            if session_manager.is_connected() and not broker_client.authentication_in_progress():
                return
        except Exception:
            pass
        raise BrokerNotLoggedIn("Session expired. Please click Connect.")

    def get_indices(self) -> list[dict[str, Any]]:
        self._require_authenticated()
        return self._market_data.get_indices()

    def get_watchlist_quotes(self) -> list[dict[str, Any]]:
        self._require_authenticated()
        return self._market_data.get_watchlist_quotes()
