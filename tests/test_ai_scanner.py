from src.scanner.model import ScannerFilters
from src.scanner.service import ScannerService


def test_ai_scanner_service_returns_qualified_rows() -> None:
    service = ScannerService()
    filters = ScannerFilters(
        exchange="NSE",
        segment="Cash",
        scanner="Intraday",
        market_cap="All",
        sector="All",
        minimum_volume=1_000_000,
        minimum_price=100.0,
        maximum_price=10_000.0,
    )

    rows, summary = service.scan(filters)

    assert summary.stocks_scanned >= summary.stocks_qualified
    assert summary.stocks_qualified == len(rows)
    assert summary.scan_time_seconds >= 0
    assert len(rows) > 0

    first = rows[0]
    assert first.signal in {"STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"}
    assert 0 <= first.ai_score <= 100
    assert first.confidence_percent <= first.ai_score + 5
    assert first.target > 0
    assert first.stop_loss > 0
