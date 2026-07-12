from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal

from src.marketdata.service import MarketDataService, market_data_service


class DashboardViewModel(QObject):
    """ViewModel for dashboard and market widgets fed by MarketDataService."""

    indices_updated = Signal(dict)
    status_updated = Signal(str)
    activity_added = Signal(str)
    log_added = Signal(str)

    def __init__(self, market_data_service: MarketDataService | None = None, refresh_seconds: int = 4) -> None:
        super().__init__()
        self._service = market_data_service or market_data_service
        self.refresh_seconds = max(2, int(refresh_seconds))
        self._latest_indices: dict[str, dict[str, Any]] = {}

    def refresh_indices(self) -> None:
        try:
            rows = self._service.get_indices()
            normalized = self._normalize_indices(rows)
            self._latest_indices = normalized
            self.indices_updated.emit(normalized)
            self.status_updated.emit("Connected")
            self.activity_added.emit(f"{datetime.now().strftime('%H:%M:%S')} refreshed index snapshot")
        except Exception as exc:
            self.status_updated.emit("Session unavailable")
            self.log_added.emit(f"{datetime.now().strftime('%H:%M:%S')} index refresh failed: {exc}")
            if self._latest_indices:
                self.indices_updated.emit(self._latest_indices)

    def get_watchlist_quotes(self) -> list[dict[str, Any]]:
        try:
            return self._service.get_watchlist_quotes()
        except Exception as exc:
            self.log_added.emit(f"{datetime.now().strftime('%H:%M:%S')} watchlist quote error: {exc}")
            return []

    def get_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        if not symbols:
            return []
        try:
            return self._service.get_quotes(symbols)
        except Exception as exc:
            self.log_added.emit(f"{datetime.now().strftime('%H:%M:%S')} quote batch error: {exc}")
            return []

    def get_quote(self, symbol: str) -> dict[str, Any] | None:
        try:
            row = self._service.get_quote(symbol)
            if row is None:
                return None
            if isinstance(row, dict):
                return row
            return {
                "symbol": getattr(row, "symbol", str(symbol or "").upper()),
                "company": getattr(row, "company", str(symbol or "").upper()),
                "sector": getattr(row, "sector", "Unknown"),
                "exchange": getattr(row, "exchange", "NSE"),
                "ltp": getattr(row, "ltp", 0.0),
                "open": getattr(row, "open", 0.0),
                "high": getattr(row, "high", 0.0),
                "low": getattr(row, "low", 0.0),
                "close": getattr(row, "previous_close", 0.0),
                "change": getattr(row, "change", 0.0),
                "change_percent": getattr(row, "change_percent", 0.0),
                "volume": getattr(row, "volume", 0),
                "bid": getattr(row, "bid", 0.0),
                "ask": getattr(row, "ask", 0.0),
                "timestamp": getattr(row, "timestamp", None),
            }
        except Exception as exc:
            self.log_added.emit(f"{datetime.now().strftime('%H:%M:%S')} quote error for {symbol}: {exc}")
            return None

    @staticmethod
    def _normalize_indices(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        lookup = {str(row.get("symbol", "")).upper(): row for row in rows}
        required = {
            "NIFTY": "NIFTY",
            "BANKNIFTY": "BANKNIFTY",
            "SENSEX": "SENSEX",
            "VIX": "VIX",
        }

        out: dict[str, dict[str, Any]] = {}
        for label, symbol in required.items():
            row = lookup.get(symbol, {})
            ltp_raw = row.get("ltp")
            change_raw = row.get("change_percent")
            out[label] = {
                "symbol": symbol,
                "ltp": float(ltp_raw) if ltp_raw is not None else None,
                "change_percent": float(change_raw) if change_raw is not None else None,
                "timestamp": row.get("timestamp"),
            }
        return out
