from __future__ import annotations

from datetime import datetime, timezone

from src.marketdata.model import HistoricalCandle, MarketDepthLevel, MarketDepthSnapshot, MarketInstrument, OptionChainRow, OptionChainSnapshot, OrderRecord, PortfolioPosition


class MarketDataRepository:
    """Neutral in-memory repository for live market snapshots.

    This repository no longer generates mock market values.
    Data is expected to be populated by an external provider/service.
    """

    def __init__(self) -> None:
        self._state: dict[tuple[str, str], MarketInstrument] = {}
        self._option_chain: dict[tuple[str, str], OptionChainSnapshot] = {}
        self._history: dict[tuple[str, str, str], list[HistoricalCandle]] = {}
        self._positions: list[PortfolioPosition] = []
        self._orders: list[OrderRecord] = []

    def step_market(self) -> list[str]:
        return []

    def upsert_quotes(self, quotes: list[MarketInstrument]) -> None:
        for item in quotes:
            self._state[(item.exchange.upper(), item.symbol.upper())] = item

    def put_option_chain(self, snapshot: OptionChainSnapshot) -> None:
        self._option_chain[(snapshot.underlying.upper(), snapshot.expiry)] = snapshot

    def put_historical_candles(self, symbol: str, exchange: str, timeframe: str, candles: list[HistoricalCandle]) -> None:
        self._history[(exchange.upper(), symbol.upper(), timeframe)] = list(candles)

    def put_portfolio_positions(self, positions: list[PortfolioPosition]) -> None:
        self._positions = list(positions)

    def put_orders(self, orders: list[OrderRecord]) -> None:
        self._orders = list(orders)

    def get_quotes(self, exchange: str = "NSE", symbol_query: str = "") -> list[MarketInstrument]:
        ex = exchange.upper()
        query = symbol_query.strip().lower()
        rows = [item for (item_exchange, _), item in self._state.items() if item_exchange == ex]
        if query:
            rows = [row for row in rows if query in row.symbol.lower() or query in row.company.lower()]
        return sorted(rows, key=lambda item: item.symbol)

    def get_quote(self, symbol: str, exchange: str = "NSE") -> MarketInstrument | None:
        return self._state.get((exchange.upper(), symbol.upper()))

    def get_market_depth(self, symbol: str, exchange: str = "NSE") -> MarketDepthSnapshot:
        quote = self.get_quote(symbol, exchange)
        now = datetime.now(timezone.utc)
        if quote is None:
            return MarketDepthSnapshot(
                symbol=symbol.upper(),
                exchange=exchange.upper(),
                bid=0.0,
                ask=0.0,
                spread=0.0,
                buy_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)],
                sell_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)],
                timestamp=now,
            )

        buy_levels = [MarketDepthLevel(price=max(0.0, quote.bid - i * 0.05), quantity=0, orders=0) for i in range(5)]
        sell_levels = [MarketDepthLevel(price=max(0.0, quote.ask + i * 0.05), quantity=0, orders=0) for i in range(5)]
        return MarketDepthSnapshot(
            symbol=quote.symbol,
            exchange=quote.exchange,
            bid=quote.bid,
            ask=quote.ask,
            spread=max(0.0, quote.ask - quote.bid),
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            timestamp=quote.timestamp,
        )

    def get_option_chain(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        key = (underlying.upper(), expiry)
        snapshot = self._option_chain.get(key)
        if snapshot is not None:
            return snapshot
        return OptionChainSnapshot(
            underlying=underlying.upper(),
            expiry=expiry,
            spot_price=0.0,
            atm_strike=0,
            pcr=0.0,
            iv=0.0,
            rows=[
                OptionChainRow(
                    strike_price=0,
                    ce_ltp=0.0,
                    ce_oi=0,
                    pe_oi=0,
                    pe_ltp=0.0,
                    iv=0.0,
                    pcr=0.0,
                    ce_change_oi=0,
                    pe_change_oi=0,
                )
            ],
            timestamp=datetime.now(timezone.utc),
        )

    def get_historical_candles(self, symbol: str, exchange: str, timeframe: str, points: int, minutes_step: int) -> list[HistoricalCandle]:
        return list(self._history.get((exchange.upper(), symbol.upper(), timeframe), []))

    def get_portfolio_positions(self) -> list[PortfolioPosition]:
        return list(self._positions)

    def get_orders(self) -> list[OrderRecord]:
        return list(self._orders)
