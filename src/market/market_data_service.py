from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.config import config
from src.core.translation import t
from src.market.adapters import LiveMarketRow, MarketAdapter
from src.marketdata.model import MarketDataEvent
from src.marketdata.service import market_data_service


@dataclass(slots=True)
class MarketDataResult:
    rows: list[LiveMarketRow]
    changed_symbols: list[str]
    removed_symbols: list[str]
    loading: bool
    reconnecting: bool
    last_updated: datetime | None
    error: str | None
    full_reload: bool


@dataclass(slots=True)
class OptionChainServiceRow:
    strike_price: int
    ce_ltp: float
    ce_oi: int
    ce_change_oi: int
    pe_oi: int
    pe_change_oi: int
    pe_ltp: float
    iv: float
    pcr: float


@dataclass(slots=True)
class OptionChainServiceSnapshot:
    underlying: str
    expiry: str
    spot_price: float
    atm_strike: int
    pcr: float
    iv: float
    last_updated: datetime
    rows: list[OptionChainServiceRow]


class MarketDataService:
    """Compatibility service facade over central market_data_service."""

    def __init__(self, adapter: MarketAdapter | None = None, refresh_interval_seconds: float | None = None) -> None:
        self.refresh_interval_seconds = float(
            refresh_interval_seconds
            if refresh_interval_seconds is not None
            else 1
        )
        self.refresh_interval_seconds = 1.0

        self._adapter = adapter
        self._exchange = "NSE"
        self._symbol_query = ""
        self._last_updated: datetime | None = None
        self._loading = False
        self._reconnecting = False
        self._cache: dict[str, LiveMarketRow] = {}

    def set_exchange(self, exchange: str) -> None:
        normalized = (exchange or "NSE").strip().upper()
        self._exchange = normalized if normalized in {"NSE", "BSE"} else "NSE"

    def set_symbol_query(self, symbol_query: str) -> None:
        self._symbol_query = symbol_query.strip()

    def get_exchange(self) -> str:
        return self._exchange

    def get_symbol_query(self) -> str:
        return self._symbol_query

    def supports_streaming(self) -> bool:
        return self._adapter.supports_streaming() if self._adapter is not None else True

    def subscribe(self, handler) -> None:
        market_data_service.subscribe(handler)

    def unsubscribe(self, handler) -> None:
        market_data_service.unsubscribe(handler)

    def get_option_chain_underlyings(self) -> list[str]:
        return ["NIFTY", "BANKNIFTY", "FINNIFTY"]

    def get_option_chain_expiries(self, underlying: str) -> list[str]:
        normalized = (underlying or "NIFTY").upper()
        if normalized == "BANKNIFTY":
            return ["30 Jul 2026", "06 Aug 2026", "13 Aug 2026"]
        if normalized == "FINNIFTY":
            return ["28 Jul 2026", "04 Aug 2026", "11 Aug 2026"]
        return ["31 Jul 2026", "07 Aug 2026", "14 Aug 2026"]

    def get_option_chain_snapshot(self, underlying: str, expiry: str) -> OptionChainServiceSnapshot:
        central = market_data_service.get_option_chain(underlying, expiry)
        rows = [
            OptionChainServiceRow(
                strike_price=row.strike_price,
                ce_ltp=row.ce_ltp,
                ce_oi=row.ce_oi,
                ce_change_oi=row.ce_change_oi,
                pe_oi=row.pe_oi,
                pe_change_oi=row.pe_change_oi,
                pe_ltp=row.pe_ltp,
                iv=row.iv,
                pcr=row.pcr,
            )
            for row in central.rows
        ]
        return OptionChainServiceSnapshot(
            underlying=central.underlying,
            expiry=central.expiry,
            spot_price=central.spot_price,
            atm_strike=central.atm_strike,
            pcr=central.pcr,
            iv=central.iv,
            last_updated=central.timestamp,
            rows=rows,
        )

    def refresh_live_market(self) -> MarketDataResult:
        self._loading = True
        full_reload = False
        error_message = None

        try:
            if self._adapter is not None:
                if not self._adapter.is_connected():
                    self._reconnecting = True
                    self._adapter.connect()
                    full_reload = True
                rows = self._adapter.fetch_live_market(self._exchange, self._symbol_query)
            else:
                quotes = market_data_service.get_live_quotes(self._exchange, self._symbol_query)
                rows = [
                    LiveMarketRow(
                        symbol=quote.symbol,
                        company=quote.company,
                        exchange=quote.exchange,
                        ltp=quote.ltp,
                        change_percent=quote.change_percent,
                        volume=quote.volume,
                        high=quote.high,
                        low=quote.low,
                        timestamp=quote.timestamp,
                        open=quote.open,
                        close=quote.previous_close,
                        bid=quote.bid,
                        ask=quote.ask,
                    )
                    for quote in quotes
                ]
                self._reconnecting = bool(getattr(market_data_service, "is_reconnecting", lambda: False)())
                service_error_getter = getattr(market_data_service, "last_error", None)
                service_error = service_error_getter() if callable(service_error_getter) else None

                if not rows and self._cache:
                    rows = list(self._cache.values())

                if self._reconnecting and service_error:
                    error_message = "Broker connection unavailable."
                else:
                    error_message = None

            changed_symbols, removed_symbols = self._apply_diff(rows)
            self._loading = False
            if self._adapter is not None:
                self._reconnecting = False
            self._last_updated = datetime.now(timezone.utc)
            return MarketDataResult(
                rows=rows,
                changed_symbols=changed_symbols,
                removed_symbols=removed_symbols,
                loading=self._loading,
                reconnecting=self._reconnecting,
                last_updated=self._last_updated,
                error=error_message,
                full_reload=full_reload,
            )
        except Exception as exc:
            self._loading = False
            self._reconnecting = True
            return MarketDataResult(
                rows=list(self._cache.values()),
                changed_symbols=[],
                removed_symbols=[],
                loading=self._loading,
                reconnecting=self._reconnecting,
                last_updated=self._last_updated,
                error=str(exc),
                full_reload=False,
            )

    def _apply_diff(self, rows: list[LiveMarketRow]) -> tuple[list[str], list[str]]:
        next_cache: dict[str, LiveMarketRow] = {row.symbol: row for row in rows}
        changed: list[str] = []

        for symbol, row in next_cache.items():
            previous = self._cache.get(symbol)
            if previous is None:
                changed.append(symbol)
                continue
            if not self._is_same(previous, row):
                changed.append(symbol)

        removed = [symbol for symbol in self._cache if symbol not in next_cache]
        self._cache = next_cache
        return changed, removed

    @staticmethod
    def _is_same(previous: LiveMarketRow, current: LiveMarketRow) -> bool:
        return (
            previous.company == current.company
            and previous.exchange == current.exchange
            and previous.ltp == current.ltp
            and previous.change_percent == current.change_percent
            and previous.volume == current.volume
            and previous.high == current.high
            and previous.low == current.low
        )


def market_event_symbols(event: MarketDataEvent) -> list[str]:
    return event.symbols
