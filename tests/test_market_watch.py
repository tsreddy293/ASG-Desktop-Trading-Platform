from src.market.service import MarketWatchService


def test_market_watch_service_returns_default_symbols() -> None:
    service = MarketWatchService()
    quotes = service.get_quotes()

    assert len(quotes) == 10
    assert [quote.symbol for quote in quotes[:3]] == ["SBIN", "RELIANCE", "TCS"]
    assert quotes[0].company == "State Bank of India"
