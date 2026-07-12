from __future__ import annotations

from datetime import datetime


class WorkspaceService:
    """Placeholder workspace service for panels not yet wired to backend modules."""

    def get_watchlist(self) -> list[str]:
        return ["HDFCBANK", "SBIN", "RELIANCE", "INFY", "TCS"]

    def get_chart_state(self) -> dict:
        return {
            "symbol": "SBIN",
            "timeframe": "15m",
            "chart_type": "Candlestick",
            "status": "Connected",
        }

    def get_positions(self) -> list[dict]:
        return [
            {"symbol": "SBIN", "qty": 20, "avg": 801.5, "ltp": 812.2, "pnl": 214.0},
            {"symbol": "HDFCBANK", "qty": 10, "avg": 1688.0, "ltp": 1702.4, "pnl": 144.0},
        ]

    def get_orders(self) -> list[dict]:
        return [
            {"order_id": "OID-101", "symbol": "SBIN", "side": "BUY", "qty": 20, "status": "OPEN"},
            {"order_id": "OID-102", "symbol": "TCS", "side": "SELL", "qty": 5, "status": "COMPLETE"},
        ]

    def get_holdings(self) -> list[dict]:
        return [
            {"symbol": "INFY", "qty": 15, "avg": 1821.4, "ltp": 1850.2},
            {"symbol": "RELIANCE", "qty": 7, "avg": 2891.0, "ltp": 2922.5},
        ]

    def get_market_depth(self) -> list[dict]:
        return [
            {"bid_qty": 1200, "bid": 812.10, "ask": 812.25, "ask_qty": 1000},
            {"bid_qty": 950, "bid": 812.05, "ask": 812.30, "ask_qty": 875},
        ]

    def get_option_chain(self) -> list[dict]:
        return [
            {"strike": 25000, "ce_ltp": 122.5, "pe_ltp": 95.0, "pcr": 0.89},
            {"strike": 25100, "ce_ltp": 101.2, "pe_ltp": 112.3, "pcr": 1.02},
        ]

    def get_ai_scanner(self) -> list[dict]:
        now = datetime.now().strftime("%H:%M:%S")
        return [
            {"symbol": "SBIN", "signal": "Breakout", "confidence": "87%", "time": now},
            {"symbol": "HDFCBANK", "signal": "Momentum", "confidence": "81%", "time": now},
        ]
