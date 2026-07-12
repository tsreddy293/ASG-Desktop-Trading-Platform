from __future__ import annotations

from src.analysis.model import AIAnalysisRequest
from src.analysis.service import AIAnalysisService
from src.core.logger import app_logger


class AIAnalysisController:
    """Controller for AI Analysis MVC interactions."""

    def __init__(self, view, service: AIAnalysisService | None = None) -> None:
        self._view = view
        self._service = service or AIAnalysisService()

    def load_symbol(self, symbol: str, exchange: str = "NSE", sector: str | None = None) -> None:
        request = AIAnalysisRequest(symbol=symbol, exchange=exchange, sector=sector)
        snapshot = self._service.get_analysis(request)
        self._view.render_analysis(snapshot)
        app_logger.info(f"AI Analysis loaded for {snapshot.symbol} ({snapshot.signal})")
