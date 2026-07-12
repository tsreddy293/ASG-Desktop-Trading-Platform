from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.core.logger import app_logger
from src.core.translation import t
from src.marketdata.model import HistoricalCandle, MarketInstrument
from src.marketdata.service import market_data_service


class CandleDataSource(Protocol):
    def get_historical_candles(self, symbol: str, exchange: str, timeframe: str):
        ...

    def get_quote(self, symbol: str, exchange: str):
        ...


class MarketDataCandleSource:
    def get_historical_candles(self, symbol: str, exchange: str, timeframe: str):
        return market_data_service.get_historical_candles(symbol, exchange, timeframe)

    def get_quote(self, symbol: str, exchange: str):
        return market_data_service.get_quote(symbol, exchange)


@dataclass(slots=True)
class IndicatorSnapshot:
    ema20: float
    ema50: float
    ema200: float
    rsi: float
    macd: float
    macd_signal: float
    vwap: float
    atr: float
    adx: float
    supertrend: float
    supertrend_bullish: bool
    bb_upper: float
    bb_mid: float
    bb_lower: float
    pivot: float
    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float
    cpr_pivot: float
    cpr_bc: float
    cpr_tc: float


@dataclass(slots=True)
class SignalSnapshot:
    trend_up: bool
    trend_down: bool
    momentum_up: bool
    momentum_down: bool
    vwap_above: bool
    adx_strong: bool
    near_support: bool
    near_resistance: bool


@dataclass(slots=True)
class ScoreBreakdown:
    trend: int
    momentum: int
    price_action: int
    support_resistance: int
    vwap: int
    adx: int
    volume: int
    delivery: int
    total: int


@dataclass(slots=True)
class AnalysisResult:
    symbol: str
    exchange: str
    quote: MarketInstrument
    candles: list[HistoricalCandle]
    indicators: IndicatorSnapshot
    signals: SignalSnapshot
    recommendation: str
    signal_strength: str
    mixed_signal: bool
    score: ScoreBreakdown
    confidence_percent: float
    recommendation_reason: str
    reasons: list[str]
    summary: str
    risk: str
    target_1: float
    target_2: float
    stop_loss: float
    delivery_percent: float


class IndicatorEngine:
    def calculate(self, candles: list[HistoricalCandle]) -> IndicatorSnapshot:
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [float(c.volume) for c in candles]

        ema20_series = self._ema_series(closes, 20)
        ema50_series = self._ema_series(closes, 50)
        ema200_series = self._ema_series(closes, 200)
        rsi_series = self._rsi_series(closes, 14)
        macd_series, macd_signal_series = self._macd_series(closes)
        vwap_series = self._vwap_series(highs, lows, closes, volumes)
        atr_series = self._atr_series(highs, lows, closes, 14)
        adx_series = self._adx_series(highs, lows, closes, 14)
        supertrend_series, supertrend_bullish = self._supertrend_series(highs, lows, closes, 10, 3.0)
        bb_mid, bb_upper, bb_lower = self._bollinger_series(closes, 20, 2.0)

        pivot_h, pivot_l, pivot_c = self._pivot_base(candles)
        pivot = (pivot_h + pivot_l + pivot_c) / 3
        support_1 = (2 * pivot) - pivot_h
        resistance_1 = (2 * pivot) - pivot_l
        support_2 = pivot - (pivot_h - pivot_l)
        resistance_2 = pivot + (pivot_h - pivot_l)
        bc = (pivot_h + pivot_l) / 2
        tc = (2 * pivot) - bc

        return IndicatorSnapshot(
            ema20=ema20_series[-1],
            ema50=ema50_series[-1],
            ema200=ema200_series[-1],
            rsi=rsi_series[-1],
            macd=macd_series[-1],
            macd_signal=macd_signal_series[-1],
            vwap=vwap_series[-1],
            atr=atr_series[-1],
            adx=adx_series[-1],
            supertrend=supertrend_series[-1],
            supertrend_bullish=supertrend_bullish[-1],
            bb_upper=bb_upper[-1],
            bb_mid=bb_mid[-1],
            bb_lower=bb_lower[-1],
            pivot=pivot,
            support_1=support_1,
            support_2=support_2,
            resistance_1=resistance_1,
            resistance_2=resistance_2,
            cpr_pivot=pivot,
            cpr_bc=min(bc, tc),
            cpr_tc=max(bc, tc),
        )

    @staticmethod
    def _ema_series(values: list[float], period: int) -> list[float]:
        if not values:
            return [0.0]
        mul = 2.0 / (period + 1)
        ema = values[0]
        out = [ema]
        for value in values[1:]:
            ema = ((value - ema) * mul) + ema
            out.append(ema)
        return out

    @staticmethod
    def _rsi_series(values: list[float], period: int) -> list[float]:
        if len(values) < 2:
            return [50.0]
        gains: list[float] = []
        losses: list[float] = []
        for index in range(1, len(values)):
            delta = values[index] - values[index - 1]
            gains.append(max(delta, 0.0))
            losses.append(max(-delta, 0.0))

        if len(gains) < period:
            mean_gain = sum(gains) / max(1, len(gains))
            mean_loss = sum(losses) / max(1, len(losses))
            rs = mean_gain / mean_loss if mean_loss > 0 else 100.0
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return [rsi] * len(values)

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        out = [50.0] * len(values)
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        out[period] = 100.0 - (100.0 / (1.0 + rs))

        for index in range(period + 1, len(values)):
            avg_gain = ((avg_gain * (period - 1)) + gains[index - 1]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[index - 1]) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
            out[index] = 100.0 - (100.0 / (1.0 + rs))
        return out

    def _macd_series(self, values: list[float]) -> tuple[list[float], list[float]]:
        ema12 = self._ema_series(values, 12)
        ema26 = self._ema_series(values, 26)
        size = min(len(ema12), len(ema26))
        macd = [ema12[i] - ema26[i] for i in range(size)]
        signal = self._ema_series(macd, 9)
        return macd, signal

    @staticmethod
    def _vwap_series(highs: list[float], lows: list[float], closes: list[float], volumes: list[float]) -> list[float]:
        out: list[float] = []
        cum_pv = 0.0
        cum_vol = 0.0
        for idx in range(len(closes)):
            typical = (highs[idx] + lows[idx] + closes[idx]) / 3
            cum_pv += typical * volumes[idx]
            cum_vol += volumes[idx]
            out.append(cum_pv / cum_vol if cum_vol else typical)
        return out or [0.0]

    @staticmethod
    def _atr_series(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float]:
        tr: list[float] = []
        for idx in range(len(highs)):
            if idx == 0:
                tr.append(highs[idx] - lows[idx])
            else:
                tr.append(max(highs[idx] - lows[idx], abs(highs[idx] - closes[idx - 1]), abs(lows[idx] - closes[idx - 1])))

        if len(tr) <= period:
            mean_tr = sum(tr) / max(1, len(tr))
            return [mean_tr] * len(tr)

        atr = [tr[0]]
        for idx in range(1, len(tr)):
            if idx < period:
                atr.append((atr[-1] * idx + tr[idx]) / (idx + 1))
            else:
                atr.append(((atr[-1] * (period - 1)) + tr[idx]) / period)
        return atr

    def _adx_series(self, highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float]:
        length = len(highs)
        if length < 3:
            return [20.0] * max(1, length)

        tr = [0.0]
        plus_dm = [0.0]
        minus_dm = [0.0]

        for idx in range(1, length):
            up_move = highs[idx] - highs[idx - 1]
            down_move = lows[idx - 1] - lows[idx]
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
            tr.append(max(highs[idx] - lows[idx], abs(highs[idx] - closes[idx - 1]), abs(lows[idx] - closes[idx - 1])))

        atr = self._atr_series(highs, lows, closes, period)
        plus_di = [0.0] * length
        minus_di = [0.0] * length

        plus_smoothed = sum(plus_dm[1 : period + 1])
        minus_smoothed = sum(minus_dm[1 : period + 1])
        for idx in range(period, length):
            if idx > period:
                plus_smoothed = plus_smoothed - (plus_smoothed / period) + plus_dm[idx]
                minus_smoothed = minus_smoothed - (minus_smoothed / period) + minus_dm[idx]
            atr_value = atr[idx] if idx < len(atr) else atr[-1]
            atr_value = atr_value if atr_value > 0 else 1e-6
            plus_di[idx] = (plus_smoothed / atr_value) * 100
            minus_di[idx] = (minus_smoothed / atr_value) * 100

        dx = [0.0] * length
        for idx in range(length):
            den = plus_di[idx] + minus_di[idx]
            dx[idx] = (abs(plus_di[idx] - minus_di[idx]) / den) * 100 if den > 0 else 0.0

        adx = [20.0] * length
        if length <= period * 2:
            avg = sum(dx[max(1, period) :]) / max(1, len(dx[max(1, period) :]))
            return [avg] * length

        adx_start = sum(dx[period : period * 2]) / period
        adx[period * 2 - 1] = adx_start
        for idx in range(period * 2, length):
            adx[idx] = ((adx[idx - 1] * (period - 1)) + dx[idx]) / period
        for idx in range(period * 2 - 2, -1, -1):
            adx[idx] = adx[idx + 1]
        return adx

    def _supertrend_series(self, highs: list[float], lows: list[float], closes: list[float], period: int, multiplier: float) -> tuple[list[float], list[bool]]:
        atr = self._atr_series(highs, lows, closes, period)
        length = len(closes)
        final_upper = [0.0] * length
        final_lower = [0.0] * length
        supertrend = [0.0] * length
        bullish = [True] * length

        for idx in range(length):
            hl2 = (highs[idx] + lows[idx]) / 2
            basic_upper = hl2 + (multiplier * atr[idx])
            basic_lower = hl2 - (multiplier * atr[idx])

            if idx == 0:
                final_upper[idx] = basic_upper
                final_lower[idx] = basic_lower
                supertrend[idx] = basic_lower
                bullish[idx] = closes[idx] >= supertrend[idx]
                continue

            final_upper[idx] = basic_upper if basic_upper < final_upper[idx - 1] or closes[idx - 1] > final_upper[idx - 1] else final_upper[idx - 1]
            final_lower[idx] = basic_lower if basic_lower > final_lower[idx - 1] or closes[idx - 1] < final_lower[idx - 1] else final_lower[idx - 1]

            if supertrend[idx - 1] == final_upper[idx - 1]:
                supertrend[idx] = final_upper[idx] if closes[idx] <= final_upper[idx] else final_lower[idx]
            else:
                supertrend[idx] = final_lower[idx] if closes[idx] >= final_lower[idx] else final_upper[idx]

            bullish[idx] = closes[idx] >= supertrend[idx]

        return supertrend, bullish

    @staticmethod
    def _bollinger_series(values: list[float], period: int, mult: float) -> tuple[list[float], list[float], list[float]]:
        if not values:
            return [0.0], [0.0], [0.0]
        mid: list[float] = []
        upper: list[float] = []
        lower: list[float] = []
        for idx in range(len(values)):
            start = max(0, idx - period + 1)
            window = values[start : idx + 1]
            mean = sum(window) / len(window)
            variance = sum((value - mean) ** 2 for value in window) / len(window)
            std = variance ** 0.5
            mid.append(mean)
            upper.append(mean + (mult * std))
            lower.append(mean - (mult * std))
        return mid, upper, lower

    @staticmethod
    def _pivot_base(candles: list[HistoricalCandle]) -> tuple[float, float, float]:
        base = candles[-2] if len(candles) > 1 else candles[-1]
        return base.high, base.low, base.close


class RecommendationEngine:
    def recommend(self, score: int, signals: SignalSnapshot, indicators: IndicatorSnapshot, price: float) -> tuple[str, str, bool]:
        mixed_signal = (signals.vwap_above and signals.trend_down) or ((not signals.vwap_above) and signals.trend_up)

        if score >= 90:
            recommendation = "STRONG BUY"
        elif score >= 80:
            recommendation = "BUY"
        elif score >= 55:
            recommendation = "HOLD"
        elif score >= 30:
            recommendation = "SELL"
        else:
            recommendation = "STRONG SELL"

        if indicators.adx < 20:
            recommendation = "HOLD"

        if mixed_signal and recommendation == "STRONG SELL":
            recommendation = "HOLD"

        if recommendation in {"STRONG BUY", "STRONG SELL"}:
            strength = "Very Strong"
        elif recommendation in {"BUY", "SELL"}:
            strength = "Strong"
        elif recommendation == "HOLD" and score >= 55:
            strength = "Moderate"
        else:
            strength = "Weak"

        if indicators.adx < 20:
            strength = "Weak"

        if mixed_signal and strength == "Very Strong":
            strength = "Moderate"

        return recommendation, strength, mixed_signal


class SignalEngine:
    def evaluate(self, price: float, indicators: IndicatorSnapshot) -> SignalSnapshot:
        trend_up = price > indicators.ema20 > indicators.ema50 > indicators.ema200 and indicators.supertrend_bullish
        trend_down = price < indicators.ema20 < indicators.ema50 < indicators.ema200 and not indicators.supertrend_bullish
        momentum_up = indicators.rsi >= 52 and indicators.macd > indicators.macd_signal
        momentum_down = indicators.rsi <= 48 and indicators.macd < indicators.macd_signal
        vwap_above = price >= indicators.vwap
        adx_strong = indicators.adx >= 20
        near_support = abs(price - indicators.support_1) <= max(indicators.atr, price * 0.004)
        near_resistance = abs(price - indicators.resistance_1) <= max(indicators.atr, price * 0.004)
        return SignalSnapshot(trend_up, trend_down, momentum_up, momentum_down, vwap_above, adx_strong, near_support, near_resistance)


class ScoreEngine:
    def score(self, price: float, candles: list[HistoricalCandle], indicators: IndicatorSnapshot, signals: SignalSnapshot) -> tuple[ScoreBreakdown, float, list[str]]:
        volumes = [float(c.volume) for c in candles]
        avg_volume20 = sum(volumes[-20:]) / max(1, len(volumes[-20:]))
        current_volume = volumes[-1]

        up_volume = sum(c.volume for c in candles if c.close >= c.open)
        total_volume = sum(c.volume for c in candles)
        delivery_percent = (up_volume / total_volume) * 100 if total_volume > 0 else 50.0

        trend_score = 25 if signals.trend_up else 5 if signals.trend_down else 13
        rsi_sub = 10 if 52 <= indicators.rsi <= 68 else 7 if 45 <= indicators.rsi < 52 else 4 if 35 <= indicators.rsi < 45 else 2
        macd_sub = 10 if indicators.macd > indicators.macd_signal else 4 if abs(indicators.macd - indicators.macd_signal) < 0.12 else 1
        momentum_score = min(20, rsi_sub + macd_sub)

        if indicators.supertrend_bullish and price >= indicators.bb_mid and price > indicators.pivot:
            price_action_score = 15
        elif (not indicators.supertrend_bullish) and price < indicators.bb_mid and price < indicators.pivot:
            price_action_score = 3
        else:
            price_action_score = 8

        vwap_score = 10 if signals.vwap_above else 3
        adx_score = 10 if indicators.adx >= 30 else 7 if indicators.adx >= 24 else 5 if indicators.adx >= 20 else 2
        volume_ratio = current_volume / avg_volume20 if avg_volume20 > 0 else 1.0
        volume_score = 10 if volume_ratio >= 1.45 else 8 if volume_ratio >= 1.2 else 6 if volume_ratio >= 1.0 else 3
        delivery_score = 5 if delivery_percent >= 62 else 4 if delivery_percent >= 55 else 3 if delivery_percent >= 47 else 1

        sr_score = 5 if indicators.support_1 <= price <= indicators.resistance_1 else 3
        if signals.near_support and signals.trend_up:
            sr_score = 5
        if signals.near_resistance and signals.trend_down:
            sr_score = 2

        total = trend_score + momentum_score + price_action_score + vwap_score + adx_score + volume_score + delivery_score + sr_score
        total = max(0, min(100, total))
        confidence = min(float(total + 5), max(30.0, min(95.0, 28.0 + (total * 0.92))))

        contributions = self._build_contributions(trend_score, momentum_score, price_action_score, vwap_score, adx_score, volume_score, delivery_score, sr_score, total)

        return (
            ScoreBreakdown(trend_score, momentum_score, price_action_score, sr_score, vwap_score, adx_score, volume_score, delivery_score, total),
            confidence,
            contributions,
        )

    @staticmethod
    def _build_contributions(trend_score: int, momentum_score: int, price_action_score: int, vwap_score: int, adx_score: int, volume_score: int, delivery_score: int, sr_score: int, total: int) -> list[str]:
        def score_line(label: str, score_value: int, max_weight: int) -> str:
            delta = score_value - (max_weight / 2)
            signed = int(round(delta))
            sign = "+" if signed >= 0 else ""
            return f"{sign}{signed} {label} ({score_value}/{max_weight})"

        return [
            score_line(t("analysis.score.ema_alignment"), trend_score, 25),
            score_line(t("analysis.score.momentum"), momentum_score, 20),
            score_line(t("analysis.score.price_action"), price_action_score, 15),
            score_line("VWAP", vwap_score, 10),
            score_line("ADX", adx_score, 10),
            score_line(t("analysis.score.volume"), volume_score, 10),
            score_line(t("analysis.score.delivery"), delivery_score, 5),
            score_line(t("analysis.score.support_resistance"), sr_score, 5),
            t("analysis.score.final", score=total),
        ]


class TechnicalAnalysisService:
    def __init__(self, data_source: CandleDataSource | None = None, indicator_engine: IndicatorEngine | None = None, signal_engine: SignalEngine | None = None, score_engine: ScoreEngine | None = None, recommendation_engine: RecommendationEngine | None = None) -> None:
        self._data_source = data_source or MarketDataCandleSource()
        self._indicator_engine = indicator_engine or IndicatorEngine()
        self._signal_engine = signal_engine or SignalEngine()
        self._score_engine = score_engine or ScoreEngine()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()

    def analyze(self, symbol: str, exchange: str, timeframe: str = "15 Minute") -> AnalysisResult:
        normalized_symbol = (symbol or "").strip().upper()
        normalized_exchange = (exchange or "NSE").strip().upper()

        if not normalized_symbol:
            app_logger.warning(f"Market quote missing for empty symbol on {normalized_exchange}")
            return self._no_data_result(normalized_symbol, normalized_exchange, t("analysis.reason.symbol_not_found"))

        quote = self._data_source.get_quote(normalized_symbol, normalized_exchange)
        if quote is None:
            app_logger.warning(f"Market quote missing for symbol={normalized_symbol} exchange={normalized_exchange}")
            return self._no_data_result(normalized_symbol, normalized_exchange, t("analysis.reason.symbol_not_found"))

        candles = list(self._data_source.get_historical_candles(normalized_symbol, normalized_exchange, timeframe))
        if not candles:
            app_logger.warning(f"Historical candles missing for symbol={normalized_symbol} exchange={normalized_exchange}")
            return self._no_data_result(normalized_symbol, normalized_exchange, t("analysis.reason.candles_unavailable"))

        indicators = self._indicator_engine.calculate(candles)
        price = quote.ltp
        signals = self._signal_engine.evaluate(price, indicators)
        score, confidence, contribution_lines = self._score_engine.score(price, candles, indicators, signals)
        recommendation, signal_strength, mixed_signal = self._recommendation_engine.recommend(score.total, signals, indicators, price)
        recommendation_label = self._localized_recommendation(recommendation)
        signal_strength_label = self._localized_strength(signal_strength)

        up_volume = sum(c.volume for c in candles if c.close >= c.open)
        total_volume = sum(c.volume for c in candles)
        delivery_percent = (up_volume / total_volume) * 100 if total_volume > 0 else 50.0

        recommendation_reason = t("analysis.recommendation_reason", recommendation=recommendation_label, strength=signal_strength_label)
        reasons = self._build_reasons(price, indicators, signals, recommendation, score, confidence, contribution_lines, mixed_signal, signal_strength)
        summary = self._build_summary(normalized_symbol, price, indicators, recommendation, confidence, signal_strength, mixed_signal)
        risk = self._risk_label(indicators.atr, price, indicators.adx)

        atr = max(indicators.atr, price * 0.004)
        if recommendation == "BUY":
            target_1 = price + (atr * 1.2)
            target_2 = price + (atr * 2.2)
            stop_loss = price - (atr * 1.1)
        elif recommendation == "SELL":
            target_1 = price - (atr * 1.2)
            target_2 = price - (atr * 2.2)
            stop_loss = price + (atr * 1.1)
        else:
            target_1 = indicators.resistance_1
            target_2 = indicators.resistance_2
            stop_loss = indicators.support_1

        return AnalysisResult(
            symbol=normalized_symbol,
            exchange=normalized_exchange,
            quote=quote,
            candles=candles,
            indicators=indicators,
            signals=signals,
            recommendation=recommendation,
            signal_strength=signal_strength,
            mixed_signal=mixed_signal,
            score=score,
            confidence_percent=confidence,
            recommendation_reason=recommendation_reason,
            reasons=reasons,
            summary=summary,
            risk=risk,
            target_1=target_1,
            target_2=target_2,
            stop_loss=stop_loss,
            delivery_percent=delivery_percent,
        )

    @staticmethod
    def _no_data_result(symbol: str, exchange: str, reason: str) -> AnalysisResult:
        now = datetime.now(timezone.utc)
        safe_symbol = symbol or "UNKNOWN"
        quote = MarketInstrument(safe_symbol, safe_symbol, "Unknown", exchange or "NSE", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, now)
        indicators = IndicatorSnapshot(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        signals = SignalSnapshot(False, False, False, False, False, False, False, False)
        return AnalysisResult(
            symbol=safe_symbol,
            exchange=exchange or "NSE",
            quote=quote,
            candles=[],
            indicators=indicators,
            signals=signals,
            recommendation="NO DATA",
            signal_strength="Weak",
            mixed_signal=False,
            score=ScoreBreakdown(0, 0, 0, 0, 0, 0, 0, 0, 0),
            confidence_percent=0.0,
            recommendation_reason=t(
                "analysis.recommendation_reason",
                recommendation=TechnicalAnalysisService._localized_recommendation("NO DATA"),
                strength=TechnicalAnalysisService._localized_strength("Weak"),
            ),
            reasons=[reason],
            summary=t("analysis.summary.no_quote"),
            risk="Unknown",
            target_1=0.0,
            target_2=0.0,
            stop_loss=0.0,
            delivery_percent=0.0,
        )

    @staticmethod
    def _risk_label(atr: float, price: float, adx: float) -> str:
        atr_pct = (atr / price) * 100 if price else 0.0
        if atr_pct < 1.0 and adx >= 22:
            return "Low"
        if atr_pct > 2.2:
            return "High"
        return "Medium"

    @staticmethod
    def _build_reasons(price: float, indicators: IndicatorSnapshot, signals: SignalSnapshot, recommendation: str, score: ScoreBreakdown, confidence: float, contribution_lines: list[str], mixed_signal: bool, signal_strength: str) -> list[str]:
        recommendation_label = TechnicalAnalysisService._localized_recommendation(recommendation)
        signal_strength_label = TechnicalAnalysisService._localized_strength(signal_strength)
        risk_label = TechnicalAnalysisService._localized_risk(TechnicalAnalysisService._risk_label(indicators.atr, price, indicators.adx))
        reasons: list[str] = []
        reasons.extend(contribution_lines)
        reasons.append(t("analysis.reason.final_recommendation", recommendation=recommendation_label))
        reasons.append(t("analysis.reason.signal_strength", strength=signal_strength_label))
        reasons.append(t("analysis.reason.risk", risk=risk_label, atr=f"{indicators.atr:.2f}", adx=f"{indicators.adx:.1f}"))
        if mixed_signal:
            reasons.append(t("analysis.reason.mixed_signal"))

        reasons.append(t("analysis.reason.ema_structure", ema20=f"{indicators.ema20:.2f}", ema50=f"{indicators.ema50:.2f}", ema200=f"{indicators.ema200:.2f}", price=f"{price:.2f}"))
        reasons.append(t("analysis.reason.momentum", rsi=f"{indicators.rsi:.1f}", macd=f"{indicators.macd:+.3f}", signal=f"{indicators.macd_signal:+.3f}"))
        reasons.append(t("analysis.reason.trend_strength", adx=f"{indicators.adx:.1f}", supertrend_state=t("analysis.trend.bullish") if indicators.supertrend_bullish else t("analysis.trend.bearish"), supertrend=f"{indicators.supertrend:.2f}"))

        if signals.vwap_above:
            reasons.append(t("analysis.reason.vwap_above", vwap=f"{indicators.vwap:.2f}"))
        else:
            reasons.append(t("analysis.reason.vwap_below", vwap=f"{indicators.vwap:.2f}"))

        reasons.append(t("analysis.reason.support_resistance", s1=f"{indicators.support_1:.2f}", r1=f"{indicators.resistance_1:.2f}", pivot=f"{indicators.pivot:.2f}"))
        reasons.append(
            t(
                "analysis.reason.cpr",
                bc=f"{indicators.cpr_bc:.2f}",
                tc=f"{indicators.cpr_tc:.2f}",
                recommendation=recommendation_label,
                score=score.total,
                confidence=f"{confidence:.1f}",
            )
        )
        return reasons

    @staticmethod
    def _build_summary(symbol: str, price: float, indicators: IndicatorSnapshot, recommendation: str, confidence: float, signal_strength: str, mixed_signal: bool) -> str:
        trend_state = t("analysis.state.uptrend") if indicators.ema20 > indicators.ema50 > indicators.ema200 else t("analysis.state.downtrend") if indicators.ema20 < indicators.ema50 < indicators.ema200 else t("analysis.state.range")
        momentum_state = t("analysis.state.positive") if indicators.macd > indicators.macd_signal and indicators.rsi >= 50 else t("analysis.state.negative") if indicators.macd < indicators.macd_signal and indicators.rsi < 50 else t("analysis.state.neutral")
        mixed = f" {t('analysis.summary.mixed')}" if mixed_signal else ""
        recommendation_label = TechnicalAnalysisService._localized_recommendation(recommendation)
        signal_strength_label = TechnicalAnalysisService._localized_strength(signal_strength)
        return t(
            "analysis.summary.main",
            symbol=symbol.upper(),
            price=f"{price:.2f}",
            trend_state=trend_state,
            momentum_state=momentum_state,
            adx=f"{indicators.adx:.1f}",
            vwap=f"{indicators.vwap:.2f}",
            recommendation=recommendation_label,
            signal_strength=signal_strength_label,
            confidence=f"{confidence:.1f}",
            mixed=mixed,
        )

    @staticmethod
    def _localized_recommendation(recommendation: str) -> str:
        key_map = {
            "STRONG BUY": "analysis.recommendation.strong_buy",
            "BUY": "analysis.recommendation.buy",
            "HOLD": "analysis.recommendation.hold",
            "SELL": "analysis.recommendation.sell",
            "STRONG SELL": "analysis.recommendation.strong_sell",
            "NO DATA": "analysis.recommendation.no_data",
        }
        return t(key_map.get(recommendation, "analysis.recommendation.hold"))

    @staticmethod
    def _localized_strength(strength: str) -> str:
        key_map = {
            "Very Strong": "analysis.strength.very_strong",
            "Strong": "analysis.strength.strong",
            "Moderate": "analysis.strength.moderate",
            "Weak": "analysis.strength.weak",
        }
        return t(key_map.get(strength, "analysis.strength.weak"))

    @staticmethod
    def _localized_risk(risk: str) -> str:
        key_map = {
            "Low": "analysis.risk.low",
            "Medium": "analysis.risk.medium",
            "High": "analysis.risk.high",
            "Unknown": "analysis.risk.unknown",
        }
        return t(key_map.get(risk, "analysis.risk.unknown"))
