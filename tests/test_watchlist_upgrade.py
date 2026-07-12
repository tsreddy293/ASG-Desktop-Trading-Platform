from src.market.watchlist_service import WatchListService


def test_watchlist_supports_extended_fields_and_duplicates() -> None:
    service = WatchListService(db_path=':memory:')
    service.add_symbol('RELIANCE', 'Reliance Industries', 'NSE', '1245.50', 'Up')
    service.add_symbol('RELIANCE', 'Reliance Industries', 'NSE', '1245.50', 'Up')
    entries = service.list_entries()
    assert len(entries) == 1
    assert entries[0].exchange == 'NSE'
    assert entries[0].live_price == 1245.5
    assert entries[0].trend == 'Up'


def test_watchlist_resolve_selection_maps_common_inputs() -> None:
    service = WatchListService(db_path=':memory:')
    assert service.resolve_selection('reliance') == ('RELIANCE', 'Reliance Industries')
    assert service.resolve_selection('SBIN') == ('SBIN', 'State Bank of India')
    assert service.resolve_selection('Tata Consultancy Services') == ('TCS', 'Tata Consultancy Services')
