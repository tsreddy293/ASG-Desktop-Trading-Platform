from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import QObject, Signal

from src.chart.model import Candle, ChartData, ChartPayload
from src.chart.viewmodel import ChartViewModel


class _FakeRefreshService(QObject):
    payload_updated = Signal(object)
    status_updated = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.request = {
            "symbol": "",
            "exchange": "",
            "timeframe": "",
            "indicators": set(),
        }
        self.refresh_count = 0
        self.auto_refresh = True
        self.started = False

    def set_request(self, symbol: str, exchange: str, timeframe: str, indicators: set[str]) -> None:
        self.request = {
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "indicators": set(indicators),
        }

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def refresh_once(self) -> None:
        self.refresh_count += 1
        payload = ChartPayload(
            data=ChartData(
                symbol=self.request["symbol"] or "SBIN",
                exchange=self.request["exchange"] or "NSE",
                timeframe=self.request["timeframe"] or "15 Minute",
                candles=[
                    Candle(
                        timestamp=datetime.now(UTC),
                        open=100.0,
                        high=101.0,
                        low=99.5,
                        close=100.5,
                        volume=1000,
                    )
                ],
            ),
            indicators={},
            last_price=100.5,
        )
        self.payload_updated.emit(payload)

    def set_auto_refresh(self, enabled: bool) -> None:
        self.auto_refresh = enabled


def test_chart_viewmodel_maps_timeframes_and_updates_request() -> None:
    fake = _FakeRefreshService()
    vm = ChartViewModel(refresh_service=fake)

    vm.set_symbol("hdfcbank", "nse")
    assert fake.request["symbol"] == "HDFCBANK"
    assert fake.request["exchange"] == "NSE"

    vm.set_timeframe("1m")
    assert fake.request["timeframe"] == "1 Minute"

    vm.set_timeframe("1H")
    assert fake.request["timeframe"] == "1 Hour"


def test_chart_viewmodel_indicator_toggle_and_refresh() -> None:
    fake = _FakeRefreshService()
    vm = ChartViewModel(refresh_service=fake)

    vm.set_indicator("MACD", True)
    assert "MACD" in fake.request["indicators"]

    vm.set_indicator("EMA", False)
    assert "EMA" not in fake.request["indicators"]

    before = fake.refresh_count
    vm.refresh_now()
    assert fake.refresh_count == before + 1


def test_chart_viewmodel_auto_refresh_and_signal_passthrough() -> None:
    fake = _FakeRefreshService()
    vm = ChartViewModel(refresh_service=fake)

    seen = []
    vm.payload_changed.connect(seen.append)

    vm.start()
    assert fake.started is True

    fake.refresh_once()
    assert len(seen) == 1

    vm.set_auto_refresh(False)
    assert fake.auto_refresh is False

    vm.stop()
    assert fake.started is False
