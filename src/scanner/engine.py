from __future__ import annotations

from src.analysis.technical_analysis import TechnicalAnalysisService
from src.core.translation import t
from src.marketdata.service import market_data_service
from src.scanner.model import ScannerFilters, ScannerRow


class AIScannerEngine:
    """Screening engine powered by the shared technical analysis service."""

    _TIMEFRAME_MAP = {
        "Intraday": "15 Minute",
        "Swing": "1 Hour",
        "Delivery": "Daily",
    }

    def __init__(self, technical_service: TechnicalAnalysisService | None = None) -> None:
        self._technical_service = technical_service or TechnicalAnalysisService()

    def run_scan(self, filters: ScannerFilters) -> tuple[list[ScannerRow], int]:
        quotes = market_data_service.get_live_quotes(filters.exchange or "NSE", "")
        timeframe = self._TIMEFRAME_MAP.get(filters.scanner, "15 Minute")
        rows: list[ScannerRow] = []

        for quote in quotes:
            if filters.sector != "All" and quote.sector != filters.sector:
                continue
            if quote.volume < filters.minimum_volume:
                continue
            if quote.ltp < filters.minimum_price or quote.ltp > filters.maximum_price:
                continue

            analysis = self._technical_service.analyze(quote.symbol, quote.exchange, timeframe=timeframe)
            indicators = analysis.indicators

            ema_trend = (
                t("analysis.trend.mixed")
                if analysis.mixed_signal
                else t("analysis.trend.bullish")
                if analysis.signals.trend_up
                else t("analysis.trend.bearish")
                if analysis.signals.trend_down
                else t("analysis.state.neutral")
            )
            vwap_position = t("analysis.vwap.above") if analysis.signals.vwap_above else t("analysis.vwap.below")
            signal_strength = self._localized_strength(analysis.signal_strength)
            risk_label = self._localized_risk(analysis.risk)

            rows.append(
                ScannerRow(
                    symbol=quote.symbol,
                    company=quote.company,
                    sector=quote.sector,
                    ltp=quote.ltp,
                    change_percent=quote.change_percent,
                    volume=quote.volume,
                    delivery_percent=analysis.delivery_percent,
                    rsi=indicators.rsi,
                    macd=indicators.macd,
                    ema_trend=ema_trend,
                    vwap_position=vwap_position,
                    ai_score=analysis.score.total,
                    signal=analysis.recommendation,
                    confidence_percent=analysis.confidence_percent,
                    risk=t("analysis.scanner.risk", risk=risk_label, strength=signal_strength),
                    target=analysis.target_1,
                    stop_loss=analysis.stop_loss,
                )
            )

        rows.sort(key=lambda item: item.ai_score, reverse=True)
        return rows, len(quotes)

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
