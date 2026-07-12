from __future__ import annotations

from datetime import datetime
from typing import Protocol

from PySide6.QtCore import QObject, QTimer, Signal

from src.marketdata.service import MarketDataService, market_data_service
from src.ui.market_watch.models import DepthLevel, MarketDepthSnapshot, MarketWatchState, WatchQuote


class MarketDataBackend(Protocol):
    def get_quotes(self, symbols: list[str]) -> list[dict]:
        ...

    def get_market_depth(self, symbol: str) -> dict:
        ...

    def get_quote(self, symbol: str):
        ...


class MarketWatchBackgroundService(QObject):
    """Single refresh service for market watch quotes and depth."""

    state_updated = Signal(object)

    def __init__(self, backend: MarketDataBackend | None = None, interval_ms: int = 2000) -> None:
        super().__init__()
        self._backend = backend or market_data_service
        self._interval_ms = max(1000, int(interval_ms))
        self._symbols: list[str] = []
        self._selected_symbol: str | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.refresh_once)

    def set_symbols(self, symbols: list[str]) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            cleaned = str(symbol or "").strip().upper()
            if not cleaned or cleaned in seen:
                continue
            unique.append(cleaned)
            seen.add(cleaned)
        self._symbols = unique

    def set_selected_symbol(self, symbol: str | None) -> None:
        cleaned = str(symbol or "").strip().upper()
        self._selected_symbol = cleaned or None

    def start(self) -> None:
        self._timer.start()
        self.refresh_once()

    def stop(self) -> None:
        self._timer.stop()

    def refresh_once(self) -> None:
        try:
            quotes_raw = self._backend.get_quotes(self._symbols) if self._symbols else []
            quotes = [self._normalize_quote(row) for row in quotes_raw]

            depth_snapshot = None
            if self._selected_symbol:
                depth_raw = self._backend.get_market_depth(self._selected_symbol)
                depth_snapshot = self._normalize_depth(self._selected_symbol, depth_raw)

            state = MarketWatchState(
                connected=True,
                last_updated=datetime.now(),
                quotes=quotes,
                depth=depth_snapshot,
                error=None,
            )
            self.state_updated.emit(state)
        except Exception as exc:
            state = MarketWatchState(
                connected=False,
                last_updated=datetime.now(),
                quotes=[],
                depth=None,
                error=str(exc),
            )
            self.state_updated.emit(state)

    @staticmethod
    def _normalize_quote(row: dict) -> WatchQuote:
        ltp = float(row.get("ltp", 0.0) or 0.0)
        close = float(row.get("close", 0.0) or 0.0)
        change = float(row.get("change", ltp - close) or (ltp - close))
        change_percent = float(row.get("change_percent", ((change / close) * 100.0 if close else 0.0)) or 0.0)
        return WatchQuote(
            symbol=str(row.get("symbol", "")).upper(),
            ltp=ltp,
            change=change,
            change_percent=change_percent,
            open=float(row.get("open", 0.0) or 0.0),
            high=float(row.get("high", 0.0) or 0.0),
            low=float(row.get("low", 0.0) or 0.0),
            close=close,
            volume=int(row.get("volume", 0) or 0),
            bid=float(row.get("bid", 0.0) or 0.0),
            ask=float(row.get("ask", 0.0) or 0.0),
            timestamp=row.get("timestamp") if hasattr(row.get("timestamp"), "astimezone") else None,
        )

    @staticmethod
    def _normalize_depth(symbol: str, payload: dict) -> MarketDepthSnapshot:
        buy_levels = list(payload.get("buy_levels", []))[:5]
        sell_levels = list(payload.get("sell_levels", []))[:5]

        levels: list[DepthLevel] = []
        max_rows = max(len(buy_levels), len(sell_levels), 5)
        for index in range(max_rows):
            buy = buy_levels[index] if index < len(buy_levels) else {}
            sell = sell_levels[index] if index < len(sell_levels) else {}
            levels.append(
                DepthLevel(
                    bid_qty=int(buy.get("quantity", 0) or 0),
                    bid_price=float(buy.get("price", 0.0) or 0.0),
                    ask_price=float(sell.get("price", 0.0) or 0.0),
                    ask_qty=int(sell.get("quantity", 0) or 0),
                )
            )

        timestamp = payload.get("timestamp")
        return MarketDepthSnapshot(
            symbol=symbol,
            levels=levels,
            timestamp=timestamp if hasattr(timestamp, "astimezone") else None,
        )
