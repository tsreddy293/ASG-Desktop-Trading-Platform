from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def _find_item(window: MainWindow, label: str):
    tree = window.navigation.menu_tree
    for index in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(index)
        if top.text(0) == label:
            return top
    return None


def test_phase2_navigation_routes_to_existing_pages() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)

    market_watch_item = _find_item(window, "Market Watch")
    watchlist_item = _find_item(window, "Watchlist")
    scanner_item = _find_item(window, "Scanner")
    portfolio_item = _find_item(window, "Portfolio")

    assert market_watch_item is not None
    assert watchlist_item is not None
    assert scanner_item is not None
    assert portfolio_item is not None

    window.navigation.menu_tree.setCurrentItem(market_watch_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.market_watch_page

    window.navigation.menu_tree.setCurrentItem(watchlist_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.watchlist_page

    window.navigation.menu_tree.setCurrentItem(scanner_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.ai_scanner_page

    window.navigation.menu_tree.setCurrentItem(portfolio_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.portfolio_page

    window.close()
    app.quit()


def test_open_ai_analysis_navigates_to_analysis_page() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)

    window.open_ai_analysis("SBIN", "NSE")
    app.processEvents()
    assert window.pages.currentWidget() is window.ai_analysis_page

    window.close()
    app.quit()
