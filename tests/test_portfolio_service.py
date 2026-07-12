from __future__ import annotations

from dataclasses import dataclass

from src.services.portfolio_service import PortfolioService


@dataclass(slots=True)
class _Pos:
    symbol: str
    company: str
    quantity: int
    average_price: float
    ltp: float
    pnl_percent: float


class _FakeMarket:
    def __init__(self) -> None:
        self.handlers = []
        self._rows = [
            _Pos("SBIN", "State Bank", 10, 800.0, 812.0, 1.5),
            _Pos("HDFCBANK", "HDFC Bank", 5, 1680.0, 1700.0, 1.1),
        ]

    def subscribe(self, handler):
        self.handlers.append(handler)

    def unsubscribe(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def get_portfolio_positions(self):
        return self._rows

    def get_quote(self, symbol: str, exchange: str = "NSE"):
        return None


def test_portfolio_service_positions_holdings_summary_calculations() -> None:
    service = PortfolioService(market_service=_FakeMarket())

    positions = service.get_positions()
    assert len(positions) == 2
    assert positions[0].unrealized_pnl > 0

    holdings = service.get_holdings()
    assert len(holdings) == 2
    assert holdings[0].current_value > 0

    summary = service.get_summary()
    assert summary.total_investment > 0
    assert summary.current_value > 0


def test_portfolio_service_filter_and_sort_modes() -> None:
    service = PortfolioService(market_service=_FakeMarket())
    rows = service.get_positions()

    open_rows = service.filter_positions(rows, "Open Positions")
    assert len(open_rows) == 2

    sorted_rows = service.sort_positions(rows, "Alphabetical")
    assert sorted_rows[0].symbol <= sorted_rows[1].symbol
