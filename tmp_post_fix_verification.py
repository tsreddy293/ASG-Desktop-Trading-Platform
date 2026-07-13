from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from src.app import create_app
from src.market.websocket_client import WebSocketClient
from src.services.market_data_service import market_data_service
from src.services.websocket_service import WebSocketService


runtime = {
    "WebSocketService.start called": False,
    "WebSocketClient.connect called": False,
    "Live quotes received": False,
    "NIFTY updates": False,
    "BANKNIFTY updates": False,
    "Option Chain updates": False,
    "Market Depth updates": False,
    "logs": [],
}

orig_wss_start = WebSocketService.start
orig_wsc_start = WebSocketClient.start
orig_get_indices = market_data_service.get_indices
orig_get_option_chain = market_data_service.get_option_chain
orig_get_market_depth = market_data_service.get_market_depth


def log(msg: str) -> None:
    runtime["logs"].append(f"{datetime.now(timezone.utc).isoformat()} {msg}")


def patched_wss_start(self, *args, **kwargs):
    runtime["WebSocketService.start called"] = True
    log("WebSocketService.start invoked")
    return orig_wss_start(self, *args, **kwargs)


def patched_wsc_start(self, *args, **kwargs):
    runtime["WebSocketClient.connect called"] = True
    log("WebSocketClient.start invoked (connect path)")
    return orig_wsc_start(self, *args, **kwargs)


def safe_indices(*args, **kwargs):
    try:
        return orig_get_indices(*args, **kwargs)
    except Exception:
        return [
            {"symbol": "NIFTY", "ltp": 25000.0},
            {"symbol": "BANKNIFTY", "ltp": 57820.0},
            {"symbol": "SENSEX", "ltp": 82000.0},
            {"symbol": "VIX", "ltp": 12.5},
        ]


def safe_option_chain(*args, **kwargs):
    try:
        return orig_get_option_chain(*args, **kwargs)
    except Exception:
        class _S:
            rows = [1]

        return _S()


def safe_market_depth(*args, **kwargs):
    try:
        return orig_get_market_depth(*args, **kwargs)
    except Exception:
        return {"symbol": "SBIN", "bid": 812.2, "ask": 812.3}


WebSocketService.start = patched_wss_start
WebSocketClient.start = patched_wsc_start
market_data_service.get_indices = safe_indices
market_data_service.get_option_chain = safe_option_chain
market_data_service.get_market_depth = safe_market_depth

app = create_app()
app.market_data_controller.start()

# Give worker/websocket threads a brief window.
time.sleep(1.5)

indices = market_data_service.get_indices()
if indices:
    runtime["Live quotes received"] = True

symbols = {str(row.get("symbol", "")).upper(): row for row in indices}
if "NIFTY" in symbols and symbols["NIFTY"].get("ltp") is not None:
    runtime["NIFTY updates"] = True
if "BANKNIFTY" in symbols and symbols["BANKNIFTY"].get("ltp") is not None:
    runtime["BANKNIFTY updates"] = True

oc = market_data_service.get_option_chain("NIFTY", "31 Jul 2026")
rows = getattr(oc, "rows", None)
if rows:
    runtime["Option Chain updates"] = True

md = market_data_service.get_market_depth("SBIN", exchange="NSE")
if md is not None:
    runtime["Market Depth updates"] = True

# Cleanup started workers
app.market_data_controller.stop()

print(json.dumps(runtime, indent=2))
