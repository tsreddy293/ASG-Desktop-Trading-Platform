from __future__ import annotations

import inspect
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from types import FrameType
from typing import Any

from src.app import create_app
from src.brokers import broker_manager
from src.market.websocket_client import WebSocketClient
from src.marketdata.engine import MarketDataEngine
from src.services.market_data_service import MarketDataService, market_data_service
from src.services.websocket_service import WebSocketService
from src.ui.main_window import MainWindow
from src.ui.option_chain_page import OptionChainPage


ROOT = os.path.normcase(os.path.abspath("d:/Projects/ASG")).replace("\\", "/")

trace_active = False
stop_triggered = False
stop_reason: dict[str, Any] | None = None

call_seq = 0
frame_to_call_id: dict[int, int] = {}
records: list[dict[str, Any]] = []

state_flags = {
    "WebSocketService.started": False,
    "WebSocketClient.connected": False,
    "MarketDataEngine.running": False,
    "MarketDataService.running": False,
    "SubscriptionManager.started": False,
    "LiveMarket.started": False,
    "OptionChain.started": False,
}

orig_ws_service_start = WebSocketService.start
orig_ws_client_start = WebSocketClient.start
orig_mde_start = MarketDataEngine.start
orig_mds_start = MarketDataService.start
orig_mds_subscribe = MarketDataService.subscribe
orig_option_chain_init = OptionChainPage.__init__


TARGET_MILESTONES = {
    "WebSocket client starts",
    "MarketDataEngine starts",
    "MarketDataService starts",
    "Live Market subscription starts",
    "Option Chain initialization starts",
    "First exception occurs",
}


def _in_workspace(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path)).replace("\\", "/")
    return p.startswith(ROOT + "/")


def _mark_stop(kind: str, file: str, line: int, function: str) -> None:
    global stop_triggered, stop_reason
    if stop_triggered:
        return
    stop_triggered = True
    stop_reason = {
        "kind": kind,
        "file": file,
        "line": line,
        "function": function,
    }


def _new_record(frame: FrameType, call_id: int) -> dict[str, Any]:
    return {
        "call_id": call_id,
        "file": frame.f_code.co_filename,
        "line": frame.f_code.co_firstlineno,
        "function_name": frame.f_code.co_name,
        "entered": True,
        "exited": False,
        "exception": None,
    }


def _profile(frame: FrameType, event: str, arg: Any):
    global call_seq

    if not trace_active:
        return _profile

    filename = frame.f_code.co_filename
    if not _in_workspace(filename):
        return _profile

    if stop_triggered:
        return _profile

    fid = id(frame)

    if event == "call":
        call_seq += 1
        frame_to_call_id[fid] = call_seq
        records.append(_new_record(frame, call_seq))
        return _profile

    if event == "return":
        call_id = frame_to_call_id.get(fid)
        if call_id is not None:
            for row in reversed(records):
                if row["call_id"] == call_id:
                    row["exited"] = True
                    break
        return _profile

    if event == "exception":
        call_id = frame_to_call_id.get(fid)
        exc_type, exc, _tb = arg
        exc_payload = {
            "type": getattr(exc_type, "__name__", str(exc_type)),
            "message": str(exc),
        }
        if call_id is not None:
            for row in reversed(records):
                if row["call_id"] == call_id and row["exception"] is None:
                    row["exception"] = exc_payload
                    break

        stack = inspect.stack(context=0)
        caller = stack[0]
        _mark_stop(
            "First exception occurs",
            file=frame.f_code.co_filename,
            line=frame.f_lineno,
            function=frame.f_code.co_name,
        )
        return _profile

    return _profile


def _wraps() -> None:
    def ws_service_start(self, *args, **kwargs):
        state_flags["WebSocketService.started"] = True
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("WebSocket client starts", fr.f_code.co_filename, fr.f_lineno, "WebSocketService.start")
        return orig_ws_service_start(self, *args, **kwargs)

    def ws_client_start(self, *args, **kwargs):
        out = orig_ws_client_start(self, *args, **kwargs)
        try:
            state_flags["WebSocketClient.connected"] = bool(self.is_connected())
        except Exception:
            state_flags["WebSocketClient.connected"] = False
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("WebSocket client starts", fr.f_code.co_filename, fr.f_lineno, "WebSocketClient.start")
        return out

    def mde_start(self, *args, **kwargs):
        out = orig_mde_start(self, *args, **kwargs)
        try:
            state_flags["MarketDataEngine.running"] = bool(getattr(self, "_worker", None) and self._worker.is_alive())
        except Exception:
            state_flags["MarketDataEngine.running"] = False
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("MarketDataEngine starts", fr.f_code.co_filename, fr.f_lineno, "MarketDataEngine.start")
        return out

    def mds_start(self, *args, **kwargs):
        out = orig_mds_start(self, *args, **kwargs)
        try:
            state_flags["MarketDataService.running"] = bool(getattr(self, "_worker", None) and self._worker.is_alive())
        except Exception:
            state_flags["MarketDataService.running"] = False
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("MarketDataService starts", fr.f_code.co_filename, fr.f_lineno, "MarketDataService.start")
        return out

    def mds_subscribe(self, *args, **kwargs):
        state_flags["SubscriptionManager.started"] = True
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("Live Market subscription starts", fr.f_code.co_filename, fr.f_lineno, "MarketDataService.subscribe")
        return orig_mds_subscribe(self, *args, **kwargs)

    def option_chain_init(self, *args, **kwargs):
        state_flags["OptionChain.started"] = True
        if trace_active:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("Option Chain initialization starts", fr.f_code.co_filename, fr.f_lineno, "OptionChainPage.__init__")
        return orig_option_chain_init(self, *args, **kwargs)

    WebSocketService.start = ws_service_start
    WebSocketClient.start = ws_client_start
    MarketDataEngine.start = mde_start
    MarketDataService.start = mds_start
    MarketDataService.subscribe = mds_subscribe
    OptionChainPage.__init__ = option_chain_init


def _compute_live_market_started(app_obj: Any) -> bool:
    try:
        window = getattr(app_obj, "window", None)
        if window is None:
            return False
        page = getattr(window, "market_workspace_page", None) or getattr(window, "market_watch_page", None)
        if page is None:
            return False
        return True
    except Exception:
        return False


def main() -> None:
    global trace_active

    _wraps()
    sys.setprofile(_profile)

    app = create_app()

    connect_ok = False
    connect_bypassed = False
    connect_exc = None
    try:
        broker_manager.connect()
        connect_ok = True
    except Exception as exc:
        connect_exc = exc
        # Trace-only bypass: user requested startup tracing after connect success.
        connect_ok = True
        connect_bypassed = True

    if not connect_ok:
        output = {
            "connect_success": False,
            "connect_bypassed": False,
            "connect_exception": {
                "type": type(connect_exc).__name__ if connect_exc else None,
                "message": str(connect_exc) if connect_exc else None,
            },
            "stop_reason": "BrokerManager.connect failed",
            "records": [],
            "states": state_flags,
        }
        print(json.dumps(output, indent=2))
        return

    trace_active = True

    startup_exc = None
    try:
        app.window = MainWindow(app.app)
        state_flags["LiveMarket.started"] = _compute_live_market_started(app)
        if not stop_triggered:
            app.market_data_controller.start()
            state_flags["MarketDataService.running"] = bool(getattr(market_data_service, "_worker", None) and market_data_service._worker.is_alive())
    except Exception as exc:
        startup_exc = exc
        if not stop_triggered:
            tb = traceback.extract_tb(exc.__traceback__)
            if tb:
                last = tb[-1]
                _mark_stop("First exception occurs", last.filename, last.lineno, last.name)

    output = {
        "connect_success": True,
        "connect_bypassed": connect_bypassed,
        "connect_exception": {
            "type": type(connect_exc).__name__,
            "message": str(connect_exc),
        }
        if connect_exc
        else None,
        "stop_reason": stop_reason,
        "first_runtime_exception": {
            "type": type(startup_exc).__name__,
            "message": str(startup_exc),
        }
        if startup_exc
        else None,
        "records": records,
        "states": state_flags,
        "milestones": sorted(TARGET_MILESTONES),
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
