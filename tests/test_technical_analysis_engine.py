from src.analysis.technical_analysis import TechnicalAnalysisService


def test_technical_analysis_valid_symbol_returns_scored_result() -> None:
    service = TechnicalAnalysisService()

    result = service.analyze("SBIN", "NSE")

    assert result.symbol == "SBIN"
    assert result.recommendation in {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}
    assert 0 <= result.score.total <= 100
    assert result.confidence_percent <= result.score.total + 5


def test_technical_analysis_invalid_symbol_returns_no_data_result() -> None:
    service = TechnicalAnalysisService()

    result = service.analyze("INVALID_SYMBOL", "NSE")

    assert result.recommendation == "NO DATA"
    assert result.score.total == 0
    assert result.confidence_percent == 0
    assert result.summary == "Market quote is unavailable for the selected symbol."
    assert result.reasons == ["Symbol not found in market quote repository."]


def test_technical_analysis_empty_symbol_returns_no_data_result() -> None:
    service = TechnicalAnalysisService()

    result = service.analyze("", "NSE")

    assert result.recommendation == "NO DATA"
    assert result.score.total == 0
    assert result.confidence_percent == 0
    assert result.summary == "Market quote is unavailable for the selected symbol."
    assert result.reasons == ["Symbol not found in market quote repository."]


def test_technical_analysis_delisted_symbol_returns_no_data_result() -> None:
    service = TechnicalAnalysisService()

    result = service.analyze("DELISTED_ABC", "NSE")

    assert result.recommendation == "NO DATA"
    assert result.score.total == 0
    assert result.confidence_percent == 0
    assert result.summary == "Market quote is unavailable for the selected symbol."
    assert result.reasons == ["Symbol not found in market quote repository."]
