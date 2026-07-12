from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MarketEventType(str, Enum):
    TICK = "tick"
    CONNECTION = "connection"
    ERROR = "error"


@dataclass(slots=True)
class MarketInstrument:
    symbol: str
    company: str
    sector: str
    exchange: str
    ltp: float
    open: float
    high: float
    low: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    bid: float
    ask: float
    timestamp: datetime


@dataclass(slots=True)
class MarketDepthLevel:
    price: float
    quantity: int
    orders: int


@dataclass(slots=True)
class MarketDepthSnapshot:
    symbol: str
    exchange: str
    bid: float
    ask: float
    spread: float
    buy_levels: list[MarketDepthLevel]
    sell_levels: list[MarketDepthLevel]
    timestamp: datetime


@dataclass(slots=True)
class OptionChainRow:
    strike_price: int
    ce_ltp: float
    ce_oi: int
    pe_oi: int
    pe_ltp: float
    iv: float
    pcr: float
    ce_change_oi: int = 0
    pe_change_oi: int = 0


@dataclass(slots=True)
class OptionChainSnapshot:
    underlying: str
    expiry: str
    spot_price: float
    atm_strike: int
    pcr: float
    iv: float
    rows: list[OptionChainRow]
    timestamp: datetime


@dataclass(slots=True)
class HistoricalCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(slots=True)
class PortfolioPosition:
    symbol: str
    company: str
    quantity: int
    average_price: float
    ltp: float
    pnl_percent: float


@dataclass(slots=True)
class OrderRecord:
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    status: str


@dataclass(slots=True)
class MarketDataEvent:
    event_type: MarketEventType
    symbols: list[str]
    timestamp: datetime
    message: str = ""


class MarketDataModel:
    MarketInstrument = MarketInstrument
    MarketDepthSnapshot = MarketDepthSnapshot
    OptionChainSnapshot = OptionChainSnapshot
    HistoricalCandle = HistoricalCandle
    PortfolioPosition = PortfolioPosition
    OrderRecord = OrderRecord
    Event = MarketDataEvent
