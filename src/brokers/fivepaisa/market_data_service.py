from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.session_manager import FivePaisaSessionManager
from src.core.logger import app_logger


class MarketDataService:
    """Centralized 5paisa market-data service.

    All market APIs must flow through this service so request headers,
    retry/timeouts, and error handling remain consistent.
    """

    def __init__(
        self,
        broker_client: FivePaisaBrokerClient | None = None,
        session_manager: FivePaisaSessionManager | None = None,
    ) -> None:
        self._broker_client = broker_client or FivePaisaBrokerClient()
        self._session_manager = session_manager or FivePaisaSessionManager()

        self._base_url = os.getenv("FIVEPAISA_XSTREAM_BASE_URL", "https://Openapi.5paisa.com").rstrip("/")
        self._quote_path = os.getenv("FIVEPAISA_QUOTE_PATH", "/VendorsAPI/Service1.svc/V1/MarketFeed")
        self._market_depth_path = os.getenv("FIVEPAISA_MARKET_DEPTH_PATH", self._quote_path)
        self._historical_path = os.getenv("FIVEPAISA_HISTORICAL_PATH", "/VendorsAPI/Service1.svc/HistoricalData")
        self._option_chain_path = os.getenv("FIVEPAISA_OPTION_CHAIN_PATH", "/VendorsAPI/Service1.svc/OptionChain")

        self._api_key = os.getenv("FIVEPAISA_API_KEY", "").strip()
        self._cache_ttl_seconds = float(os.getenv("FIVEPAISA_MARKET_CACHE_SECONDS", "4") or "4")
        self._timeout_seconds = float(os.getenv("FIVEPAISA_MARKET_TIMEOUT_SECONDS", "20") or "20")
        self._retry_attempts = int(os.getenv("FIVEPAISA_MARKET_RETRY_ATTEMPTS", "3") or "3")
        self._watch_symbols = self._parse_symbol_list(
            os.getenv("FIVEPAISA_WATCH_SYMBOLS", "SBIN,RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK")
        )
        self._index_symbols = self._parse_symbol_list(
            os.getenv("FIVEPAISA_INDEX_SYMBOLS", "NIFTY,BANKNIFTY,FINNIFTY,SENSEX")
        )

        self._cache: dict[str, tuple[datetime, Any]] = {}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = self._normalize_symbol(symbol)
        cache_key = f"quote:{normalized_symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        payload_body = self._market_feed_payload([normalized_symbol], exchange_type="C")
        payload = self._request_json(
            "POST",
            self._quote_path,
            body={"head": self._request_head(), "body": payload_body},
        )
        quotes = self._normalize_quotes(payload, exchange="NSE")
        quote = quotes[0] if quotes else self._empty_quote(normalized_symbol, "NSE")

        app_logger.info(f"Quote received for {normalized_symbol}")
        self._set_cache(cache_key, quote)
        return quote

    def get_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        normalized_symbols = [self._normalize_symbol(symbol) for symbol in symbols if str(symbol or "").strip()]
        if not normalized_symbols:
            return []

        uncached: list[str] = []
        out: list[dict[str, Any]] = []
        for symbol in normalized_symbols:
            cached = self._get_cached(f"quote:{symbol}")
            if cached is None:
                uncached.append(symbol)
            else:
                out.append(cached)

        if uncached:
            payload_body = self._market_feed_payload(uncached, exchange_type="C")
            payload = self._request_json(
                "POST",
                self._quote_path,
                body={"head": self._request_head(), "body": payload_body},
            )
            fresh = self._normalize_quotes(payload, exchange="NSE")
            by_symbol = {row["symbol"]: row for row in fresh}
            for symbol in uncached:
                quote = by_symbol.get(symbol, self._empty_quote(symbol, "NSE"))
                self._set_cache(f"quote:{symbol}", quote)
                out.append(quote)

        ordered = {row["symbol"]: row for row in out}
        return [ordered.get(symbol, self._empty_quote(symbol, "NSE")) for symbol in normalized_symbols]

    def get_market_depth(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = self._normalize_symbol(symbol)
        cache_key = f"depth:{normalized_symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        quote = self.get_quote(normalized_symbol)
        bid = float(quote.get("bid", quote.get("ltp", 0.0)) or 0.0)
        ask = float(quote.get("ask", quote.get("ltp", 0.0)) or 0.0)

        depth = {
            "symbol": quote.get("symbol", normalized_symbol),
            "exchange": quote.get("exchange", "NSE"),
            "bid": bid,
            "ask": ask,
            "spread": max(0.0, ask - bid),
            "buy_levels": [
                {"price": max(0.0, bid - i * 0.05), "quantity": 0, "orders": 0} for i in range(5)
            ],
            "sell_levels": [
                {"price": max(0.0, ask + i * 0.05), "quantity": 0, "orders": 0} for i in range(5)
            ],
            "timestamp": datetime.now(timezone.utc),
        }
        self._set_cache(cache_key, depth)
        return depth

    def get_ohlc(self, symbol: str, timeframe: str, exchange: str = "NSE") -> dict[str, Any]:
        quote = self.get_quote(symbol)
        return {
            "symbol": quote["symbol"],
            "exchange": quote["exchange"],
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "ltp": quote["ltp"],
            "volume": quote["volume"],
            "bid": quote["bid"],
            "ask": quote["ask"],
            "oi": quote.get("oi", 0),
            "timestamp": quote["timestamp"],
        }

    def get_option_chain(self, symbol: str, expiry: str | None = None) -> dict[str, Any]:
        normalized_symbol = self._normalize_symbol(symbol)
        normalized_expiry = str(expiry or "").strip()
        cache_key = f"option_chain:{normalized_symbol}:{normalized_expiry}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        query: dict[str, Any] = {"Symbol": normalized_symbol}
        if normalized_expiry:
            query["Expiry"] = normalized_expiry

        payload = self._request_json("GET", self._option_chain_path, query=query)

        root = self._extract_dict(payload)
        rows_raw = root.get("Options", root.get("Data", []))
        rows: list[dict[str, Any]] = []
        for item in rows_raw if isinstance(rows_raw, list) else []:
            strike = int(item.get("StrikePrice", 0) or 0)
            ce = item.get("CE", {}) if isinstance(item.get("CE", {}), dict) else {}
            pe = item.get("PE", {}) if isinstance(item.get("PE", {}), dict) else {}
            ce_oi = int(ce.get("OI", 0) or 0)
            pe_oi = int(pe.get("OI", 0) or 0)
            rows.append(
                {
                    "strike_price": strike,
                    "ce_ltp": float(ce.get("LTP", 0.0) or 0.0),
                    "ce_oi": ce_oi,
                    "ce_change_oi": int(ce.get("ChangeInOI", 0) or 0),
                    "pe_oi": pe_oi,
                    "pe_change_oi": int(pe.get("ChangeInOI", 0) or 0),
                    "pe_ltp": float(pe.get("LTP", 0.0) or 0.0),
                    "iv": float(item.get("IV", 0.0) or 0.0),
                    "pcr": float(pe_oi / ce_oi) if ce_oi else 0.0,
                }
            )

        rows.sort(key=lambda row: row["strike_price"])
        spot_price = float(root.get("SpotPrice", root.get("LTP", 0.0)) or 0.0)
        atm = min((row["strike_price"] for row in rows), key=lambda strike: abs(strike - spot_price), default=0)
        total_ce = sum(row["ce_oi"] for row in rows)
        total_pe = sum(row["pe_oi"] for row in rows)

        response = {
            "underlying": normalized_symbol,
            "expiry": str(root.get("Expiry", normalized_expiry)),
            "spot_price": spot_price,
            "atm_strike": atm,
            "pcr": (total_pe / total_ce) if total_ce else 0.0,
            "iv": float(root.get("IV", 0.0) or 0.0),
            "rows": rows,
            "timestamp": datetime.now(timezone.utc),
        }
        self._set_cache(cache_key, response)
        return response

    def get_historical_candles(
        self,
        symbol: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> list[dict[str, Any]]:
        normalized_symbol = self._normalize_symbol(symbol)
        normalized_interval = str(interval or "15 Minute").strip() or "15 Minute"
        start = str(from_date or "").strip()
        end = str(to_date or "").strip()

        if not start or not end:
            now = datetime.now(timezone.utc)
            default_start = now - timedelta(days=30)
            start = start or default_start.strftime("%Y-%m-%d")
            end = end or now.strftime("%Y-%m-%d")

        cache_key = f"historical:{normalized_symbol}:{normalized_interval}:{start}:{end}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        payload = self._request_json(
            "GET",
            self._historical_path,
            query={
                "Exchange": "NSE",
                "ExchangeType": "C",
                "Symbol": normalized_symbol,
                "TimeFrame": normalized_interval,
                "FromDate": start,
                "ToDate": end,
            },
        )

        rows = self._extract_list(payload)
        candles: list[dict[str, Any]] = []
        for row in rows:
            candles.append(
                {
                    "timestamp": self._parse_datetime(str(row.get("Time", "") or row.get("Timestamp", ""))),
                    "open": float(row.get("Open", 0.0) or 0.0),
                    "high": float(row.get("High", 0.0) or 0.0),
                    "low": float(row.get("Low", 0.0) or 0.0),
                    "close": float(row.get("Close", 0.0) or 0.0),
                    "volume": int(row.get("Volume", 0) or 0),
                }
            )

        self._set_cache(cache_key, candles)
        return candles

    def get_indices(self) -> list[dict[str, Any]]:
        if not self._index_symbols:
            return []

        payload_body = self._market_feed_payload(self._index_symbols, exchange_type="I")
        payload = self._request_json(
            "POST",
            self._quote_path,
            body={"head": self._request_head(), "body": payload_body},
        )

        rows = self._normalize_quotes(payload, exchange="NSE")
        by_symbol = {row["symbol"]: row for row in rows}
        return [by_symbol.get(symbol, self._empty_quote(symbol, "NSE")) for symbol in self._index_symbols]

    def get_watchlist_quotes(self) -> list[dict[str, Any]]:
        return self.get_quotes(self._watch_symbols)

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._broker_client.ensure_authenticated()

        url = f"{self._base_url}{path}"
        if query:
            sanitized_query = {key: str(value) for key, value in query.items() if value is not None}
            url = f"{url}?{urlencode(sanitized_query)}"

        request_body = None
        if method.upper() in {"POST", "PUT", "PATCH"}:
            request_body = json.dumps(body or {}).encode("utf-8")

        last_error: Exception | None = None

        for attempt in range(1, max(1, self._retry_attempts) + 1):
            try:
                request = Request(
                    url=url,
                    data=request_body,
                    method=method.upper(),
                    headers=self._build_headers(),
                )

                with urlopen(request, timeout=max(1.0, self._timeout_seconds)) as response:
                    response_text = response.read().decode("utf-8")

                parsed = json.loads(response_text)
                if not isinstance(parsed, dict):
                    raise BrokerConnectionError("Broker connection unavailable: malformed response")

                reason = self._decode_error_reason_from_json(parsed)
                if reason:
                    raise BrokerConnectionError(f"Broker API error: {reason}")

                return parsed
            except HTTPError as exc:
                error_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                app_logger.warning(f"5paisa API HTTP error {exc.code} on attempt {attempt}: {error_text}")
                if exc.code in {401, 403}:
                    self._session_manager.clear()
                    if self._broker_client.try_reauthenticate_from_env():
                        continue
                    raise BrokerConnectionError("Broker API error: unauthorized") from exc
                if exc.code in {408, 429, 500, 502, 503, 504} and attempt < self._retry_attempts:
                    sleep(0.2 * attempt)
                    continue
                reason = self._decode_error_reason(error_text) or f"HTTP {exc.code}"
                raise BrokerConnectionError(f"Broker API error: {reason}") from exc
            except (TimeoutError, URLError) as exc:
                last_error = exc
                app_logger.warning(f"5paisa request timeout/network error on attempt {attempt}: {exc}")
                if attempt < self._retry_attempts:
                    sleep(0.2 * attempt)
                    continue
                raise BrokerConnectionError(f"Broker connection unavailable: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise BrokerConnectionError("Broker connection unavailable: invalid JSON response") from exc
            except BrokerConnectionError:
                raise
            except Exception as exc:
                last_error = exc
                app_logger.error(f"Unexpected 5paisa market-data error on attempt {attempt}: {exc}")
                if attempt < self._retry_attempts:
                    sleep(0.2 * attempt)
                    continue
                raise BrokerConnectionError(f"Broker connection unavailable: {exc}") from exc

        raise BrokerConnectionError(f"Broker connection unavailable: {last_error}")

    def _build_headers(self) -> dict[str, str]:
        token = self._session_manager.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["x-clientcode"] = self._api_key
        return headers

    def _request_head(self) -> dict[str, Any]:
        head: dict[str, Any] = {}
        if self._api_key:
            head["key"] = self._api_key
        return head

    def _market_feed_payload(self, symbols: list[str], exchange_type: str) -> dict[str, Any]:
        session = self._session_manager.require_valid_session()
        feed_rows: list[dict[str, Any]] = []
        for symbol in symbols:
            normalized = self._normalize_symbol(symbol)
            feed_rows.append(
                {
                    "Exch": "N",
                    "ExchType": exchange_type,
                    "ScripData": self._to_scrip_data(normalized, exchange_type),
                }
            )

        return {
            "MarketFeedData": feed_rows,
            "ClientLoginType": 0,
            "LastRequestTime": f"/Date({int(datetime.now(timezone.utc).timestamp())})/",
            "RefreshRate": "H",
            "ClientCode": session.client_code,
        }

    @staticmethod
    def _to_scrip_data(symbol: str, exchange_type: str) -> str:
        if exchange_type == "C":
            if symbol.endswith("_EQ"):
                return symbol
            return f"{symbol}_EQ"
        return symbol

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return str(symbol or "").strip().upper()

    @staticmethod
    def _parse_symbol_list(raw_value: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for chunk in str(raw_value or "").split(","):
            symbol = chunk.strip().upper()
            if not symbol or symbol in seen:
                continue
            out.append(symbol)
            seen.add(symbol)
        return out

    @staticmethod
    def _decode_error_reason(error_text: str) -> str:
        text = (error_text or "").strip()
        if not text:
            return ""
        try:
            parsed = json.loads(text)
        except Exception:
            return text
        if not isinstance(parsed, dict):
            return text
        return MarketDataService._decode_error_reason_from_json(parsed) or text

    @staticmethod
    def _decode_error_reason_from_json(payload: dict[str, Any]) -> str:
        body = payload.get("body", payload)
        if isinstance(body, dict):
            for key in ("Message", "message", "Status", "Error", "ErrorMessage", "Reason"):
                value = body.get(key)
                if isinstance(value, str):
                    cleaned = value.strip()
                    if cleaned and cleaned.lower() not in {"success", "ok", "0", "true"}:
                        return cleaned
        for key in ("Message", "message", "Status", "Error", "ErrorMessage", "Reason"):
            value = payload.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned and cleaned.lower() not in {"success", "ok", "0", "true"}:
                    return cleaned
        return ""

    @staticmethod
    def _extract_dict(payload: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload.get("body"), dict):
            return payload["body"]
        if isinstance(payload.get("Data"), dict):
            return payload["Data"]
        return payload

    @staticmethod
    def _extract_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload.get("body"), dict):
            body_data = payload["body"].get("Data")
            if isinstance(body_data, list):
                return [item for item in body_data if isinstance(item, dict)]
        if isinstance(payload.get("body"), list):
            return [item for item in payload["body"] if isinstance(item, dict)]
        if isinstance(payload.get("Data"), list):
            return [item for item in payload["Data"] if isinstance(item, dict)]
        if isinstance(payload.get("Candles"), list):
            return [item for item in payload["Candles"] if isinstance(item, dict)]
        return []

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        text = (value or "").strip()
        if not text:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)

    def _normalize_quotes(self, payload: dict[str, Any], exchange: str) -> list[dict[str, Any]]:
        rows = self._extract_list(payload)
        if not rows:
            root = self._extract_dict(payload)
            rows = [root] if isinstance(root, dict) and root else []

        out: list[dict[str, Any]] = []
        for item in rows:
            symbol = str(item.get("Symbol", "") or "").upper()
            out.append(
                {
                    "symbol": symbol,
                    "company": str(item.get("FullName", item.get("CompanyName", symbol))),
                    "sector": str(item.get("Sector", "Unknown")),
                    "exchange": str(item.get("Exchange", item.get("Exch", exchange))).upper(),
                    "ltp": float(item.get("LastRate", item.get("LTP", 0.0)) or 0.0),
                    "open": float(item.get("Open", 0.0) or 0.0),
                    "high": float(item.get("High", 0.0) or 0.0),
                    "low": float(item.get("Low", 0.0) or 0.0),
                    "close": float(item.get("Close", item.get("PClose", item.get("PreviousClose", 0.0))) or 0.0),
                    "change": float(item.get("Chg", 0.0) or 0.0),
                    "change_percent": float(item.get("ChgPcnt", 0.0) or 0.0),
                    "volume": int(item.get("Volume", item.get("TotalQty", item.get("Vol", 0))) or 0),
                    "bid": float(item.get("BestBuyRate", item.get("Bid", 0.0)) or 0.0),
                    "ask": float(item.get("BestSellRate", item.get("Ask", 0.0)) or 0.0),
                    "oi": int(item.get("OpenInterest", item.get("OI", 0)) or 0),
                    "timestamp": datetime.now(timezone.utc),
                }
            )

        normalized: list[dict[str, Any]] = []
        for quote in out:
            close = float(quote.get("close", 0.0) or 0.0)
            ltp = float(quote.get("ltp", 0.0) or 0.0)
            change = quote["change"] if quote["change"] else ltp - close
            change_percent = quote["change_percent"] if quote["change_percent"] else ((change / close) * 100 if close else 0.0)
            quote["change"] = float(change)
            quote["change_percent"] = float(change_percent)
            normalized.append(quote)

        return normalized

    def _empty_quote(self, symbol: str, exchange: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "symbol": symbol,
            "company": symbol,
            "sector": "Unknown",
            "exchange": exchange,
            "ltp": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "volume": 0,
            "bid": 0.0,
            "ask": 0.0,
            "oi": 0,
            "timestamp": now,
        }

    def _get_cached(self, key: str):
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, value = entry
        if (datetime.now(timezone.utc) - ts).total_seconds() > self._cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (datetime.now(timezone.utc), value)
