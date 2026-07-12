from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ScannerFilters:
    exchange: str
    segment: str
    scanner: str
    market_cap: str
    sector: str
    minimum_volume: int
    minimum_price: float
    maximum_price: float


@dataclass(slots=True)
class ScannerRow:
    symbol: str
    company: str
    sector: str
    ltp: float
    change_percent: float
    volume: int
    delivery_percent: float
    rsi: float
    macd: float
    ema_trend: str
    vwap_position: str
    ai_score: int
    signal: str
    confidence_percent: float
    risk: str
    target: float
    stop_loss: float


@dataclass(slots=True)
class ScannerSummary:
    stocks_scanned: int
    stocks_qualified: int
    scan_time_seconds: float
    last_updated: datetime
