from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(slots=True)
class ChartRequest:
    symbol: str
    exchange: str
    timeframe: str


@dataclass(slots=True)
class ChartData:
    symbol: str
    exchange: str
    timeframe: str
    candles: list[Candle]


@dataclass(slots=True)
class IndicatorSeries:
    name: str
    values: list[float | None]


@dataclass(slots=True)
class ChartPayload:
    data: ChartData
    indicators: dict[str, IndicatorSeries]
    last_price: float


class ChartModel:
    """Compatibility model wrapper for MVC naming conventions."""

    Candle = Candle
    ChartRequest = ChartRequest
    ChartData = ChartData
    IndicatorSeries = IndicatorSeries
    ChartPayload = ChartPayload
