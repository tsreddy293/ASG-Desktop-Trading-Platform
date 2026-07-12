from __future__ import annotations

from PySide6.QtWidgets import QApplication

from src.ui.orders_page import OrdersPage


def test_orders_page_has_required_place_order_controls() -> None:
    app = QApplication.instance() or QApplication([])
    page = OrdersPage()

    assert page.tabs.count() == 3

    order_types = [page.order_type_combo.itemText(i) for i in range(page.order_type_combo.count())]
    assert order_types == ["MARKET", "LIMIT", "SL", "SL-M"]

    product_types = [page.product_combo.itemText(i) for i in range(page.product_combo.count())]
    assert product_types == ["CNC", "MIS", "NRML"]

    assert page.buy_button.text() == "BUY"
    assert page.sell_button.text() == "SELL"
    assert page.reset_button.text() == "RESET"

    page.close()
    app.quit()


def test_orders_page_has_required_tables() -> None:
    app = QApplication.instance() or QApplication([])
    page = OrdersPage()

    order_headers = [page.order_table.horizontalHeaderItem(i).text() for i in range(page.order_table.columnCount())]
    assert order_headers == [
        "Order ID",
        "Symbol",
        "Buy/Sell",
        "Quantity",
        "Executed Qty",
        "Pending Qty",
        "Price",
        "Status",
        "Time",
    ]

    trade_headers = [page.trade_table.horizontalHeaderItem(i).text() for i in range(page.trade_table.columnCount())]
    assert trade_headers == [
        "Trade ID",
        "Order ID",
        "Symbol",
        "Buy/Sell",
        "Price",
        "Quantity",
        "Exchange",
        "Trade Time",
    ]

    page.close()
    app.quit()
