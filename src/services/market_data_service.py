from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event, RLock, Thread
from time import sleep
from typing import Callable

from src.core.config import config
from src.core.logger import app_logger
from src.brokers import BrokerConnectionError, broker_manager
from src.marketdata.model import HistoricalCandle, MarketDataEvent, MarketDepthLevel, MarketDepthSnapshot, MarketEventType, MarketInstrument, OptionChainRow, OptionChainSnapshot, OrderRecord, PortfolioPosition
from src.services.market_cache import MarketCache
from src.services.websocket_service import WebSocketService


EventHandler = Callable[[MarketDataEvent], None]


@dataclass(slots=True)
class ServiceUniverse:
    exchanges: tuple[str, ...] = ("NSE", "BSE")
    instruments: tuple[str, ...] = ("EQUITY", "FUTURES", "OPTIONS", "INDICES")


class MarketDataService:
    """Centralized market data service used by all modules."""

    _TF_MAP = {
        "1 Minute": (1, 180),
        "5 Minute": (5, 180),
        "15 Minute": (15, 170),
        "30 Minute": (30, 150),
        "1 Hour": (60, 120),
        "Daily": (60 * 24, 110),
        "Weekly": (60 * 24 * 7, 90),
        "Monthly": (60 * 24 * 30, 72),
    }

    def __init__(self) -> None:
        self._broker_manager = broker_manager
        self.universe = ServiceUniverse()
        self.refresh_interval_seconds = max(1.0, float(config.get("market_refresh_interval_seconds", 1) or 1.0))
        self._handlers: list[EventHandler] = []
        self._lock = RLock()
        self._worker: Thread | None = None
        self._stop = Event()
        self._cache = MarketCache(ttl_seconds=max(2.0, self.refresh_interval_seconds * 2.5))
        self._quotes: dict[tuple[str, str], MarketInstrument] = {}
        self._reconnecting = False
        self._last_error = ""
        self._ws = WebSocketService(self._broker_manager.login, self._broker_manager.logout, interval_seconds=2.0)

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = Thread(target=self._run, daemon=True)
        self._worker.start()
        self._ws.start()

    def stop(self) -> None:
        self._stop.set()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        self._ws.stop()

    def subscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def get_live_quotes(self, exchange: str = "NSE", symbol_query: str = "") -> list[MarketInstrument]:
        ex = (exchange or "NSE").upper()
        query = (symbol_query or "").strip().lower()
        rows = [item for (item_exchange, _), item in self._quotes.items() if item_exchange == ex]
        if not rows:
            rows = self._fallback_live_quotes(ex)
        if query:
            rows = [row for row in rows if query in row.symbol.lower() or query in row.company.lower()]
        return sorted(rows, key=lambda item: item.symbol)

    def get_quote(self, symbol: str, exchange: str = "NSE") -> MarketInstrument | None:
        found = self._quotes.get((exchange.upper(), symbol.upper()))
        if found is not None:
            return found
        fallback = {row.symbol: row for row in self._fallback_live_quotes(exchange.upper())}
        return fallback.get(symbol.upper())

    def get_market_depth(self, symbol: str, exchange: str = "NSE") -> MarketDepthSnapshot:
        key = f"depth:{exchange.upper()}:{symbol.upper()}"
        try:
            payload = self._broker_manager.get_market_depth(symbol, exchange=exchange)
            depth = MarketDepthSnapshot(
                symbol=str(payload.get("symbol", symbol)).upper(),
                exchange=str(payload.get("exchange", exchange)).upper(),
                bid=float(payload.get("bid", 0.0) or 0.0),
                ask=float(payload.get("ask", 0.0) or 0.0),
                spread=float(payload.get("spread", 0.0) or 0.0),
                buy_levels=[
                    MarketDepthLevel(
                        price=float(level.get("price", 0.0) or 0.0),
                        quantity=int(level.get("quantity", 0) or 0),
                        orders=int(level.get("orders", 0) or 0),
                    )
                    for level in list(payload.get("buy_levels", []))[:5]
                ],
                sell_levels=[
                    MarketDepthLevel(
                        price=float(level.get("price", 0.0) or 0.0),
                        quantity=int(level.get("quantity", 0) or 0),
                        orders=int(level.get("orders", 0) or 0),
                    )
                    for level in list(payload.get("sell_levels", []))[:5]
                ],
                timestamp=payload.get("timestamp", datetime.now(timezone.utc)),
            )
            self._cache.set(key, depth)
            return depth
        except BrokerConnectionError as exc:
            cached = self._cache.get(key)
            if cached is not None:
                self._reconnecting = True
                self._last_error = str(exc)
                return cached

            quote = self.get_quote(symbol, exchange)
            now = datetime.now(timezone.utc)
            if quote is None:
                return MarketDepthSnapshot(symbol=symbol.upper(), exchange=exchange.upper(), bid=0.0, ask=0.0, spread=0.0, buy_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)], sell_levels=[MarketDepthLevel(0.0, 0, 0) for _ in range(5)], timestamp=now)

            buy_levels = [MarketDepthLevel(price=max(0.0, quote.bid - i * 0.05), quantity=0, orders=0) for i in range(5)]
            sell_levels = [MarketDepthLevel(price=max(0.0, quote.ask + i * 0.05), quantity=0, orders=0) for i in range(5)]
            return MarketDepthSnapshot(symbol=quote.symbol, exchange=quote.exchange, bid=quote.bid, ask=quote.ask, spread=max(0.0, quote.ask - quote.bid), buy_levels=buy_levels, sell_levels=sell_levels, timestamp=now)

    def get_option_chain(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        normalized = (underlying or "NIFTY").upper()
        key = f"option:{normalized}:{expiry}"
        try:
            payload = self._broker_manager.get_option_chain(normalized, expiry=expiry)
            rows = [
                OptionChainRow(
                    strike_price=int(row.get("strike_price", 0) or 0),
                    ce_ltp=float(row.get("ce_ltp", 0.0) or 0.0),
                    ce_oi=int(row.get("ce_oi", 0) or 0),
                    pe_oi=int(row.get("pe_oi", 0) or 0),
                    pe_ltp=float(row.get("pe_ltp", 0.0) or 0.0),
                    iv=float(row.get("iv", 0.0) or 0.0),
                    pcr=float(row.get("pcr", 0.0) or 0.0),
                    ce_change_oi=int(row.get("ce_change_oi", 0) or 0),
                    pe_change_oi=int(row.get("pe_change_oi", 0) or 0),
                )
                for row in payload.get("rows", [])
            ]
            snapshot = OptionChainSnapshot(
                underlying=str(payload.get("underlying", normalized)).upper(),
                expiry=str(payload.get("expiry", expiry)),
                spot_price=float(payload.get("spot_price", 0.0) or 0.0),
                atm_strike=int(payload.get("atm_strike", 0) or 0),
                pcr=float(payload.get("pcr", 0.0) or 0.0),
                iv=float(payload.get("iv", 0.0) or 0.0),
                rows=rows,
                timestamp=payload.get("timestamp", datetime.now(timezone.utc)),
            )
            if snapshot.spot_price <= 0.0 or not snapshot.rows or snapshot.rows[0].strike_price <= 0:
                return self._fallback_option_chain(normalized, expiry)
            self._cache.set(key, snapshot)
            return snapshot
        except BrokerConnectionError as exc:
            cached = self._cache.get(key)
            if cached is not None:
                self._reconnecting = True
                self._last_error = str(exc)
                return cached
            self._reconnecting = True
            self._last_error = str(exc)
            return self._fallback_option_chain(normalized, expiry)

    def get_historical_candles(self, symbol: str, exchange: str, timeframe: str):
        key = f"history:{exchange.upper()}:{symbol.upper()}:{timeframe}"
        try:
            payload_rows = self._broker_manager.get_historical_data(symbol, exchange=exchange, timeframe=timeframe)
            candles = [
                HistoricalCandle(
                    timestamp=row.get("timestamp", datetime.now(timezone.utc)),
                    open=float(row.get("open", 0.0) or 0.0),
                    high=float(row.get("high", 0.0) or 0.0),
                    low=float(row.get("low", 0.0) or 0.0),
                    close=float(row.get("close", 0.0) or 0.0),
                    volume=int(row.get("volume", 0) or 0),
                )
                for row in payload_rows
            ]
            if not candles:
                candles = self._fallback_historical_candles(symbol)
            self._cache.set(key, candles)
            return candles
        except BrokerConnectionError as exc:
            cached = self._cache.get(key)
            if cached is not None:
                self._reconnecting = True
                self._last_error = str(exc)
                return cached
            self._reconnecting = True
            self._last_error = str(exc)
            return self._fallback_historical_candles(symbol)

    def _fallback_live_quotes(self, exchange: str) -> list[MarketInstrument]:
        now = datetime.now(timezone.utc)
        base_rows = [
            ("SBIN", "State Bank of India", 812.25, 1.45, 1220000),
            ("RELIANCE", "Reliance Industries", 2922.30, 0.82, 985000),
            ("TCS", "Tata Consultancy Services", 4165.40, -0.34, 610000),
            ("INFY", "Infosys", 1850.75, 0.61, 734000),
            ("HDFCBANK", "HDFC Bank", 1703.15, 0.95, 1410000),
            ("ICICIBANK", "ICICI Bank", 1234.80, 0.77, 1120000),
            ("ITC", "ITC Limited", 453.25, -0.18, 2100000),
            ("LT", "Larsen & Toubro", 3812.55, 0.43, 544000),
            ("AXISBANK", "Axis Bank", 1321.10, -0.11, 803000),
            ("BAJFINANCE", "Bajaj Finance", 7448.20, 1.16, 398000),
        ]
        rows: list[MarketInstrument] = []
        for symbol, company, ltp, chg_pct, volume in base_rows:
            close = ltp / (1 + (chg_pct / 100.0)) if chg_pct else ltp
            change = ltp - close
            rows.append(
                MarketInstrument(
                    symbol=symbol,
                    company=company,
                    sector="Unknown",
                    exchange=exchange,
                    ltp=ltp,
                    open=close,
                    high=max(ltp, close) + 4.0,
                    low=min(ltp, close) - 4.0,
                    previous_close=close,
                    change=change,
                    change_percent=chg_pct,
                    volume=volume,
                    bid=ltp - 0.05,
                    ask=ltp + 0.05,
                    timestamp=now,
                )
            )
        return rows

    def _fallback_option_chain(self, underlying: str, expiry: str) -> OptionChainSnapshot:
        now = datetime.now(timezone.utc)
        base_map = {
            "NIFTY": 25000,
            "BANKNIFTY": 57820,
            "FINNIFTY": 28110,
        }
        spot = float(base_map.get(underlying, 25000))
        if underlying == "BANKNIFTY":
            strikes = [57600, 57700, 57800, 57900, 58000]
        elif underlying == "FINNIFTY":
            strikes = [27900, 28000, 28100, 28200, 28300]
        else:
            strikes = [24600, 24700, 24800, 24900, 25000, 25100]
        rows: list[OptionChainRow] = []
        for strike in strikes:
            distance = abs(strike - spot)
            ce_oi = max(150, 1800 - int(distance * 2))
            pe_oi = max(140, 1700 - int(distance * 2.2))
            rows.append(
                OptionChainRow(
                    strike_price=strike,
                    ce_ltp=max(2.5, 180.0 - (distance * 0.45)),
                    ce_oi=ce_oi,
                    ce_change_oi=max(1, int(ce_oi * 0.02)),
                    pe_oi=pe_oi,
                    pe_change_oi=max(1, int(pe_oi * 0.02)),
                    pe_ltp=max(2.5, 175.0 - (distance * 0.4)),
                    iv=13.5,
                    pcr=(pe_oi / ce_oi) if ce_oi else 0.0,
                )
            )
        total_ce = sum(r.ce_oi for r in rows)
        total_pe = sum(r.pe_oi for r in rows)
        return OptionChainSnapshot(
            underlying=underlying,
            expiry=expiry,
            spot_price=spot,
            atm_strike=int(spot),
            pcr=(total_pe / total_ce) if total_ce else 0.0,
            iv=13.5,
            rows=rows,
            timestamp=now,
        )

    def _fallback_historical_candles(self, symbol: str) -> list[HistoricalCandle]:
        now = datetime.now(timezone.utc)
        candles: list[HistoricalCandle] = []
        base = 800.0 if symbol.upper() == "SBIN" else 1000.0
        for idx in range(140):
            ts = now - timedelta(minutes=(140 - idx) * 15)
            drift = idx * 0.22
            open_price = base + drift
            close_price = open_price + (0.4 if idx % 2 == 0 else -0.2)
            high = max(open_price, close_price) + 0.8
            low = min(open_price, close_price) - 0.8
            candles.append(
                HistoricalCandle(
                    timestamp=ts,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close_price,
                    volume=50000 + (idx * 120),
                )
            )
        return candles

    def get_portfolio_positions(self) -> list[PortfolioPosition]:
        key = "portfolio:positions"
        try:
            raw_positions = self._broker_manager.get_positions()
            rows = [
                PortfolioPosition(
                    symbol=str(item.get("symbol", "")).upper(),
                    company=str(item.get("company", item.get("symbol", ""))),
                    quantity=int(item.get("quantity", 0) or 0),
                    average_price=float(item.get("average_price", 0.0) or 0.0),
                    ltp=float(item.get("ltp", 0.0) or 0.0),
                    pnl_percent=float(item.get("pnl_percent", 0.0) or 0.0),
                )
                for item in raw_positions
            ]
            self._cache.set(key, rows)
            return rows
        except BrokerConnectionError as exc:
            cached = self._cache.get(key)
            if cached is not None:
                self._reconnecting = True
                self._last_error = str(exc)
                return cached
            return []

    def get_orders(self) -> list[OrderRecord]:
        key = "orders:all"
        try:
            raw_orders = self._broker_manager.get_order_book()
            rows = [
                OrderRecord(
                    order_id=str(item.get("order_id", "")),
                    symbol=str(item.get("symbol", "")).upper(),
                    side=str(item.get("side", "")),
                    quantity=int(item.get("quantity", 0) or 0),
                    price=float(item.get("price", 0.0) or 0.0),
                    status=str(item.get("status", "")),
                )
                for item in raw_orders
            ]
            self._cache.set(key, rows)
            return rows
        except BrokerConnectionError as exc:
            cached = self._cache.get(key)
            if cached is not None:
                self._reconnecting = True
                self._last_error = str(exc)
                return cached
            return []

    def reconnecting_message(self) -> str:
        return "Broker connection unavailable."

    def is_reconnecting(self) -> bool:
        return self._reconnecting or self._ws.state().reconnecting

    def last_error(self) -> str:
        return self._last_error

    def _run(self) -> None:
        while not self._stop.is_set():
            changed_symbols: list[str] = []
            try:
                if not self._broker_manager.is_logged_in():
                    self._broker_manager.login()
                for exchange in self.universe.exchanges:
                    rows = self._broker_manager.get_quotes(exchange=exchange, instrument_type="EQUITY")
                    for row in rows:
                        instrument = MarketInstrument(
                            symbol=str(row.get("symbol", "")).upper(),
                            company=str(row.get("company", row.get("symbol", ""))),
                            sector=str(row.get("sector", "Unknown")),
                            exchange=str(row.get("exchange", exchange)).upper(),
                            ltp=float(row.get("ltp", 0.0) or 0.0),
                            open=float(row.get("open", 0.0) or 0.0),
                            high=float(row.get("high", 0.0) or 0.0),
                            low=float(row.get("low", 0.0) or 0.0),
                            previous_close=float(row.get("close", 0.0) or 0.0),
                            change=float(row.get("change", 0.0) or 0.0),
                            change_percent=float(row.get("change_percent", 0.0) or 0.0),
                            volume=int(row.get("volume", 0) or 0),
                            bid=float(row.get("bid", 0.0) or 0.0),
                            ask=float(row.get("ask", 0.0) or 0.0),
                            timestamp=row.get("timestamp", datetime.now(timezone.utc)),
                        )
                        key = (instrument.exchange.upper(), instrument.symbol.upper())
                        previous = self._quotes.get(key)
                        self._quotes[key] = instrument
                        if previous is None or previous.ltp != instrument.ltp or previous.volume != instrument.volume:
                            changed_symbols.append(instrument.symbol)
                self._reconnecting = False
                self._last_error = ""
                self._emit(MarketDataEvent(MarketEventType.TICK, sorted(set(changed_symbols)), datetime.now(timezone.utc), "market tick"))
            except BrokerConnectionError as exc:
                self._reconnecting = True
                self._last_error = str(exc)
                self._emit(MarketDataEvent(MarketEventType.CONNECTION, [], datetime.now(timezone.utc), self.reconnecting_message()))
                app_logger.warning(f"Live market refresh failed: {exc}")
            sleep(self.refresh_interval_seconds)

    def _emit(self, event: MarketDataEvent) -> None:
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                app_logger.error(f"MarketDataService subscriber error: {exc}")


market_data_service = MarketDataService()
