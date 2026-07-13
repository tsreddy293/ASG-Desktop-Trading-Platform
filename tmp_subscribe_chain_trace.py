from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import threading
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.market.websocket_client import WebSocketClient
from src.marketdata.engine import MarketDataEngine
from src.services.market_data_service import MarketDataService, market_data_service
from src.services.websocket_service import WebSocketService
from src.ui.portfolio_summary_page import PortfolioSummaryPage


ROOT = os.path.normcase(os.path.abspath("d:/Projects/ASG")).replace("\\", "/")

records: list[dict[str, Any]] = []
branches: list[dict[str, Any]] = []

trace_active = False
stop_triggered = False
stop_reason: dict[str, Any] | None = None

call_seq = 0
frame_to_call_id: dict[int, int] = {}
root_start_call_id: int | None = None


orig_subscribe = MarketDataService.subscribe
orig_ws_service_start = WebSocketService.start
orig_ws_client_start = WebSocketClient.start
orig_mde_start = MarketDataEngine.start
orig_mde_run = getattr(MarketDataEngine, "run", None)
orig_mde__run = getattr(MarketDataEngine, "_run", None)
orig_thread_init = threading.Thread.__init__
orig_create_task = asyncio.create_task
orig_qtimer_single_shot = QTimer.singleShot


def _in_scope(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path)).replace("\\", "/")
    if not p.startswith(ROOT + "/"):
        return False
    return "/src/" in p or p.endswith("/tmp_subscribe_chain_trace.py")


def _safe_repr(value: Any, max_len: int = 220) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<{type(value).__name__}>"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _mark_stop(kind: str, file: str, line: int, function: str) -> None:
    global stop_triggered, stop_reason
    if stop_triggered:
        return
    stop_triggered = True
    stop_reason = {"kind": kind, "file": file, "line": line, "function": function}


def _new_record(frame: Any, call_id: int) -> dict[str, Any]:
    return {
        "call_id": call_id,
        "file": frame.f_code.co_filename,
        "line": frame.f_lineno,
        "function": frame.f_code.co_name,
        "entered": True,
        "exited": False,
        "return_value": None,
        "exception": None,
    }


def _profile(frame: Any, event: str, arg: Any):
    global call_seq, root_start_call_id

    filename = frame.f_code.co_filename
    if not _in_scope(filename):
        return _profile

    if event == "call":
        if trace_active and not stop_triggered:
            call_seq += 1
            frame_to_call_id[id(frame)] = call_seq
            records.append(_new_record(frame, call_seq))
            if frame.f_code.co_name == "start" and frame.f_code.co_filename.endswith("portfolio_view_model.py"):
                root_start_call_id = call_seq
        return _profile

    if not trace_active or stop_triggered:
        return _profile

    call_id = frame_to_call_id.get(id(frame))
    if call_id is None:
        return _profile

    if event == "return":
        for row in reversed(records):
            if row["call_id"] == call_id:
                row["exited"] = True
                row["return_value"] = _safe_repr(arg)
                break
        if root_start_call_id is not None and call_id == root_start_call_id and not stop_triggered:
            _mark_stop("execution segment completed", frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

    if event == "exception":
        exc_type, exc, _tb = arg
        for row in reversed(records):
            if row["call_id"] == call_id and row["exception"] is None:
                row["exception"] = {"type": getattr(exc_type, "__name__", str(exc_type)), "message": str(exc)}
                break
        _mark_stop("any exception", frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)

    return _profile


def _patch_runtime() -> None:
    global trace_active

    def patched_subscribe(self: Any, handler: Any):
        global trace_active
        trace_active = True
        cond = handler not in self._handlers
        branches.append(
            {
                "file": inspect.getsourcefile(orig_subscribe),
                "line": 70,
                "function": "MarketDataService.subscribe",
                "condition": "handler not in self._handlers",
                "evaluated_value": bool(cond),
                "branch_skipped": not bool(cond),
            }
        )
        return orig_subscribe(self, handler)

    def patched_ws_service_start(self: Any, *args: Any, **kwargs: Any):
        fr = inspect.currentframe()
        if fr is not None:
            _mark_stop("WebSocketService.start()", fr.f_code.co_filename, fr.f_lineno, "WebSocketService.start")
        return orig_ws_service_start(self, *args, **kwargs)

    def patched_ws_client_start(self: Any, *args: Any, **kwargs: Any):
        fr = inspect.currentframe()
        if fr is not None:
            _mark_stop("WebSocketClient.connect()", fr.f_code.co_filename, fr.f_lineno, "WebSocketClient.start")
        return orig_ws_client_start(self, *args, **kwargs)

    def patched_mde_start(self: Any, *args: Any, **kwargs: Any):
        fr = inspect.currentframe()
        if fr is not None:
            _mark_stop("MarketDataEngine.start()", fr.f_code.co_filename, fr.f_lineno, "MarketDataEngine.start")
        return orig_mde_start(self, *args, **kwargs)

    def patched_mde_run(self: Any, *args: Any, **kwargs: Any):
        fr = inspect.currentframe()
        if fr is not None:
            _mark_stop("MarketDataEngine.run()", fr.f_code.co_filename, fr.f_lineno, "MarketDataEngine.run")
        return orig_mde_run(self, *args, **kwargs)

    def patched_mde__run(self: Any, *args: Any, **kwargs: Any):
        fr = inspect.currentframe()
        if fr is not None:
            _mark_stop("MarketDataEngine.run()", fr.f_code.co_filename, fr.f_lineno, "MarketDataEngine._run")
        return orig_mde__run(self, *args, **kwargs)

    def patched_thread_init(self: Any, *args: Any, **kwargs: Any):
        if trace_active and not stop_triggered:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("any thread creation", fr.f_code.co_filename, fr.f_lineno, "threading.Thread.__init__")
        return orig_thread_init(self, *args, **kwargs)

    def patched_create_task(*args: Any, **kwargs: Any):
        if trace_active and not stop_triggered:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("any asyncio.create_task()", fr.f_code.co_filename, fr.f_lineno, "asyncio.create_task")
        return orig_create_task(*args, **kwargs)

    def patched_single_shot(*args: Any, **kwargs: Any):
        if trace_active and not stop_triggered:
            fr = inspect.currentframe()
            if fr is not None:
                _mark_stop("any QTimer.singleShot()", fr.f_code.co_filename, fr.f_lineno, "QTimer.singleShot")
        return orig_qtimer_single_shot(*args, **kwargs)

    MarketDataService.subscribe = patched_subscribe
    WebSocketService.start = patched_ws_service_start
    WebSocketClient.start = patched_ws_client_start
    MarketDataEngine.start = patched_mde_start
    if orig_mde_run is not None:
        MarketDataEngine.run = patched_mde_run
    if orig_mde__run is not None:
        MarketDataEngine._run = patched_mde__run
    threading.Thread.__init__ = patched_thread_init
    asyncio.create_task = patched_create_task
    QTimer.singleShot = patched_single_shot


def main() -> None:
    _patch_runtime()
    sys.setprofile(_profile)
    _app = QApplication.instance() or QApplication([])

    raised = None
    try:
        _page = PortfolioSummaryPage(None)
    except Exception as exc:
        raised = exc
        if not stop_triggered:
            _mark_stop("any exception", __file__, 0, "main")

    output = {
        "stop_reason": stop_reason,
        "exception": None if raised is None else {"type": type(raised).__name__, "message": str(raised)},
        "branches": branches,
        "steps": records,
        "WebSocketService.started": False,
        "WebSocketClient.connected": False,
        "MarketDataEngine.running": False,
        "MarketDataService.running": bool(getattr(market_data_service, "_worker", None) and market_data_service._worker.is_alive()),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()


def main() -> None:
    _patch_runtime()
    sys.setprofile(_profile)
    _app = QApplication.instance() or QApplication([])

    raised = None
    try:
        # This constructor invokes PortfolioViewModel.start(), which calls PortfolioService.subscribe(),
        # which then calls MarketDataService.subscribe().
        _page = PortfolioSummaryPage(None)
    except Exception as exc:
        raised = exc
        if not stop_triggered:
            _mark_stop("any exception", __file__, 0, "main")

    output = {
        "stop_reason": stop_reason,
        "exception": None if raised is None else {"type": type(raised).__name__, "message": str(raised)},
        "branches": branches,
        "steps": records,
        "WebSocketService.started": False,
        "WebSocketClient.connected": False,
        "MarketDataEngine.running": False,
        "MarketDataService.running": bool(getattr(market_data_service, "_worker", None) and market_data_service._worker.is_alive()),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
