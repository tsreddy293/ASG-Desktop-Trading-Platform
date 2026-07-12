from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter

from src.chart.model import ChartRequest
from src.chart.service import ChartService
from src.chart.widget import ChartWidget


@dataclass(slots=True)
class _Hist:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class _FakeMarketService:
    def __init__(self, candle_count: int = 12_000) -> None:
        self._rows: list[_Hist] = []
        now = datetime.now(UTC)
        for idx in range(candle_count):
            ts = now - timedelta(minutes=(candle_count - idx))
            base = 800.0 + (idx * 0.02)
            close = base + (0.3 if idx % 2 == 0 else -0.2)
            self._rows.append(_Hist(ts, base, max(base, close) + 0.5, min(base, close) - 0.5, close, 10_000 + idx))

    def get_historical_candles(self, symbol: str, exchange: str, timeframe: str):
        return self._rows


def test_chart_service_handles_10000_plus_candles() -> None:
    service = ChartService(market_service=_FakeMarketService())
    start = perf_counter()
    payload = service.load_chart(
        ChartRequest(symbol="SBIN", exchange="NSE", timeframe="1 Minute"),
        {"EMA", "SMA", "VWAP", "RSI", "MACD", "Bollinger Bands", "ATR", "ADX", "SuperTrend"},
    )
    elapsed = perf_counter() - start

    assert len(payload.data.candles) == 12_000
    assert "ATR" in payload.indicators
    assert "ADX" in payload.indicators
    assert elapsed < 3.0


def test_chart_widget_decimation_for_large_draw_sets() -> None:
    candles = list(range(20_000))
    reduced = ChartWidget._decimate_if_needed(candles, max_points=600)

    assert len(reduced) <= 600
    assert reduced[0] == 0
