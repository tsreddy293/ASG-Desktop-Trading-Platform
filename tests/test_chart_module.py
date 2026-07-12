from PySide6.QtWidgets import QApplication

from src.chart.model import ChartRequest
from src.chart.service import ChartService
from src.ui.main_window import MainWindow


def test_chart_service_returns_mock_candles_and_indicators() -> None:
    service = ChartService()
    payload = service.load_chart(
        ChartRequest(symbol="SBIN", exchange="NSE", timeframe="15 Minute"),
        {"EMA", "SMA", "VWAP", "Bollinger Bands", "Volume"},
    )

    assert payload.data.symbol == "SBIN"
    assert payload.data.exchange == "NSE"
    assert payload.data.timeframe == "15 Minute"
    assert len(payload.data.candles) >= 100
    assert payload.last_price > 0
    assert "EMA" in payload.indicators
    assert "SMA" in payload.indicators
    assert "VWAP" in payload.indicators
    assert "BB_UPPER" in payload.indicators


def test_charts_navigation_routes_to_reusable_chart_page() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)

    tree = window.navigation.menu_tree
    charts_item = None
    for index in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(index)
        if top.text(0) == "Charts":
            charts_item = top
            break

    assert charts_item is not None
    tree.setCurrentItem(charts_item)
    app.processEvents()
    assert window.pages.currentWidget() is window.charts_page

    window.close()
    app.quit()
