from __future__ import annotations

from src.chart.model import Candle, ChartData, ChartPayload, ChartRequest, IndicatorSeries
from src.marketdata.service import MarketDataService, market_data_service


class ChartService:
    """Service layer for chart data and indicator calculations."""

    def __init__(self, market_service: MarketDataService | None = None) -> None:
        self._market_service = market_service or market_data_service

    def load_chart(self, request: ChartRequest, enabled_indicators: set[str]) -> ChartPayload:
        historical = self._market_service.get_historical_candles(request.symbol, request.exchange, request.timeframe)
        candles = [
            Candle(
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in historical
        ]
        indicators: dict[str, IndicatorSeries] = {}

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [float(c.volume) for c in candles]

        if "EMA" in enabled_indicators:
            indicators["EMA"] = IndicatorSeries("EMA", self._ema(closes, 21))
        if "SMA" in enabled_indicators:
            indicators["SMA"] = IndicatorSeries("SMA", self._sma(closes, 20))
        if "VWAP" in enabled_indicators:
            indicators["VWAP"] = IndicatorSeries("VWAP", self._vwap(candles))
        if "Bollinger Bands" in enabled_indicators:
            mid, upper, lower = self._bollinger(closes, 20, 2.0)
            indicators["BB_MID"] = IndicatorSeries("BB_MID", mid)
            indicators["BB_UPPER"] = IndicatorSeries("BB_UPPER", upper)
            indicators["BB_LOWER"] = IndicatorSeries("BB_LOWER", lower)
        if "RSI" in enabled_indicators:
            indicators["RSI"] = IndicatorSeries("RSI", self._rsi(closes, 14))
        if "MACD" in enabled_indicators:
            macd, signal = self._macd(closes)
            indicators["MACD"] = IndicatorSeries("MACD", macd)
            indicators["MACD_SIGNAL"] = IndicatorSeries("MACD_SIGNAL", signal)
        if "ATR" in enabled_indicators:
            indicators["ATR"] = IndicatorSeries("ATR", self._atr(highs, lows, closes, 14))
        if "ADX" in enabled_indicators:
            indicators["ADX"] = IndicatorSeries("ADX", self._adx(highs, lows, closes, 14))
        if "SuperTrend" in enabled_indicators:
            indicators["SuperTrend"] = IndicatorSeries("SuperTrend", self._supertrend(highs, lows, closes, 10, 3.0))
        if "Volume" in enabled_indicators:
            indicators["Volume"] = IndicatorSeries("Volume", volumes)

        return ChartPayload(
            data=ChartData(symbol=request.symbol, exchange=request.exchange, timeframe=request.timeframe, candles=candles),
            indicators=indicators,
            last_price=candles[-1].close if candles else 0.0,
        )

    @staticmethod
    def _sma(values: list[float], period: int) -> list[float | None]:
        out: list[float | None] = [None] * len(values)
        if period <= 0:
            return out
        rolling = 0.0
        for i, value in enumerate(values):
            rolling += value
            if i >= period:
                rolling -= values[i - period]
            if i >= period - 1:
                out[i] = rolling / period
        return out

    @staticmethod
    def _ema(values: list[float], period: int) -> list[float | None]:
        out: list[float | None] = [None] * len(values)
        if not values or period <= 0:
            return out
        multiplier = 2 / (period + 1)
        ema_val = values[0]
        out[0] = ema_val
        for i in range(1, len(values)):
            ema_val = (values[i] - ema_val) * multiplier + ema_val
            out[i] = ema_val
        return out

    @staticmethod
    def _vwap(candles: list[Candle]) -> list[float | None]:
        out: list[float | None] = [None] * len(candles)
        cum_pv = 0.0
        cum_vol = 0.0
        for i, candle in enumerate(candles):
            typical = (candle.high + candle.low + candle.close) / 3
            cum_pv += typical * candle.volume
            cum_vol += candle.volume
            out[i] = cum_pv / cum_vol if cum_vol else None
        return out

    @staticmethod
    def _bollinger(values: list[float], period: int, std_mult: float) -> tuple[list[float | None], list[float | None], list[float | None]]:
        mid = ChartService._sma(values, period)
        upper: list[float | None] = [None] * len(values)
        lower: list[float | None] = [None] * len(values)
        for i in range(period - 1, len(values)):
            window = values[i - period + 1 : i + 1]
            mean = mid[i] or 0.0
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper[i] = mean + std_mult * std
            lower[i] = mean - std_mult * std
        return mid, upper, lower

    @staticmethod
    def _rsi(values: list[float], period: int) -> list[float | None]:
        out: list[float | None] = [None] * len(values)
        if len(values) < period + 1:
            return out
        gains = []
        losses = []
        for i in range(1, len(values)):
            delta = values[i] - values[i - 1]
            gains.append(max(delta, 0.0))
            losses.append(abs(min(delta, 0.0)))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        out[period] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

        for i in range(period + 1, len(values)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i - 1]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i - 1]) / period
            out[i] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))
        return out

    @staticmethod
    def _macd(values: list[float]) -> tuple[list[float | None], list[float | None]]:
        ema12 = ChartService._ema(values, 12)
        ema26 = ChartService._ema(values, 26)
        macd: list[float | None] = [None] * len(values)
        for i in range(len(values)):
            if ema12[i] is None or ema26[i] is None:
                continue
            macd[i] = ema12[i] - ema26[i]

        macd_values = [m if m is not None else 0.0 for m in macd]
        signal = ChartService._ema(macd_values, 9)
        return macd, signal

    @staticmethod
    def _atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float | None]:
        tr: list[float] = []
        for i in range(len(highs)):
            if i == 0:
                tr.append(highs[i] - lows[i])
            else:
                tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
        return ChartService._sma(tr, period)

    @staticmethod
    def _adx(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float | None]:
        # Simplified ADX approximation for mock visualization.
        atr = ChartService._atr(highs, lows, closes, period)
        out: list[float | None] = [None] * len(highs)
        for i in range(len(highs)):
            if atr[i] is None:
                continue
            out[i] = min(60.0, 14.0 + (atr[i] * 2.5))
        return out

    @staticmethod
    def _supertrend(highs: list[float], lows: list[float], closes: list[float], period: int, multiplier: float) -> list[float | None]:
        atr = ChartService._atr(highs, lows, closes, period)
        out: list[float | None] = [None] * len(highs)
        for i in range(len(highs)):
            if atr[i] is None:
                continue
            hl2 = (highs[i] + lows[i]) / 2
            out[i] = hl2 - (multiplier * atr[i])
        return out
