from PySide6.QtWidgets import QApplication

from src.ui.holdings_page import HoldingsPage
from src.ui.main_window import MainWindow
from src.ui.portfolio_summary_page import PortfolioSummaryPage
from src.ui.positions_page import PositionsPage


def test_positions_holdings_portfolio_pages_build() -> None:
    app = QApplication.instance() or QApplication([])

    positions = PositionsPage()
    holdings = HoldingsPage()
    portfolio = PortfolioSummaryPage()

    assert positions.table.columnCount() == 8
    assert holdings.table.columnCount() == 8
    assert len(portfolio._cards) == 6

    positions.close()
    holdings.close()
    portfolio.close()
    app.quit()


def test_main_window_routes_positions_and_holdings_pages() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)

    tree = window.navigation.menu_tree
    positions_item = None
    holdings_item = None
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.text(0) == "Positions":
            positions_item = item
        if item.text(0) == "Holdings":
            holdings_item = item

    assert positions_item is not None
    assert holdings_item is not None

    tree.setCurrentItem(positions_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.positions_page

    tree.setCurrentItem(holdings_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.holdings_page

    window.close()
    app.quit()
