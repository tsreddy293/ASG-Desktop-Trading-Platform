from __future__ import annotations

from typing import Any

from src.brokers.fivepaisa.market_data_service import MarketDataService


class FivePaisaMarketData(MarketDataService):
    """Backward-compatible wrapper over the centralized MarketDataService."""

    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        return super().get_quote(symbol)

    def get_quotes(self, symbols: list[str], exchange: str = "NSE") -> list[dict[str, Any]]:
        return super().get_quotes(symbols)

    def get_market_depth(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        return super().get_market_depth(symbol)

    def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        return super().get_option_chain(symbol, expiry=expiry)

    def get_historical(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        return super().get_historical_candles(symbol, timeframe, from_date, to_date)

    def get_ohlc(self, symbol: str, timeframe: str, exchange: str = "NSE") -> dict[str, Any]:
        quote = super().get_quote(symbol)
        return {
            "symbol": quote["symbol"],
            "exchange": quote["exchange"],
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "ltp": quote["ltp"],
            "volume": quote["volume"],
            "bid": quote["bid"],
            "ask": quote["ask"],
            "oi": quote.get("oi", 0),
            "timestamp": quote["timestamp"],
        }
