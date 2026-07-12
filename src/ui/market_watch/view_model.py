from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, Signal

from src.brokers.fivepaisa.market_data_service import MarketDataService
from src.ui.market_watch.models import MarketWatchState, QuoteDetails, WatchQuote
from src.ui.market_watch.service import MarketDataBackend, MarketWatchBackgroundService


class MarketWatchViewModel(QObject):
    symbols_changed = Signal(list)
    state_changed = Signal(object)

    def __init__(self, backend: MarketDataBackend | None = None) -> None:
        super().__init__()
        self._backend = backend or MarketDataService()
        self._service = MarketWatchBackgroundService(self._backend, interval_ms=2000)
        self._service.state_updated.connect(self._on_state_updated)

        self._symbols: list[str] = ["HDFCBANK", "SBIN", "RELIANCE", "TCS"]
        self._pins: set[str] = set()
        self._search_text = ""
        self._latest_quotes: dict[str, WatchQuote] = {}
        self._selected_symbol: str | None = None

        self._service.set_symbols(self._symbols)

    def start(self) -> None:
        self._service.start()

    def stop(self) -> None:
        self._service.stop()

    def refresh(self) -> None:
        self._service.refresh_once()

    def set_auto_refresh(self, enabled: bool) -> None:
        if enabled:
            self._service.start()
        else:
            self._service.stop()

    def set_search_text(self, value: str) -> None:
        self._search_text = str(value or "").strip().upper()

    def add_symbol(self, symbol: str) -> None:
        cleaned = str(symbol or "").strip().upper()
        if not cleaned:
            return
        if cleaned not in self._symbols:
            self._symbols.append(cleaned)
            self._emit_symbols_changed()

    def remove_symbol(self, symbol: str) -> None:
        cleaned = str(symbol or "").strip().upper()
        self._symbols = [item for item in self._symbols if item != cleaned]
        self._pins.discard(cleaned)
        if self._selected_symbol == cleaned:
            self._selected_symbol = None
            self._service.set_selected_symbol(None)
        self._emit_symbols_changed()

    def toggle_pin(self, symbol: str) -> None:
        cleaned = str(symbol or "").strip().upper()
        if cleaned in self._pins:
            self._pins.remove(cleaned)
        else:
            self._pins.add(cleaned)
        self._emit_symbols_changed()

    def set_selected_symbol(self, symbol: str) -> None:
        cleaned = str(symbol or "").strip().upper()
        self._selected_symbol = cleaned or None
        self._service.set_selected_symbol(self._selected_symbol)

    def selected_symbol(self) -> str | None:
        return self._selected_symbol

    def visible_symbols(self) -> list[str]:
        symbols = list(self._symbols)
        if self._search_text:
            symbols = [sym for sym in symbols if self._search_text in sym]
        symbols.sort(key=lambda sym: (sym not in self._pins, sym))
        return symbols

    def is_pinned(self, symbol: str) -> bool:
        return str(symbol or "").strip().upper() in self._pins

    def quote_details(self, symbol: str) -> QuoteDetails:
        cleaned = str(symbol or "").strip().upper()
        quote = self._latest_quotes.get(cleaned)

        if quote is None:
            try:
                row = self._backend.get_quote(cleaned)
                quote = MarketWatchBackgroundService._normalize_quote(row)
            except Exception:
                quote = None

        if quote is None:
            return QuoteDetails(
                symbol=cleaned,
                ltp=None,
                open=None,
                high=None,
                low=None,
                close=None,
                upper_circuit=None,
                lower_circuit=None,
                week_52_high=None,
                week_52_low=None,
                volume=None,
                bid=None,
                ask=None,
                last_trade_time=None,
            )

        return QuoteDetails(
            symbol=cleaned,
            ltp=quote.ltp,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            upper_circuit=None,
            lower_circuit=None,
            week_52_high=None,
            week_52_low=None,
            volume=quote.volume,
            bid=quote.bid,
            ask=quote.ask,
            last_trade_time=quote.timestamp,
        )

    def _emit_symbols_changed(self) -> None:
        ordered = self.visible_symbols()
        self._service.set_symbols(ordered)
        self.symbols_changed.emit(ordered)

    def _on_state_updated(self, state: MarketWatchState) -> None:
        by_symbol = {row.symbol: row for row in state.quotes}
        self._latest_quotes = by_symbol

        ordered_quotes: list[WatchQuote] = []
        for symbol in self.visible_symbols():
            quote = by_symbol.get(symbol)
            if quote is not None:
                ordered_quotes.append(quote)

        emitted = MarketWatchState(
            connected=state.connected,
            last_updated=state.last_updated or datetime.now(),
            quotes=ordered_quotes,
            depth=state.depth,
            error=state.error,
        )
        self.state_changed.emit(emitted)
