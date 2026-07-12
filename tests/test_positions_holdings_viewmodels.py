from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.marketdata.model import MarketDataEvent, MarketEventType
from src.services.portfolio_service import HoldingRow, PortfolioSummary, PositionRow
from src.ui.viewmodels.holdings_view_model import HoldingsViewModel
from src.ui.viewmodels.portfolio_view_model import PortfolioViewModel
from src.ui.viewmodels.positions_view_model import PositionsViewModel


@dataclass(slots=True)
class _FakeService:
    handlers: list

    def __init__(self) -> None:
        self.handlers = []

    def subscribe(self, handler):
        self.handlers.append(handler)

    def unsubscribe(self, handler):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def get_positions(self):
        return [
            PositionRow("SBIN", "NSE", 10, 800.0, 812.0, 120.0, 20.0, 100.0, "MIS", "EQUITY", True),
            PositionRow("ABC", "BSE", 0, 100.0, 100.0, 0.0, 0.0, 0.0, "CNC", "EQUITY", False),
        ]

    def get_holdings(self):
        return [HoldingRow("SBIN", "NSE", 10, 800.0, 812.0, 8120.0, 18.0, 120.0, "CNC")]

    def get_summary(self):
        return PortfolioSummary(900000.0, 100000.0, 50000.0, 52000.0, 1500.0, 2000.0, datetime.now(UTC))

    @staticmethod
    def filter_positions(rows, mode: str):
        if mode.upper() == "OPEN POSITIONS":
            return [r for r in rows if r.open_position]
        return rows

    @staticmethod
    def sort_positions(rows, mode: str):
        if mode.lower() == "alphabetical":
            return sorted(rows, key=lambda r: r.symbol)
        return rows


def test_positions_viewmodel_streaming_filter_sort_and_actions() -> None:
    service = _FakeService()
    vm = PositionsViewModel(service=service)

    seen = []
    info = []
    vm.positionsUpdated.connect(seen.append)
    vm.errorOccurred.connect(info.append)

    vm.start()
    vm.set_filter("Open Positions")
    vm.set_sort("Alphabetical")

    assert seen
    assert len(seen[-1]) == 1

    vm.exit_position("SBIN")
    vm.reverse_position("SBIN")
    vm.add_quantity("SBIN", 1)
    vm.square_off("SBIN")
    assert len(info) >= 4

    event = MarketDataEvent(MarketEventType.TICK, ["SBIN"], datetime.now(UTC))
    for handler in list(service.handlers):
        handler(event)
    assert len(seen) >= 2

    vm.stop()


def test_holdings_and_portfolio_viewmodels_streaming() -> None:
    service = _FakeService()
    hvm = HoldingsViewModel(service=service)
    pvm = PortfolioViewModel(service=service)

    seen_holdings = []
    seen_summary = []

    hvm.holdingsUpdated.connect(seen_holdings.append)
    pvm.summaryUpdated.connect(seen_summary.append)

    hvm.start()
    pvm.start()

    assert seen_holdings
    assert seen_summary
    assert seen_summary[-1]["available_cash"] == 900000.0

    event = MarketDataEvent(MarketEventType.TICK, ["SBIN"], datetime.now(UTC))
    for handler in list(service.handlers):
        handler(event)

    assert len(seen_holdings) >= 2
    assert len(seen_summary) >= 2

    hvm.stop()
    pvm.stop()
