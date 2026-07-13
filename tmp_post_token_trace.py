from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from typing import Any

from src.brokers import broker_manager
from src.brokers.broker_manager import BrokerManager, FivePaisaBroker
from src.brokers.fivepaisa.auth_service import AccessTokenResponse, FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import AuthResult, FivePaisaBrokerClient
from src.brokers.fivepaisa.login import FivePaisaLoginService
from src.brokers.fivepaisa.session_manager import BrokerSession, FivePaisaSessionManager
from src.market.websocket_client import WebSocketClient
from src.services.market_data_service import MarketDataService, market_data_service
from src.services.websocket_service import WebSocketService


trace_report: dict[str, Any] = {
    "started_post_token": False,
    "steps": [],
    "first_exception": None,
    "stopped_at": None,
    "ts_utc": datetime.now(timezone.utc).isoformat(),
}

websocket_start_seen = {"service": False, "client": False}
market_feed_start_seen = {"called": False}


ORIGINALS: dict[str, Any] = {}


def _safe_repr(value: Any, max_len: int = 500) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<{type(value).__name__}>"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _result_obj(value: Any) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "type": type(value).__name__,
        "repr": _safe_repr(value),
    }
    if isinstance(value, AccessTokenResponse):
        obj["access_token_len"] = len(value.access_token or "")
        obj["refresh_token_len"] = len(value.refresh_token or "")
        obj["client_code"] = value.client_code
        obj["status"] = value.status
    elif isinstance(value, AuthResult):
        obj["access_token_len"] = len(value.access_token or "")
        obj["refresh_token_len"] = len(value.refresh_token or "")
        obj["client_code"] = value.client_code
        obj["status"] = value.status
    elif isinstance(value, BrokerSession):
        obj["access_token_len"] = len(value.access_token or "")
        obj["client_code"] = value.client_code
        obj["status"] = value.status
    return obj


def _collect_runtime_state() -> dict[str, Any]:
    session_manager = FivePaisaSessionManager()
    session = None
    try:
        session = session_manager.get_session()
    except Exception:
        session = None

    access_token = (getattr(session, "access_token", "") or "") if session is not None else ""

    broker = None
    broker_name = None
    try:
        broker = broker_manager.active_broker()
        broker_name = getattr(broker, "name", None)
    except Exception:
        pass

    broker_client = None
    login_service = getattr(broker, "_login_service", None) if broker is not None else None
    if login_service is not None:
        broker_client = getattr(login_service, "_broker_client", None)

    auth_state = None
    if broker_client is not None:
        try:
            auth_state = bool(broker_client.authentication_in_progress())
        except Exception:
            auth_state = None

    session_state = None
    try:
        session_state = session_manager.state().value
    except Exception:
        session_state = None

    feed_worker_alive = False
    worker = getattr(market_data_service, "_worker", None)
    if worker is not None:
        try:
            feed_worker_alive = bool(worker.is_alive())
        except Exception:
            feed_worker_alive = False

    return {
        "access_token_length": len(access_token),
        "token_stored": bool(access_token),
        "authentication_state": auth_state,
        "broker_state": {
            "active_broker": broker_name,
            "broker_type": type(broker).__name__ if broker is not None else None,
        },
        "session_state": session_state,
        "websocket_initialization": {
            "websocket_service_start_called": websocket_start_seen["service"],
            "websocket_client_start_called": websocket_start_seen["client"],
        },
        "market_feed_initialization": {
            "market_data_service_start_called": market_feed_start_seen["called"],
            "market_data_worker_alive": feed_worker_alive,
        },
    }


def _record(function_name: str, returned: Any = None, exc: Exception | None = None) -> None:
    row = {
        "function_name": function_name,
        "returned_object": None if returned is None else _result_obj(returned),
        **_collect_runtime_state(),
        "first_exception": trace_report["first_exception"],
    }

    if exc is not None and trace_report["first_exception"] is None:
        trace_report["first_exception"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(limit=8),
            "at_function": function_name,
        }
        row["first_exception"] = trace_report["first_exception"]

    trace_report["steps"].append(row)


def _wrap_method(cls: Any, method_name: str, key: str) -> None:
    original = getattr(cls, method_name)
    ORIGINALS[key] = original

    def wrapped(self, *args, **kwargs):
        try:
            out = original(self, *args, **kwargs)
            if method_name == "exchange_request_token":
                token_len = len(getattr(out, "access_token", "") or "")
                trace_report["started_post_token"] = token_len > 0
                _record(f"{cls.__name__}.{method_name}", returned=out)
            elif trace_report["started_post_token"]:
                _record(f"{cls.__name__}.{method_name}", returned=out)
            return out
        except Exception as exc:
            if method_name == "exchange_request_token" or trace_report["started_post_token"]:
                _record(f"{cls.__name__}.{method_name}", exc=exc)
            raise

    setattr(cls, method_name, wrapped)


def _wrap_market_feed_start() -> None:
    original = MarketDataService.start
    ORIGINALS["MarketDataService.start"] = original

    def wrapped(self, *args, **kwargs):
        market_feed_start_seen["called"] = True
        out = original(self, *args, **kwargs)
        if trace_report["started_post_token"]:
            _record("MarketDataService.start", returned=out)
        return out

    MarketDataService.start = wrapped


def _wrap_websocket_starts() -> None:
    ws_service_start = WebSocketService.start
    ORIGINALS["WebSocketService.start"] = ws_service_start

    def wrapped_service(self, *args, **kwargs):
        websocket_start_seen["service"] = True
        out = ws_service_start(self, *args, **kwargs)
        if trace_report["started_post_token"]:
            _record("WebSocketService.start", returned=out)
        return out

    WebSocketService.start = wrapped_service

    ws_client_start = WebSocketClient.start
    ORIGINALS["WebSocketClient.start"] = ws_client_start

    def wrapped_client(self, *args, **kwargs):
        websocket_start_seen["client"] = True
        out = ws_client_start(self, *args, **kwargs)
        if trace_report["started_post_token"]:
            _record("WebSocketClient.start", returned=out)
        return out

    WebSocketClient.start = wrapped_client


def install_tracing() -> None:
    _wrap_method(FivePaisaAuthService, "exchange_request_token", "FivePaisaAuthService.exchange_request_token")
    _wrap_method(FivePaisaSessionManager, "set_session", "FivePaisaSessionManager.set_session")
    _wrap_method(FivePaisaBrokerClient, "reauthenticate_from_request_token", "FivePaisaBrokerClient.reauthenticate_from_request_token")
    _wrap_method(FivePaisaBrokerClient, "ensure_authenticated", "FivePaisaBrokerClient.ensure_authenticated")
    _wrap_method(FivePaisaLoginService, "login", "FivePaisaLoginService.login")
    _wrap_method(FivePaisaBroker, "login", "FivePaisaBroker.login")
    _wrap_method(BrokerManager, "connect", "BrokerManager.connect")
    _wrap_market_feed_start()
    _wrap_websocket_starts()


def main() -> None:
    install_tracing()

    try:
        broker_manager.connect()
        trace_report["stopped_at"] = "BrokerManager.connect (success)"
    except Exception as exc:
        if trace_report["first_exception"] is None:
            trace_report["first_exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(limit=10),
                "at_function": "top_level.connect",
            }
        trace_report["stopped_at"] = "first_failure"

    print(json.dumps(trace_report, indent=2))


if __name__ == "__main__":
    main()
