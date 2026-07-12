from src.market.watchlist_service import WatchListService


def test_watchlist_service_supports_crud_and_favorites() -> None:
    service = WatchListService(db_path=':memory:')
    service.add_symbol('RELIANCE', 'Reliance Industries')
    service.add_symbol('TCS', 'Tata Consultancy Services')
    entries = service.list_entries()
    assert len(entries) == 2
    service.toggle_favorite(entries[0].id)
    favorite_entries = service.list_entries(favorites_only=True)
    assert len(favorite_entries) == 1
    service.delete_entry(entries[1].id)
    assert len(service.list_entries()) == 1
