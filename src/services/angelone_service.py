from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Protocol

from src.marketdata.model import HistoricalCandle, MarketDepthLevel, MarketDepthSnapshot, MarketInstrument, OptionChainRow, OptionChainSnapshot, OrderRecord, PortfolioPosition


class MarketDataProvider(Protocol):
    name: str

    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...

    def supports_websocket(self) -> bool:
        ...

    def fetch_live_quotes(self, exchange: str, instrument_type: str = "EQUITY") -> list[MarketInstrument]:
        ...

    def fetch_market_depth(self, symbol: str, exchange: str) -> MarketDepthSnapshot:
        ...

    def fetch_option_chain(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        ...

    def fetch_historical_candles(self, symbol: str, exchange: str, timeframe: str) -> list[HistoricalCandle]:
        ...

    def fetch_portfolio_positions(self) -> list[PortfolioPosition]:
        ...

    def fetch_orders(self) -> list[OrderRecord]:
        ...


class AngelOneService:
    """Angel One provider abstraction.

    This class is intentionally API-agnostic for production replaceability.
    Real request wiring should be added with broker credentials.
    """

    name = "angelone"

    def __init__(self) -> None:
        self._connected = False
        self._api_key = os.getenv("ANGELONE_API_KEY", "").strip()
        self._access_token = os.getenv("ANGELONE_ACCESS_TOKEN", "").strip()

    def connect(self) -> None:
        if not self._api_key or not self._access_token:
            raise RuntimeError("Angel One credentials not configured")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def supports_websocket(self) -> bool:
        return True

    def fetch_live_quotes(self, exchange: str, instrument_type: str = "EQUITY") -> list[MarketInstrument]:
        raise RuntimeError("Angel One live quote fetch is not configured in this environment")

    def fetch_market_depth(self, symbol: str, exchange: str) -> MarketDepthSnapshot:
        now = datetime.now(timezone.utc)
        return MarketDepthSnapshot(
            symbol=symbol,
            exchange=exchange,
            bid=0.0,
            ask=0.0,
            spread=0.0,
            buy_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)],
            sell_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)],
            timestamp=now,
        )

    def fetch_option_chain(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        now = datetime.now(timezone.utc)
        return OptionChainSnapshot(
            underlying=underlying,
            expiry=expiry,
            spot_price=0.0,
            atm_strike=0,
            pcr=0.0,
            iv=0.0,
            rows=[
                OptionChainRow(
                    strike_price=0,
                    ce_ltp=0.0,
                    ce_oi=0,
                    ce_change_oi=0,
                    pe_oi=0,
                    pe_change_oi=0,
                    pe_ltp=0.0,
                    iv=0.0,
                    pcr=0.0,
                )
            ],
            timestamp=now,
        )

    def fetch_historical_candles(self, symbol: str, exchange: str, timeframe: str) -> list[HistoricalCandle]:
        return []

    def fetch_portfolio_positions(self) -> list[PortfolioPosition]:
        return []

    def fetch_orders(self) -> list[OrderRecord]:
        return []
