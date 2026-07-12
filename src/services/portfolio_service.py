from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.marketdata.service import market_data_service


@dataclass(slots=True)
class PositionRow:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    ltp: float
    mtm: float
    realized_pnl: float
    unrealized_pnl: float
    product: str
    segment: str
    open_position: bool


@dataclass(slots=True)
class HoldingRow:
    symbol: str
    exchange: str
    quantity: int
    average_cost: float
    ltp: float
    current_value: float
    day_change: float
    total_profit: float
    holding_type: str


@dataclass(slots=True)
class PortfolioSummary:
    available_cash: float
    margin_used: float
    total_investment: float
    current_value: float
    todays_profit: float
    overall_profit: float
    updated_at: datetime


class MarketServiceProtocol(Protocol):
    def subscribe(self, handler):
        ...

    def unsubscribe(self, handler):
        ...

    def get_portfolio_positions(self):
        ...

    def get_quote(self, symbol: str, exchange: str = "NSE"):
        ...


class PortfolioService:
    """Service layer for positions/holdings/portfolio fed by MarketDataService."""

    def __init__(self, market_service: MarketServiceProtocol | None = None) -> None:
        self._market_service = market_service or market_data_service

    def subscribe(self, handler) -> None:
        self._market_service.subscribe(handler)

    def unsubscribe(self, handler) -> None:
        self._market_service.unsubscribe(handler)

    def get_positions(self) -> list[PositionRow]:
        rows = self._market_service.get_portfolio_positions()
        positions: list[PositionRow] = []

        for item in rows:
            qty = int(getattr(item, "quantity", 0) or 0)
            avg = float(getattr(item, "average_price", 0.0) or 0.0)
            ltp = float(getattr(item, "ltp", 0.0) or 0.0)
            unrealized = (ltp - avg) * qty
            realized = float(getattr(item, "realized_pnl", 0.0) or 0.0)
            mtm = unrealized + realized

            positions.append(
                PositionRow(
                    symbol=str(getattr(item, "symbol", "")).upper(),
                    exchange="NSE",
                    quantity=qty,
                    average_price=avg,
                    ltp=ltp,
                    mtm=mtm,
                    realized_pnl=realized,
                    unrealized_pnl=unrealized,
                    product="MIS" if qty != 0 else "CNC",
                    segment="EQUITY",
                    open_position=qty != 0,
                )
            )
        return positions

    def get_holdings(self) -> list[HoldingRow]:
        positions = self.get_positions()
        holdings: list[HoldingRow] = []
        for pos in positions:
            qty = max(0, pos.quantity)
            current_value = qty * pos.ltp
            invested = qty * pos.average_price
            total_profit = current_value - invested
            day_change = (pos.ltp - pos.average_price) * qty * 0.15
            holdings.append(
                HoldingRow(
                    symbol=pos.symbol,
                    exchange=pos.exchange,
                    quantity=qty,
                    average_cost=pos.average_price,
                    ltp=pos.ltp,
                    current_value=current_value,
                    day_change=day_change,
                    total_profit=total_profit,
                    holding_type="CNC",
                )
            )
        return holdings

    def get_summary(self) -> PortfolioSummary:
        positions = self.get_positions()
        total_investment = sum(max(0, p.quantity) * p.average_price for p in positions)
        current_value = sum(max(0, p.quantity) * p.ltp for p in positions)
        overall_profit = current_value - total_investment
        todays_profit = sum((p.ltp - p.average_price) * max(0, p.quantity) * 0.15 for p in positions)
        margin_used = sum(abs(p.quantity) * p.average_price * 0.2 for p in positions if p.quantity != 0)
        available_cash = max(0.0, 1_000_000.0 - margin_used)
        return PortfolioSummary(
            available_cash=available_cash,
            margin_used=margin_used,
            total_investment=total_investment,
            current_value=current_value,
            todays_profit=todays_profit,
            overall_profit=overall_profit,
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def sort_positions(rows: list[PositionRow], mode: str) -> list[PositionRow]:
        key = str(mode or "").strip().lower()
        if key == "highest profit":
            return sorted(rows, key=lambda r: r.unrealized_pnl + r.realized_pnl, reverse=True)
        if key == "highest loss":
            return sorted(rows, key=lambda r: r.unrealized_pnl + r.realized_pnl)
        if key == "exchange":
            return sorted(rows, key=lambda r: (r.exchange, r.symbol))
        return sorted(rows, key=lambda r: r.symbol)

    @staticmethod
    def filter_positions(rows: list[PositionRow], mode: str) -> list[PositionRow]:
        key = str(mode or "ALL").strip().upper()
        if key == "OPEN POSITIONS":
            return [r for r in rows if r.open_position]
        if key == "CLOSED POSITIONS":
            return [r for r in rows if not r.open_position]
        if key == "INTRADAY":
            return [r for r in rows if r.product == "MIS"]
        if key == "DELIVERY":
            return [r for r in rows if r.product == "CNC"]
        if key == "F&O":
            return [r for r in rows if r.segment == "F&O"]
        if key == "EQUITY":
            return [r for r in rows if r.segment == "EQUITY"]
        return list(rows)
