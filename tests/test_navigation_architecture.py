from PySide6.QtWidgets import QApplication

from src.ui.menu import NavigationMenu


def test_navigation_menu_contains_phase2_sections() -> None:
    app = QApplication.instance() or QApplication([])
    menu = NavigationMenu()

    top_level_labels = [menu.menu_tree.topLevelItem(index).text(0) for index in range(menu.menu_tree.topLevelItemCount())]

    assert "Dashboard" in top_level_labels
    assert "Market Watch" in top_level_labels
    assert "Watchlist" in top_level_labels
    assert "Scanner" in top_level_labels
    assert "Orders" in top_level_labels
    assert "Positions" in top_level_labels
    assert "Holdings" in top_level_labels
    assert "Portfolio" in top_level_labels
    assert "Strategy" in top_level_labels
    assert "Settings" in top_level_labels

    app.quit()
