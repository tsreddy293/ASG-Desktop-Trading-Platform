from src.analysis.model import AIAnalysisRequest
from src.analysis.service import AIAnalysisService


def test_ai_analysis_service_returns_full_snapshot() -> None:
    service = AIAnalysisService()
    snapshot = service.get_analysis(AIAnalysisRequest(symbol="SBIN", exchange="NSE"))

    assert snapshot.symbol == "SBIN"
    assert snapshot.stock_name != ""
    assert snapshot.exchange == "NSE"
    assert snapshot.current_price > 0
    assert snapshot.signal in {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}
    assert 0 <= snapshot.ai_score <= 100
    assert snapshot.confidence_percent <= snapshot.ai_score + 5
    assert len(snapshot.reasons) >= 3
    assert len(snapshot.recent_signals) >= 3
    assert len(snapshot.candles) >= 10
