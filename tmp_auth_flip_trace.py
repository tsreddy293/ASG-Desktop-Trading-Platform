from __future__ import annotations

import inspect
import json
import traceback
from datetime import datetime, timezone
from typing import Any

from src.brokers import broker_manager
from src.brokers.broker_manager import BrokerManager
from src.brokers.fivepaisa.auth_service import AccessTokenResponse, FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient


TARGET_FIELDS = {
    "authenticated",
    "_authentication_state",
    "is_authenticated",
    "authenticated_state",
    "connection_state",
    "session.authenticated",
    "_authentication_in_progress",  # Runtime source behind authentication_in_progress()
}

report: dict[str, Any] = {
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "assignments": [],
    "first_true_to_false": None,
    "stopped": None,
}


orig_bc_setattr = FivePaisaBrokerClient.__setattr__
orig_oauth = FivePaisaBrokerClient._authenticate_via_oauth_flow
orig_exchange = FivePaisaAuthService.exchange_request_token
orig_connect = BrokerManager.connect


def _project_frame() -> dict[str, Any] | None:
    for frame in inspect.stack(context=0)[2:]:
        f = frame.filename.replace('\\', '/')
        if '/src/' in f:
            return {
                "file": frame.filename,
                "line": frame.lineno,
                "function": frame.function,
            }
    return None


def _stack_lines(limit: int = 12) -> list[str]:
    lines = traceback.format_stack(limit=limit)
    return [line.rstrip("\n") for line in lines]


def _log_assignment(name: str, old: Any, new: Any) -> None:
    if name not in TARGET_FIELDS:
        return
    frame = _project_frame()
    row = {
        "field": name,
        "old_value": repr(old),
        "new_value": repr(new),
        "file": frame["file"] if frame else None,
        "line": frame["line"] if frame else None,
        "call_stack": _stack_lines(),
    }
    report["assignments"].append(row)

    if old is True and new is False and report["first_true_to_false"] is None:
        report["first_true_to_false"] = row


def patched_bc_setattr(self, name, value):
    old = getattr(self, name, None)
    _log_assignment(name, old, value)
    return orig_bc_setattr(self, name, value)


def patched_exchange(self, request_token: str) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token="TRACE_ACCESS_TOKEN_" + ("X" * 180),
        refresh_token="TRACE_REFRESH_TOKEN_" + ("Y" * 180),
        client_code="52828064",
        status="0",
        raw_response={"body": {"Status": 0, "Message": "Success"}},
    )


def patched_oauth(self):
    self.reauthenticate_from_request_token("TRACE_ONLY_REQUEST_TOKEN")


def patched_connect(self):
    return orig_connect(self)


def main() -> None:
    FivePaisaBrokerClient.__setattr__ = patched_bc_setattr
    FivePaisaAuthService.exchange_request_token = patched_exchange
    FivePaisaBrokerClient._authenticate_via_oauth_flow = patched_oauth
    BrokerManager.connect = patched_connect

    try:
        broker_manager.connect()
        report["stopped"] = "connect_completed"
    except Exception as exc:
        report["stopped"] = f"exception:{type(exc).__name__}:{exc}"

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
