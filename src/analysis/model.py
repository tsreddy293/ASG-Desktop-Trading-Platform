from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AIAnalysisRequest:
    symbol: str
    exchange: str
    sector: str | None = None


@dataclass(slots=True)
class AIAnalysisSnapshot:
    symbol: str
    stock_name: str
    exchange: str
    sector: str
    current_price: float
    todays_change_percent: float
    volume: int
    signal: str
    ai_score: int
    confidence_percent: float
    trend: str
    risk: str
    support: float
    resistance: float
    target_1: float
    target_2: float
    stop_loss: float
    rsi: float
    macd: float
    ema: str
    vwap: str
    adx: float
    atr: float
    supertrend: str
    delivery_percent: float
    volume_analysis: str
    reasons: list[str]
    ai_summary: str
    recent_signals: list[str]
    trend_strength: int
    momentum: int
    volume_strength: int
    confidence_meter: int
    candles: list[tuple[float, float, float, float]]
    last_updated: datetime
