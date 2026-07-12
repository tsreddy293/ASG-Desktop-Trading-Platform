from PySide6.QtWidgets import QApplication

from src.ui.dashboard_page import DashboardPage
from src.ui.market_watch_page import MarketWatchPage
from src.ui.watchlist_page import WatchListPage


def test_dashboard_has_required_index_cards() -> None:
    app = QApplication.instance() or QApplication([])
    page = DashboardPage()
    cards = set(page._cards.keys())
    assert cards == {"NIFTY", "BANKNIFTY", "SENSEX", "VIX"}
    assert page.connection_badge.text() != ""
    page.close()
    app.quit()


def test_market_watch_page_has_required_columns() -> None:
    app = QApplication.instance() or QApplication([])
    page = MarketWatchPage()
    expected = ["Symbol", "LTP", "Change", "Change %", "Open", "High", "Low", "Close", "Volume", "Pinned"]
    actual = [page.table.horizontalHeaderItem(index).text() for index in range(page.table.columnCount())]
    assert actual == expected
    assert page.depth_panel is not None
    page.close()
    app.quit()

def test_watchlist_page_has_live_watchlist_columns() -> None:
    app = QApplication.instance() or QApplication([])
    page = WatchListPage()
    expected = ["Symbol", "Company", "Exchange", "Live Price", "Change %", "Volume", "AI Rating", "Risk", "Favorite"]
    actual = [page.table.horizontalHeaderItem(index).text() for index in range(page.table.columnCount())]
    assert actual == expected
    assert page.live_quote_panel is not None
    page.close()
    app.quit()
