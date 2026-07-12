from __future__ import annotations

from src.analysis.engine import AIAnalysisEngine
from src.analysis.model import AIAnalysisRequest, AIAnalysisSnapshot


class AIAnalysisService:
    """Service layer for AI analysis orchestration."""

    def __init__(self, engine: AIAnalysisEngine | None = None) -> None:
        self._engine = engine or AIAnalysisEngine()

    def get_analysis(self, request: AIAnalysisRequest) -> AIAnalysisSnapshot:
        return self._engine.analyze(request)
