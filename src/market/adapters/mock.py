from __future__ import annotations

from datetime import datetime, timezone

from src.market.adapters.base import LiveMarketRow


class MockMarketAdapter:
    """Mock adapter used until broker authentication and live APIs are enabled."""

    name = "mock"

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def fetch_live_market(self, exchange: str, symbol_query: str = "") -> list[LiveMarketRow]:
        if not self._connected:
            raise RuntimeError("Mock adapter is disconnected")

        query = symbol_query.strip().lower()
        rows = [
            LiveMarketRow("SBIN", "State Bank of India", "NSE", 812.25, 1.42, 15420000, 821.30, 803.40, datetime.now(timezone.utc)),
            LiveMarketRow("RELIANCE", "Reliance Industries", "NSE", 2824.40, 0.81, 11840000, 2852.00, 2798.20, datetime.now(timezone.utc)),
            LiveMarketRow("TCS", "Tata Consultancy Services", "NSE", 3956.10, -0.54, 9410000, 4010.50, 3921.30, datetime.now(timezone.utc)),
            LiveMarketRow("INFY", "Infosys", "NSE", 1870.65, 0.67, 8650000, 1898.10, 1848.20, datetime.now(timezone.utc)),
            LiveMarketRow("ITC", "ITC Limited", "NSE", 465.20, 0.48, 6210000, 470.00, 459.40, datetime.now(timezone.utc)),
            LiveMarketRow("SBIN", "State Bank of India", "BSE", 811.80, 1.35, 842000, 820.40, 804.10, datetime.now(timezone.utc)),
            LiveMarketRow("RELIANCE", "Reliance Industries", "BSE", 2823.20, 0.77, 692000, 2849.90, 2800.40, datetime.now(timezone.utc)),
            LiveMarketRow("TCS", "Tata Consultancy Services", "BSE", 3954.85, -0.49, 511000, 4008.60, 3924.10, datetime.now(timezone.utc)),
        ]

        filtered = [row for row in rows if row.exchange == exchange.upper()]
        if query:
            filtered = [
                row for row in filtered if query in row.symbol.lower() or query in row.company.lower()
            ]
        return filtered

    def supports_streaming(self) -> bool:
        return False

    def subscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None

    def unsubscribe_stream(self, exchange: str, symbols: list[str]) -> None:
        return None
