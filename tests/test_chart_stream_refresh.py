from __future__ import annotations

from datetime import UTC, datetime

from src.chart.model import Candle, ChartData, ChartPayload
from src.chart.refresh_service import ChartRefreshService


class _FakeMarketStream:
    def __init__(self) -> None:
        self.handler = None

    def subscribe(self, handler):
        self.handler = handler

    def unsubscribe(self, handler):
        if self.handler == handler:
            self.handler = None

    def get_quote(self, symbol: str, exchange: str):
        return type(
            "Q",
            (),
            {
                "open": 100.0,
                "high": 103.0,
                "low": 99.5,
                "ltp": 102.0,
                "volume": 1000,
                "timestamp": datetime.now(UTC),
            },
        )()


class _FakeChartService:
    def load_chart(self, request, indicators):
        return ChartPayload(
            data=ChartData(
                symbol=request.symbol,
                exchange=request.exchange,
                timeframe=request.timeframe,
                candles=[
                    Candle(
                        timestamp=datetime.now(UTC),
                        open=100.0,
                        high=101.0,
                        low=99.0,
                        close=100.5,
                        volume=900,
                    )
                ],
            ),
            indicators={},
            last_price=100.5,
        )


def test_chart_refresh_service_uses_stream_subscription(monkeypatch) -> None:
    fake_stream = _FakeMarketStream()
    monkeypatch.setattr("src.chart.refresh_service.market_data_service", fake_stream)

    service = ChartRefreshService(chart_service=_FakeChartService())

    seen = []
    service.payload_updated.connect(seen.append)

    service.start()
    assert fake_stream.handler is not None
    assert hasattr(service, "_timer") is False
    assert seen

    fake_stream.handler(type("E", (), {"symbols": ["SBIN"]})())
    assert len(seen) >= 2

    service.stop()
    assert fake_stream.handler is None
