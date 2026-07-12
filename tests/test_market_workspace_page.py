from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.workspace import ProfessionalMarketWorkspacePage


def test_workspace_page_has_required_dock_tabs() -> None:
    app = QApplication.instance() or QApplication([])
    page = ProfessionalMarketWorkspacePage()

    tab_labels = [page.bottom_tabs.tabText(i) for i in range(page.bottom_tabs.count())]
    assert tab_labels == ["Positions", "Orders", "Holdings", "Market Depth", "Option Chain", "AI Scanner"]

    page.close()
    app.quit()


def test_main_window_routes_to_market_workspace_page() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)

    tree = window.navigation.menu_tree
    target = None
    for i in range(tree.topLevelItemCount()):
        node = tree.topLevelItem(i)
        if node.text(0) == "Market Workspace":
            target = node
            break

    assert target is not None
    tree.setCurrentItem(target)
    app.processEvents()
    assert window.pages.currentWidget() is window.market_workspace_page

    window.close()
    app.quit()
