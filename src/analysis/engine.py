from __future__ import annotations

from datetime import datetime, timezone

from src.analysis.model import AIAnalysisRequest, AIAnalysisSnapshot
from src.analysis.technical_analysis import TechnicalAnalysisService
from src.core.translation import t


class AIAnalysisEngine:
    """Engine that builds AI analysis snapshots from deterministic technical calculations."""

    def __init__(self, technical_service: TechnicalAnalysisService | None = None) -> None:
        self._technical_service = technical_service or TechnicalAnalysisService()

    def analyze(self, request: AIAnalysisRequest) -> AIAnalysisSnapshot:
        result = self._technical_service.analyze(request.symbol, request.exchange, timeframe="15 Minute")
        localized_recommendation = self._localized_recommendation(result.recommendation)
        localized_strength = self._localized_strength(result.signal_strength)
        localized_risk = self._localized_risk(result.risk)

        if result.recommendation == "NO DATA":
            return AIAnalysisSnapshot(
                symbol=result.symbol,
                stock_name=result.quote.company,
                exchange=result.exchange,
                sector=request.sector or result.quote.sector,
                current_price=0.0,
                todays_change_percent=0.0,
                volume=0,
                signal="NO DATA",
                ai_score=0,
                confidence_percent=0.0,
                trend=t("ai.no_data_message"),
                risk=t("analysis.risk.explain", risk=self._localized_risk("Unknown"), atr="0.00", adx="0.0"),
                support=0.0,
                resistance=0.0,
                target_1=0.0,
                target_2=0.0,
                stop_loss=0.0,
                rsi=0.0,
                macd=0.0,
                ema="--",
                vwap="--",
                adx=0.0,
                atr=0.0,
                supertrend="--",
                delivery_percent=0.0,
                volume_analysis=t("ai.no_data_message"),
                reasons=[t("analysis.reason.symbol_not_found")],
                ai_summary=t("ai.no_data_message"),
                recent_signals=[t("analysis.recent.no_data")],
                trend_strength=0,
                momentum=0,
                volume_strength=0,
                confidence_meter=0,
                candles=[],
                last_updated=datetime.now(timezone.utc),
            )

        indicators = result.indicators
        quote = result.quote

        ema_description = (
            f"EMA20 {indicators.ema20:.2f} | "
            f"EMA50 {indicators.ema50:.2f} | "
            f"EMA200 {indicators.ema200:.2f}"
        )
        vwap_position = t("analysis.vwap.above") if result.signals.vwap_above else t("analysis.vwap.below")
        trend = (
            t("analysis.trend.mixed")
            if result.mixed_signal
            else t("analysis.trend.uptrend")
            if result.signals.trend_up
            else t("analysis.trend.downtrend")
            if result.signals.trend_down
            else t("analysis.trend.sideways")
        )
        candles = [(c.open, c.high, c.low, c.close) for c in result.candles[-24:]]

        recent_signals = [
            t("analysis.recent.pivot_cpr", pivot=f"{indicators.pivot:.2f}", bc=f"{indicators.cpr_bc:.2f}", tc=f"{indicators.cpr_tc:.2f}"),
            t(
                "analysis.recent.bollinger",
                lower=f"{indicators.bb_lower:.2f}",
                mid=f"{indicators.bb_mid:.2f}",
                upper=f"{indicators.bb_upper:.2f}",
            ),
            t("analysis.recent.ema_check", ema=ema_description),
            t(
                "analysis.recent.rule_output",
                recommendation=localized_recommendation,
                strength=localized_strength,
                confidence=f"{result.confidence_percent:.1f}",
            ),
            result.recommendation_reason,
        ]

        return AIAnalysisSnapshot(
            symbol=result.symbol,
            stock_name=quote.company,
            exchange=result.exchange,
            sector=request.sector or quote.sector,
            current_price=quote.ltp,
            todays_change_percent=quote.change_percent,
            volume=quote.volume,
            signal=result.recommendation,
            ai_score=result.score.total,
            confidence_percent=result.confidence_percent,
            trend=trend,
            risk=t("analysis.risk.explain", risk=localized_risk, atr=f"{indicators.atr:.2f}", adx=f"{indicators.adx:.1f}"),
            support=indicators.support_1,
            resistance=indicators.resistance_1,
            target_1=result.target_1,
            target_2=result.target_2,
            stop_loss=result.stop_loss,
            rsi=indicators.rsi,
            macd=indicators.macd,
            ema=ema_description,
            vwap=vwap_position,
            adx=indicators.adx,
            atr=indicators.atr,
            supertrend=t("analysis.trend.bullish") if indicators.supertrend_bullish else t("analysis.trend.bearish"),
            delivery_percent=result.delivery_percent,
            volume_analysis=t(
                "analysis.volume",
                volume=f"{quote.volume:,}",
                vwap=f"{indicators.vwap:.2f}",
                spread=f"{(indicators.bb_upper - indicators.bb_lower):.2f}",
            ),
            reasons=result.reasons,
            ai_summary=result.summary,
            recent_signals=recent_signals,
            trend_strength=result.score.trend,
            momentum=result.score.momentum,
            volume_strength=result.score.volume,
            confidence_meter=int(round(result.confidence_percent)),
            candles=candles,
            last_updated=datetime.now(timezone.utc),
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
