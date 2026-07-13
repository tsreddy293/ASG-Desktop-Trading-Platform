from __future__ import annotations

import inspect
import json
import os
from typing import Any

from PySide6.QtWidgets import QApplication

from src.app import create_app
from src.brokers import broker_manager
from src.brokers.fivepaisa.auth_service import AccessTokenResponse, FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.session_manager import BrokerSession, FivePaisaSessionManager
from src.ui.portfolio_summary_page import PortfolioSummaryPage


ROOT = os.path.normcase(os.path.abspath("d:/Projects/ASG")).replace("\\", "/")

trace: dict[str, Any] = {
    "instances_created": [],
    "calls": [],
}
_seen_instance_ids: set[int] = set()

orig_new = FivePaisaSessionManager.__new__
orig_init = FivePaisaSessionManager.__init__
orig_set_session = FivePaisaSessionManager.set_session
orig_get_session = FivePaisaSessionManager.get_session
orig_load_secure = FivePaisaSessionManager._load_secure
orig_store_secure = FivePaisaSessionManager._store_secure
orig_needs_refresh = FivePaisaSessionManager.needs_refresh

orig_exchange = FivePaisaAuthService.exchange_request_token
orig_oauth_flow = FivePaisaBrokerClient._authenticate_via_oauth_flow


def _workspace_caller() -> dict[str, Any]:
    for fr in inspect.stack(context=0)[2:]:
        p = os.path.normcase(os.path.abspath(fr.filename)).replace("\\", "/")
        if p.startswith(ROOT + "/"):
            return {
                "file": fr.filename,
                "line": fr.lineno,
                "caller": fr.function,
            }
    fr = inspect.stack(context=0)[2]
    return {
        "file": fr.filename,
        "line": fr.lineno,
        "caller": fr.function,
    }


def _session_obj(self: FivePaisaSessionManager):
    try:
        return getattr(self, "_session", None)
    except Exception:
        return None


def _session_id(self: FivePaisaSessionManager) -> int | None:
    s = _session_obj(self)
    return id(s) if s is not None else None


def _token_len(self: FivePaisaSessionManager) -> int:
    s = _session_obj(self)
    tok = (getattr(s, "access_token", "") or "") if s is not None else ""
    return len(tok)


def _state(self: FivePaisaSessionManager) -> str | None:
    try:
        st = self.state()
        return getattr(st, "value", str(st))
    except Exception:
        return None


def _ret(v: Any) -> Any:
    if isinstance(v, BrokerSession):
        return {
            "type": "BrokerSession",
            "id": id(v),
            "access_token_length": len(v.access_token or ""),
        }
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    return repr(v)


def _record_call(name: str, self: FivePaisaSessionManager, ret: Any) -> None:
    trace["calls"].append(
        {
            "method": name,
            "id(self)": id(self),
            "session_object_id": _session_id(self),
            "access_token_length": _token_len(self),
            "session_state": _state(self),
            "return_value": _ret(ret),
        }
    )


def patched_new(cls, *args, **kwargs):
    obj = orig_new(cls, *args, **kwargs)
    oid = id(obj)
    if oid not in _seen_instance_ids:
        _seen_instance_ids.add(oid)
        c = _workspace_caller()
        trace["instances_created"].append(
            {
                "id(self)": oid,
                "file": c["file"],
                "line": c["line"],
                "caller": c["caller"],
            }
        )
    return obj


def patched_init(self, *args, **kwargs):
    return orig_init(self, *args, **kwargs)


def patched_set_session(self, *args, **kwargs):
    out = orig_set_session(self, *args, **kwargs)
    _record_call("set_session", self, out)
    return out


def patched_get_session(self, *args, **kwargs):
    out = orig_get_session(self, *args, **kwargs)
    _record_call("get_session", self, out)
    return out


def patched_load_secure(self, *args, **kwargs):
    out = orig_load_secure(self, *args, **kwargs)
    _record_call("_load_secure", self, out)
    return out


def patched_store_secure(self, *args, **kwargs):
    out = orig_store_secure(self, *args, **kwargs)
    _record_call("_store_secure", self, out)
    return out


def patched_needs_refresh(self, *args, **kwargs):
    out = orig_needs_refresh(self, *args, **kwargs)
    _record_call("needs_refresh", self, out)
    return out


def patched_exchange(self, request_token: str):
    return AccessTokenResponse(
        access_token="TRACE_ACCESS_TOKEN_" + ("X" * 180),
        refresh_token="TRACE_REFRESH_TOKEN_" + ("Y" * 180),
        client_code="52828064",
        status="0",
        raw_response={"body": {"Status": 0, "Message": "Success"}},
    )


def patched_oauth_flow(self):
    self.reauthenticate_from_request_token("TRACE_REQUEST_TOKEN")


def main() -> None:
    FivePaisaSessionManager.__new__ = patched_new
    FivePaisaSessionManager.__init__ = patched_init
    FivePaisaSessionManager.set_session = patched_set_session
    FivePaisaSessionManager.get_session = patched_get_session
    FivePaisaSessionManager._load_secure = patched_load_secure
    FivePaisaSessionManager._store_secure = patched_store_secure
    FivePaisaSessionManager.needs_refresh = patched_needs_refresh

    FivePaisaAuthService.exchange_request_token = patched_exchange
    FivePaisaBrokerClient._authenticate_via_oauth_flow = patched_oauth_flow

    _app = QApplication.instance() or QApplication([])
    app_obj = create_app()

    try:
        broker_manager.connect()
    except Exception:
        pass

    try:
        _page = PortfolioSummaryPage(None)
        _page.refresh_data()
    except Exception:
        pass

    print(json.dumps(trace, indent=2))


if __name__ == "__main__":
    main()
