from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone

from src.brokers.broker_manager import BrokerManager


def _session_token_len(session) -> int:
    if session is None:
        return 0
    token = getattr(session, "access_token", "") or ""
    return len(str(token))


def _safe_state_name(state_obj) -> str:
    try:
        return str(getattr(state_obj, "value", state_obj))
    except Exception:
        return "<error>"


def _snapshot(label: str, manager: BrokerManager) -> dict:
    broker = manager.active_broker()
    login_service = broker._login_service
    broker_client = login_service._broker_client
    market = broker._market
    market_data = market._market_data

    client_session_manager = broker_client.session_manager
    market_session_manager = market_data._session_manager

    client_session = client_session_manager.get_session()
    market_session = market_session_manager.get_session()

    broker_client_authenticated = bool(broker_client.is_authenticated())

    market_authenticated = False
    market_require_expr = "session_manager.is_connected() and not broker_client.authentication_in_progress()"
    try:
        market_authenticated = bool(
            client_session_manager.is_connected() and not broker_client.authentication_in_progress()
        )
    except Exception:
        market_authenticated = False

    market_data_authenticated = False
    market_data_require_expr = "_session_manager.is_connected() and not _session_manager.needs_refresh()"
    try:
        market_data_authenticated = bool(
            market_session_manager.is_connected() and not market_session_manager.needs_refresh()
        )
    except Exception:
        market_data_authenticated = False

    return {
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ids": {
            "FivePaisaBroker": id(broker),
            "BrokerClient": id(broker_client),
            "Market": id(market),
            "MarketDataService": id(market_data),
            "SessionManager_in_BrokerClient": id(client_session_manager),
            "SessionManager_in_MarketDataService": id(market_session_manager),
            "SessionObject_in_BrokerClient": id(client_session) if client_session is not None else None,
            "SessionObject_in_MarketDataService": id(market_session) if market_session is not None else None,
        },
        "states": {
            "BrokerClient.is_authenticated": broker_client_authenticated,
            "BrokerClient.session_manager.state": _safe_state_name(client_session_manager.state()),
            "BrokerClient.session_manager.is_connected": bool(client_session_manager.is_connected()),
            "Market._require_authenticated": {
                "expr": market_require_expr,
                "value": market_authenticated,
                "auth_in_progress": bool(broker_client.authentication_in_progress()),
            },
            "MarketDataService._require_authenticated": {
                "expr": market_data_require_expr,
                "value": market_data_authenticated,
                "state": _safe_state_name(market_session_manager.state()),
                "is_connected": bool(market_session_manager.is_connected()),
                "needs_refresh": bool(market_session_manager.needs_refresh()),
            },
        },
        "token_lengths": {
            "BrokerClient": _session_token_len(client_session),
            "Market": _session_token_len(market_session),
        },
    }


def main() -> None:
    out: dict = {
        "trace_path": [
            "BrokerManager.connect()",
            "FivePaisaBroker",
            "FivePaisaLoginService",
            "FivePaisaBrokerClient",
            "Market.get_option_chain()",
            "_require_authenticated()",
        ]
    }

    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")

    out["before_connect"] = _snapshot("before_connect", manager)

    connect_ok = False
    connect_error = None
    try:
        manager.connect()
        connect_ok = True
    except Exception as exc:
        connect_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    out["connect"] = {
        "ok": connect_ok,
        "error": connect_error,
    }

    out["after_connect"] = _snapshot("after_connect", manager)

    option_ok = False
    option_error = None
    option_rows = None
    try:
        payload = manager.get_option_chain("NIFTY", expiry="31 Jul 2026")
        option_ok = True
        if isinstance(payload, dict):
            rows = payload.get("rows")
            option_rows = len(rows) if isinstance(rows, list) else None
    except Exception as exc:
        option_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    out["option_chain_call"] = {
        "ok": option_ok,
        "rows": option_rows,
        "error": option_error,
    }

    out["after_option_chain"] = _snapshot("after_option_chain", manager)

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
