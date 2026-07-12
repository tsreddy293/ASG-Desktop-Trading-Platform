from __future__ import annotations

from datetime import datetime, timezone

from src.market.cache import MarketSnapshot
from src.market.data_provider import MarketProviderError
from src.market.market_data import MarketDataManager, MarketEventType, MarketStatus
from src.market.symbols import MarketSymbol
from src.market.watchlist_service import WatchListService


class DummyProvider:
    def __init__(self) -> None:
        self.connected = False
        self.connect_calls = 0
        self.disconnect_calls = 0

    def connect(self) -> None:
        self.connected = True
        self.connect_calls += 1

    def disconnect(self) -> None:
        self.connected = False
        self.disconnect_calls += 1

    def is_connected(self) -> bool:
        return self.connected

    def fetch_snapshots(self, symbols: list[MarketSymbol]) -> list[MarketSnapshot]:
        now = datetime.now(timezone.utc)
        snapshots: list[MarketSnapshot] = []
        for symbol in symbols:
            snapshots.append(
                MarketSnapshot(
                    symbol=symbol.symbol,
                    company=symbol.company,
                    exchange=symbol.exchange,
                    ltp=101.5,
                    open=100.0,
                    high=103.0,
                    low=99.0,
                    previous_close=100.0,
                    change=1.5,
                    change_percent=1.5,
                    volume=25000,
                    bid=101.4,
                    ask=101.6,
                    timestamp=now,
                )
            )
        return snapshots


class FlakyProvider(DummyProvider):
    def __init__(self) -> None:
        super().__init__()
        self._first = True

    def fetch_snapshots(self, symbols: list[MarketSymbol]) -> list[MarketSnapshot]:
        if self._first:
            self._first = False
            raise MarketProviderError("temporary connection drop")
        return super().fetch_snapshots(symbols)


def test_market_data_manager_refresh_populates_cache_and_emits_events() -> None:
    watchlist = WatchListService(db_path=":memory:")
    watchlist.add_symbol("RELIANCE", "Reliance Industries", "NSE", 0.0, "Neutral")

    provider = DummyProvider()
    manager = MarketDataManager(watchlist_service=watchlist, provider=provider, refresh_interval_seconds=1)

    received_events = []
    manager.subscribe(received_events.append)
    manager.load_watchlist()

    snapshots = manager.refresh_once()

    assert len(snapshots) == 1
    snapshot = manager.get_snapshot("RELIANCE")
    assert snapshot is not None
    assert snapshot.symbol == "RELIANCE"
    assert snapshot.company == "Reliance Industries"
    assert snapshot.exchange == "NSE"
    assert snapshot.ltp == 101.5
    assert snapshot.open == 100.0
    assert snapshot.high == 103.0
    assert snapshot.low == 99.0
    assert snapshot.previous_close == 100.0
    assert snapshot.change == 1.5
    assert snapshot.change_percent == 1.5
    assert snapshot.volume == 25000
    assert snapshot.bid == 101.4
    assert snapshot.ask == 101.6

    event_types = {event.event_type for event in received_events}
    assert MarketEventType.STATUS in event_types
    assert MarketEventType.CACHE_UPDATED in event_types


def test_market_data_manager_handles_reconnect_gracefully(monkeypatch) -> None:
    watchlist = WatchListService(db_path=":memory:")
    watchlist.add_symbol("SBIN", "State Bank of India", "NSE", 0.0, "Neutral")

    provider = FlakyProvider()
    manager = MarketDataManager(watchlist_service=watchlist, provider=provider, refresh_interval_seconds=1)

    events = []
    manager.subscribe(events.append)
    manager.load_watchlist()

    monkeypatch.setattr("src.market.market_data.sleep", lambda *_: None)

    first_result = manager.refresh_once()
    second_result = manager.refresh_once()

    assert first_result == []
    assert len(second_result) == 1
    assert provider.connect_calls >= 1

    event_types = [event.event_type for event in events]
    assert MarketEventType.ERROR in event_types
    assert MarketEventType.CONNECTION in event_types


def test_market_status_detects_open_and_closed() -> None:
    manager = MarketDataManager(watchlist_service=WatchListService(db_path=":memory:"), provider=DummyProvider())

    open_time = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
    weekend = datetime(2026, 7, 11, 10, 0, tzinfo=timezone.utc)

    assert manager.market_status(open_time) in {MarketStatus.OPEN, MarketStatus.PRE_OPEN, MarketStatus.POST_CLOSE}
    assert manager.market_status(weekend) == MarketStatus.CLOSED
