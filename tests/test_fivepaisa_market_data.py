from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.market_data_service import MarketDataService


class _Session:
    def __init__(self) -> None:
        self.token = "token-1"
        self.client_code = "C123"

    def get_access_token(self) -> str:
        return self.token

    def require_valid_session(self):
        return self

    def clear(self) -> None:
        self.token = ""


class _Client:
    def __init__(self) -> None:
        self.reauthed = False
        self.auth_checked = 0

    def ensure_authenticated(self):
        self.auth_checked += 1
        return None

    def try_reauthenticate_from_env(self) -> bool:
        self.reauthed = True
        return True


def _mk_service() -> MarketDataService:
    service = MarketDataService(broker_client=_Client(), session_manager=_Session())
    return service


def test_get_quote_parses_live_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    def fake_request(method, path, body=None, query=None):
        return {
            "Data": [
                {
                    "Symbol": "SBIN",
                    "FullName": "State Bank of India",
                    "Exchange": "NSE",
                    "LastRate": 812.25,
                    "Open": 808.1,
                    "High": 816.0,
                    "Low": 804.7,
                    "Close": 805.0,
                    "Volume": 123456,
                    "BestBuyRate": 812.2,
                    "BestSellRate": 812.3,
                    "OpenInterest": 999,
                }
            ]
        }

    monkeypatch.setattr(service, "_request_json", fake_request)
    quote = service.get_quote("SBIN")

    assert quote["symbol"] == "SBIN"
    assert quote["ltp"] == 812.25
    assert quote["open"] == 808.1
    assert quote["high"] == 816.0
    assert quote["low"] == 804.7
    assert quote["volume"] == 123456
    assert quote["bid"] == 812.2
    assert quote["ask"] == 812.3
    assert quote["oi"] == 999


def test_quote_uses_cache_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    calls = {"count": 0}

    def fake_request(method, path, body=None, query=None):
        calls["count"] += 1
        return {"Data": [{"Symbol": "SBIN", "LastRate": 100, "Close": 100}]}

    monkeypatch.setattr(service, "_request_json", fake_request)

    first = service.get_quote("SBIN")
    second = service.get_quote("SBIN")

    assert first["ltp"] == second["ltp"]
    assert calls["count"] == 1


def test_quote_cache_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    calls = {"count": 0}

    def fake_request(method, path, body=None, query=None):
        calls["count"] += 1
        return {"Data": [{"Symbol": "SBIN", "LastRate": 100 + calls["count"], "Close": 100}]}

    monkeypatch.setattr(service, "_request_json", fake_request)

    first = service.get_quote("SBIN")
    key = "quote:SBIN"
    ts, value = service._cache[key]
    service._cache[key] = (ts - timedelta(seconds=10), value)
    second = service.get_quote("SBIN")

    assert first["ltp"] != second["ltp"]
    assert calls["count"] == 2


def test_request_json_retries_on_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    attempts = {"n": 0}

    from urllib.error import HTTPError
    from io import BytesIO

    def fake_urlopen(req, timeout=20):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise HTTPError(req.full_url, 401, "unauthorized", hdrs=None, fp=BytesIO(b""))

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"Data":[{"Symbol":"SBIN","LastRate":100,"Close":100}]}'

        return _Resp()

    monkeypatch.setattr("src.brokers.fivepaisa.market_data_service.urlopen", fake_urlopen)
    out = service._request_json("GET", "/x")
    assert out["Data"][0]["Symbol"] == "SBIN"
    assert attempts["n"] == 2


def test_get_historical_candles_maps_candles(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    def fake_request(method, path, body=None, query=None):
        return {
            "Data": [
                {
                    "Time": "2026-07-11T09:15:00+00:00",
                    "Open": 100,
                    "High": 102,
                    "Low": 99,
                    "Close": 101,
                    "Volume": 200,
                }
            ]
        }

    monkeypatch.setattr(service, "_request_json", fake_request)
    candles = service.get_historical_candles("SBIN", "15 Minute", "2026-07-01", "2026-07-11")
    assert len(candles) == 1
    assert candles[0]["close"] == 101


def test_quote_uses_official_marketfeed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    service._cache_ttl_seconds = 0
    captured = {}

    def fake_request(method, path, body=None, query=None):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return {"Data": [{"Symbol": "HDFCBANK", "LastRate": 1600, "Close": 1590}]}

    monkeypatch.setattr(service, "_request_json", fake_request)

    quote = service.get_quote("HDFCBANK")

    assert quote["symbol"] == "HDFCBANK"
    assert captured["method"] == "POST"
    assert captured["path"].endswith("/V1/MarketFeed")
    assert captured["body"]["body"]["MarketFeedData"][0]["Exch"] == "N"
    assert captured["body"]["body"]["MarketFeedData"][0]["ExchType"] == "C"
    assert captured["body"]["body"]["MarketFeedData"][0]["ScripData"] == "HDFCBANK_EQ"


def test_get_quotes_batches_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    def fake_request(method, path, body=None, query=None):
        rows = body["body"]["MarketFeedData"]
        assert len(rows) == 2
        return {
            "Data": [
                {"Symbol": "SBIN", "LastRate": 800, "Close": 790},
                {"Symbol": "HDFCBANK", "LastRate": 1600, "Close": 1590},
            ]
        }

    monkeypatch.setattr(service, "_request_json", fake_request)
    quotes = service.get_quotes(["SBIN", "HDFCBANK"])
    assert [row["symbol"] for row in quotes] == ["SBIN", "HDFCBANK"]


def test_get_market_depth_returns_normalized_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    monkeypatch.setattr(
        service,
        "get_quote",
        lambda symbol: {
            "symbol": "SBIN",
            "exchange": "NSE",
            "ltp": 812.0,
            "bid": 811.9,
            "ask": 812.1,
            "timestamp": datetime.now(timezone.utc),
        },
    )
    depth = service.get_market_depth("SBIN")
    assert depth["symbol"] == "SBIN"
    assert depth["spread"] == pytest.approx(0.2)
    assert len(depth["buy_levels"]) == 5
    assert len(depth["sell_levels"]) == 5


def test_get_option_chain_normalizes_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    def fake_request(method, path, body=None, query=None):
        return {
            "Data": {
                "SpotPrice": 24500,
                "Options": [
                    {
                        "StrikePrice": 24400,
                        "IV": 13.2,
                        "CE": {"LTP": 210.5, "OI": 1000, "ChangeInOI": 50},
                        "PE": {"LTP": 120.0, "OI": 900, "ChangeInOI": 10},
                    }
                ],
            }
        }

    monkeypatch.setattr(service, "_request_json", fake_request)
    chain = service.get_option_chain("NIFTY")
    assert chain["underlying"] == "NIFTY"
    assert chain["atm_strike"] == 24400
    assert chain["rows"][0]["ce_oi"] == 1000


def test_get_indices_uses_configured_index_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    service._index_symbols = ["NIFTY", "BANKNIFTY"]

    def fake_request(method, path, body=None, query=None):
        rows = body["body"]["MarketFeedData"]
        assert rows[0]["ExchType"] == "I"
        return {
            "Data": [
                {"Symbol": "NIFTY", "LastRate": 24800, "Close": 24750},
                {"Symbol": "BANKNIFTY", "LastRate": 53200, "Close": 53100},
            ]
        }

    monkeypatch.setattr(service, "_request_json", fake_request)
    rows = service.get_indices()
    assert [item["symbol"] for item in rows] == ["NIFTY", "BANKNIFTY"]


def test_get_watchlist_quotes_uses_default_watchlist(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    service._watch_symbols = ["SBIN", "RELIANCE"]
    monkeypatch.setattr(service, "get_quotes", lambda symbols: [{"symbol": s, "ltp": 1.0} for s in symbols])
    rows = service.get_watchlist_quotes()
    assert [item["symbol"] for item in rows] == ["SBIN", "RELIANCE"]


def test_request_json_retries_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()
    service._retry_attempts = 3
    attempts = {"n": 0}

    def fake_urlopen(req, timeout=20):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("request timed out")

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"Data":[{"Symbol":"SBIN","LastRate":101,"Close":100}]}'

        return _Resp()

    monkeypatch.setattr("src.brokers.fivepaisa.market_data_service.urlopen", fake_urlopen)
    out = service._request_json("GET", "/x")
    assert out["Data"][0]["LastRate"] == 101
    assert attempts["n"] == 3


def test_request_json_decodes_error_reason() -> None:
    reason = MarketDataService._decode_error_reason('{"body":{"Message":"Invalid ScripData"}}')
    assert reason == "Invalid ScripData"


def test_request_json_raises_broker_error_on_api_message(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _mk_service()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"body":{"Message":"Invalid Token"}}'

    monkeypatch.setattr("src.brokers.fivepaisa.market_data_service.urlopen", lambda req, timeout=20: _Resp())

    with pytest.raises(BrokerConnectionError):
        service._request_json("GET", "/x")
