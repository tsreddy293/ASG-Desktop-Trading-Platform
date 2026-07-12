from src.analysis.controller import AIAnalysisController
from src.analysis.engine import AIAnalysisEngine
from src.analysis.model import AIAnalysisRequest, AIAnalysisSnapshot
from src.analysis.service import AIAnalysisService


class AIAnalysisModel:
    Request = AIAnalysisRequest
    Snapshot = AIAnalysisSnapshot


__all__ = [
    "AIAnalysisEngine",
    "AIAnalysisService",
    "AIAnalysisController",
    "AIAnalysisModel",
    "AIAnalysisRequest",
    "AIAnalysisSnapshot",
]
