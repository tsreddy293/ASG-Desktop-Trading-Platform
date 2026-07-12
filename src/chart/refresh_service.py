from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, Signal

from src.chart.model import Candle, ChartPayload, ChartRequest
from src.chart.service import ChartService
from src.marketdata.service import market_data_service


class ChartRefreshService(QObject):
    """Single background refresh service for chart payload + live candle updates."""

    payload_updated = Signal(object)
    status_updated = Signal(str, str)

    def __init__(self, chart_service: ChartService | None = None, interval_ms: int = 2000) -> None:
        super().__init__()
        self._chart_service = chart_service or ChartService()
        self._interval_ms = max(1000, int(interval_ms))
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.refresh_once)

        self._symbol = "SBIN"
        self._exchange = "NSE"
        self._timeframe = "15 Minute"
        self._indicators: set[str] = {"EMA", "SMA", "VWAP"}

    def set_request(self, symbol: str, exchange: str, timeframe: str, indicators: set[str]) -> None:
        self._symbol = (symbol or "SBIN").strip().upper() or "SBIN"
        self._exchange = (exchange or "NSE").strip().upper() or "NSE"
        self._timeframe = timeframe or "15 Minute"
        self._indicators = set(indicators)

    def start(self) -> None:
        self._timer.start()
        self.refresh_once()

    def stop(self) -> None:
        self._timer.stop()

    def set_auto_refresh(self, enabled: bool) -> None:
        if enabled:
            self.start()
        else:
            self.stop()

    def refresh_once(self) -> None:
        request = ChartRequest(symbol=self._symbol, exchange=self._exchange, timeframe=self._timeframe)
        try:
            payload = self._chart_service.load_chart(request, self._indicators)
            payload = self._merge_live_candle(payload)
            self.payload_updated.emit(payload)
            self.status_updated.emit("Connected", datetime.now(timezone.utc).strftime("%H:%M:%S"))
        except Exception as exc:
            self.status_updated.emit(f"Disconnected: {exc}", datetime.now(timezone.utc).strftime("%H:%M:%S"))

    def _merge_live_candle(self, payload: ChartPayload) -> ChartPayload:
        quote = market_data_service.get_quote(self._symbol, self._exchange)
        if quote is None:
            return payload
        candles = list(payload.data.candles)
        if not candles:
            candles.append(
                Candle(
                    timestamp=datetime.now(timezone.utc),
                    open=quote.open,
                    high=quote.high,
                    low=quote.low,
                    close=quote.ltp,
                    volume=quote.volume,
                )
            )
            payload.data.candles = candles
            payload.last_price = quote.ltp
            return payload

        latest = candles[-1]
        now = datetime.now(timezone.utc)
        candles[-1] = Candle(
            timestamp=quote.timestamp if hasattr(quote.timestamp, "astimezone") else now,
            open=latest.open,
            high=max(latest.high, quote.ltp),
            low=min(latest.low, quote.ltp),
            close=quote.ltp,
            volume=max(latest.volume, quote.volume),
        )
        payload.data.candles = candles
        payload.last_price = quote.ltp
        return payload
