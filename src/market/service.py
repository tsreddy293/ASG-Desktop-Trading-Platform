from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.marketdata.service import MarketDataService as CentralMarketDataService
from src.marketdata.service import market_data_service


@dataclass(slots=True)
class MarketQuote:
    symbol: str
    company: str
    price: float
    change_percent: float
    volume: int
    trend: str


@dataclass(slots=True)
class OptionChainRow:
    strike_price: float
    ce_ltp: float
    ce_oi: int
    ce_change_oi: int
    pe_oi: int
    pe_change_oi: int
    pe_ltp: float
    iv: float
    pcr: float


@dataclass(slots=True)
class MarketDepthOrder:
    price: float
    quantity: int
    orders: int


@dataclass(slots=True)
class OptionChainSnapshot:
    underlying: str
    expiry: str
    spot_price: float
    atm_strike: int
    pcr: float
    iv: float
    last_updated: datetime
    rows: list[OptionChainRow]


@dataclass(slots=True)
class MarketDepthSnapshot:
    symbol: str
    company: str
    exchange: str
    ltp: float
    change_percent: float
    bid: float
    ask: float
    spread: float
    volume: int
    last_updated: datetime
    buy_orders: list[MarketDepthOrder]
    sell_orders: list[MarketDepthOrder]


class MarketDataProvider(Protocol):
    def get_quotes(self) -> list[MarketQuote]:
        ...


class SampleMarketDataProvider:
    """Compatibility provider that proxies centralized live service."""

    def get_quotes(self) -> list[MarketQuote]:
        rows = market_data_service.get_live_quotes("NSE", "")
        return [
            MarketQuote(
                symbol=row.symbol,
                company=row.company,
                price=row.ltp,
                change_percent=row.change_percent,
                volume=row.volume,
                trend="Up" if row.change_percent >= 0 else "Down",
            )
            for row in rows
        ]


class LiveMarketDataProvider:
    """Placeholder provider for a future live market data feed."""

    def get_quotes(self) -> list[MarketQuote]:
        return SampleMarketDataProvider().get_quotes()


class MarketWatchService:
    """Application service that supplies market data to the UI layer."""

    def __init__(self, provider: MarketDataProvider | None = None) -> None:
        self._provider = provider
        self._central_service: CentralMarketDataService = market_data_service
        self._preferred_order = ["SBIN", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "ITC", "LT", "AXISBANK", "BAJFINANCE"]

    def get_quotes(self) -> list[MarketQuote]:
        if self._provider is not None:
            return self._provider.get_quotes()

        rows = self._central_service.get_live_quotes("NSE", "")
        quotes = [
            MarketQuote(
                symbol=row.symbol,
                company=row.company,
                price=row.ltp,
                change_percent=row.change_percent,
                volume=row.volume,
                trend="Up" if row.change_percent >= 0 else "Down",
            )
            for row in rows
        ]
        if quotes:
            return self._sort_quotes(quotes)
        return self._sort_quotes(self._fallback_quotes())

    def _sort_quotes(self, quotes: list[MarketQuote]) -> list[MarketQuote]:
        rank = {symbol: index for index, symbol in enumerate(self._preferred_order)}
        return sorted(quotes, key=lambda row: rank.get(row.symbol, 9999))

    @staticmethod
    def _fallback_quotes() -> list[MarketQuote]:
        return [
            MarketQuote("SBIN", "State Bank of India", 812.25, 1.45, 1220000, "Up"),
            MarketQuote("RELIANCE", "Reliance Industries", 2922.30, 0.82, 985000, "Up"),
            MarketQuote("TCS", "Tata Consultancy Services", 4165.40, -0.34, 610000, "Down"),
            MarketQuote("INFY", "Infosys", 1850.75, 0.61, 734000, "Up"),
            MarketQuote("HDFCBANK", "HDFC Bank", 1703.15, 0.95, 1410000, "Up"),
            MarketQuote("ICICIBANK", "ICICI Bank", 1234.80, 0.77, 1120000, "Up"),
            MarketQuote("ITC", "ITC Limited", 453.25, -0.18, 2100000, "Down"),
            MarketQuote("LT", "Larsen & Toubro", 3812.55, 0.43, 544000, "Up"),
            MarketQuote("AXISBANK", "Axis Bank", 1321.10, -0.11, 803000, "Down"),
            MarketQuote("BAJFINANCE", "Bajaj Finance", 7448.20, 1.16, 398000, "Up"),
        ]

    def set_provider(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def get_option_chain_rows(self, underlying: str) -> list[OptionChainRow]:
        snapshot = self.get_option_chain_snapshot(underlying, self.get_option_chain_expiries(underlying)[0])
        return [
            OptionChainRow(
                strike_price=row.strike_price,
                ce_ltp=row.ce_ltp,
                ce_oi=row.ce_oi,
                ce_change_oi=row.ce_change_oi,
                pe_oi=row.pe_oi,
                pe_change_oi=row.pe_change_oi,
                pe_ltp=row.pe_ltp,
                iv=row.iv,
                pcr=row.pcr,
            )
            for row in snapshot.rows
        ]

    def get_market_depth(self, symbol: str) -> tuple[list[MarketDepthOrder], list[MarketDepthOrder]]:
        snapshot = self._central_service.get_market_depth(symbol, "NSE")
        buy_orders = [MarketDepthOrder(level.price, level.quantity, level.orders) for level in snapshot.buy_levels]
        sell_orders = [MarketDepthOrder(level.price, level.quantity, level.orders) for level in snapshot.sell_levels]
        return buy_orders, sell_orders

    def get_market_depth_symbols(self) -> list[str]:
        symbols = [quote.symbol for quote in self.get_quotes()]
        return symbols or ["SBIN"]

    def get_option_chain_underlyings(self) -> list[str]:
        return ["NIFTY", "BANKNIFTY", "FINNIFTY"]

    def get_option_chain_expiries(self, underlying: str) -> list[str]:
        return ["31 Jul 2026", "07 Aug 2026", "14 Aug 2026"]

    def get_option_chain_snapshot(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        normalized_underlying = (underlying or "NIFTY").upper()
        central_snapshot = self._central_service.get_option_chain(normalized_underlying, expiry)
        rows = [
            OptionChainRow(
                strike_price=row.strike_price,
                ce_ltp=row.ce_ltp,
                ce_oi=row.ce_oi,
                ce_change_oi=row.ce_change_oi,
                pe_oi=row.pe_oi,
                pe_change_oi=row.pe_change_oi,
                pe_ltp=row.pe_ltp,
                iv=row.iv,
                pcr=row.pcr,
            )
            for row in central_snapshot.rows
        ]
        return OptionChainSnapshot(
            underlying=normalized_underlying,
            expiry=expiry,
            spot_price=central_snapshot.spot_price,
            atm_strike=central_snapshot.atm_strike,
            pcr=central_snapshot.pcr,
            iv=central_snapshot.iv,
            last_updated=central_snapshot.timestamp,
            rows=rows,
        )

    def get_market_depth_snapshot(self, symbol: str, exchange: str = "NSE") -> MarketDepthSnapshot:
        central = self._central_service.get_market_depth(symbol, exchange)
        quote = self._quote_by_symbol(central.symbol)
        buy_orders, sell_orders = self.get_market_depth(central.symbol)
        return MarketDepthSnapshot(
            symbol=central.symbol,
            company=quote.company,
            exchange=central.exchange,
            ltp=central.ask,
            change_percent=quote.change_percent,
            bid=central.bid,
            ask=central.ask,
            spread=central.spread,
            volume=quote.volume,
            last_updated=central.timestamp,
            buy_orders=buy_orders,
            sell_orders=sell_orders,
        )

    def _quote_by_symbol(self, symbol: str) -> MarketQuote:
        normalized_symbol = (symbol or "").upper()
        for quote in self.get_quotes():
            if quote.symbol == normalized_symbol:
                return quote
        quotes = self.get_quotes()
        if quotes:
            return quotes[0]
        return MarketQuote(
            symbol=normalized_symbol or "UNKNOWN",
            company=normalized_symbol or "Unknown",
            price=0.0,
            change_percent=0.0,
            volume=0,
            trend="Neutral",
        )
