from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class WatchQuote:
    symbol: str
    ltp: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    bid: float
    ask: float
    timestamp: datetime | None


@dataclass(slots=True)
class QuoteDetails:
    symbol: str
    ltp: float | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    upper_circuit: float | None
    lower_circuit: float | None
    week_52_high: float | None
    week_52_low: float | None
    volume: int | None
    bid: float | None
    ask: float | None
    last_trade_time: datetime | None


@dataclass(slots=True)
class DepthLevel:
    bid_qty: int
    bid_price: float
    ask_price: float
    ask_qty: int


@dataclass(slots=True)
class MarketDepthSnapshot:
    symbol: str
    levels: list[DepthLevel]
    timestamp: datetime | None


@dataclass(slots=True)
class MarketWatchState:
    connected: bool
    last_updated: datetime | None
    quotes: list[WatchQuote]
    depth: MarketDepthSnapshot | None
    error: str | None
