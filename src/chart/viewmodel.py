from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.chart.model import ChartPayload
from src.chart.refresh_service import ChartRefreshService


_TIMEFRAME_MAP = {
    "1m": "1 Minute",
    "3m": "3 Minute",
    "5m": "5 Minute",
    "10m": "10 Minute",
    "15m": "15 Minute",
    "30m": "30 Minute",
    "1H": "1 Hour",
    "2H": "2 Hour",
    "4H": "4 Hour",
    "1D": "Daily",
    "1W": "Weekly",
    "1M": "Monthly",
    "3 Minute": "3 Minute",
    "10 Minute": "10 Minute",
    "2 Hour": "2 Hour",
    "4 Hour": "4 Hour",
    "Weekly": "Weekly",
    "Monthly": "Monthly",
    "1 Minute": "1 Minute",
    "5 Minute": "5 Minute",
    "15 Minute": "15 Minute",
    "30 Minute": "30 Minute",
    "1 Hour": "1 Hour",
    "Daily": "Daily",
}


class ChartViewModel(QObject):
    payload_changed = Signal(object)
    status_changed = Signal(str, str)

    def __init__(self, refresh_service: ChartRefreshService | None = None) -> None:
        super().__init__()
        self._refresh_service = refresh_service or ChartRefreshService()
        self._refresh_service.payload_updated.connect(self.payload_changed.emit)
        self._refresh_service.status_updated.connect(self.status_changed.emit)

        self._symbol = "SBIN"
        self._exchange = "NSE"
        self._timeframe = "15 Minute"
        self._indicators: set[str] = {"EMA", "SMA", "VWAP"}

    def start(self) -> None:
        self._apply_request()
        self._refresh_service.start()

    def stop(self) -> None:
        self._refresh_service.stop()

    def set_symbol(self, symbol: str, exchange: str = "NSE") -> None:
        self._symbol = (symbol or "SBIN").strip().upper() or "SBIN"
        self._exchange = (exchange or "NSE").strip().upper() or "NSE"
        self._apply_request()
        self._refresh_service.refresh_once()

    def set_timeframe(self, timeframe: str) -> None:
        mapped = _TIMEFRAME_MAP.get(timeframe, timeframe)
        self._timeframe = mapped if mapped else "15 Minute"
        self._apply_request()
        self._refresh_service.refresh_once()

    def set_indicator(self, indicator: str, enabled: bool) -> None:
        if enabled:
            self._indicators.add(indicator)
        else:
            self._indicators.discard(indicator)
        self._apply_request()
        self._refresh_service.refresh_once()

    def refresh_now(self) -> None:
        self._apply_request()
        self._refresh_service.refresh_once()

    def set_auto_refresh(self, enabled: bool) -> None:
        self._refresh_service.set_auto_refresh(enabled)

    def _apply_request(self) -> None:
        self._refresh_service.set_request(
            symbol=self._symbol,
            exchange=self._exchange,
            timeframe=self._timeframe,
            indicators=self._indicators,
        )
