from __future__ import annotations

from datetime import datetime, timezone

from src.market.adapters.base import LiveMarketRow
from src.market.market_data_service import MarketDataService


class StaticAdapter:
    name = "static"

    def __init__(self) -> None:
        self._connected = False
        self._rows: list[LiveMarketRow] = [
            LiveMarketRow("SBIN", "State Bank of India", "NSE", 800.0, 0.5, 1000, 810.0, 790.0, datetime.now(timezone.utc)),
            LiveMarketRow("RELIANCE", "Reliance Industries", "NSE", 2800.0, 0.8, 2000, 2820.0, 2780.0, datetime.now(timezone.utc)),
        ]

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def fetch_live_market(self, exchange: str, symbol_query: str = "") -> list[LiveMarketRow]:
        return [row for row in self._rows if row.exchange == exchange and symbol_query.lower() in row.symbol.lower()]

    def supports_streaming(self) -> bool:
        return True

    def subscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None

    def unsubscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None


def test_market_data_service_refresh_tracks_changes() -> None:
    adapter = StaticAdapter()
    service = MarketDataService(adapter=adapter, refresh_interval_seconds=1)
    service.set_exchange("NSE")
    result_one = service.refresh_live_market()

    assert result_one.error is None
    assert result_one.reconnecting is False
    assert sorted(result_one.changed_symbols) == ["RELIANCE", "SBIN"]
    assert result_one.last_updated is not None

    result_two = service.refresh_live_market()
    assert result_two.changed_symbols == []


def test_market_data_service_applies_symbol_search() -> None:
    adapter = StaticAdapter()
    service = MarketDataService(adapter=adapter, refresh_interval_seconds=1)
    service.set_exchange("NSE")
    service.set_symbol_query("sbin")

    result = service.refresh_live_market()

    assert len(result.rows) == 1
    assert result.rows[0].symbol == "SBIN"


def test_option_chain_datasets_are_unique_per_underlying() -> None:
    service = MarketDataService(adapter=StaticAdapter(), refresh_interval_seconds=1)

    nifty = service.get_option_chain_snapshot("NIFTY", "31 Jul 2026")
    banknifty = service.get_option_chain_snapshot("BANKNIFTY", "30 Jul 2026")
    finnifty = service.get_option_chain_snapshot("FINNIFTY", "28 Jul 2026")

    assert 24900 <= nifty.spot_price <= 25100
    assert 57700 <= banknifty.spot_price <= 57950
    assert 28050 <= finnifty.spot_price <= 28180

    nifty_strikes = [row.strike_price for row in nifty.rows]
    banknifty_strikes = [row.strike_price for row in banknifty.rows]
    finnifty_strikes = [row.strike_price for row in finnifty.rows]

    assert min(nifty_strikes) >= 24600 and max(nifty_strikes) <= 25100
    assert min(banknifty_strikes) >= 57600 and max(banknifty_strikes) <= 58000
    assert min(finnifty_strikes) >= 27900 and max(finnifty_strikes) <= 28300
