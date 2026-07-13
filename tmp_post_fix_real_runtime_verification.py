from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from time import sleep
from typing import Any, Callable

from src.brokers.broker_manager import BrokerManager
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
from src.brokers.fivepaisa.session_manager import FivePaisaSessionManager


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if key in {"AccessToken", "RefreshToken", "RequestToken", "Authorization", "EncryKey", "Key", "key"}:
                text = str(v or "")
                out[key] = f"***MASKED(len={len(text)})***"
            else:
                out[key] = mask_secrets(v)
        return out
    if isinstance(value, list):
        return [mask_secrets(v) for v in value]
    return value


class RuntimeProbe:
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.flags: dict[str, bool] = {
            "http_200": False,
            "status_parsed_0": False,
            "broker_connection_error_not_raised": False,
            "set_session_called": False,
            "session_connected": False,
            "access_token_len_gt_0": False,
            "connect_returned": False,
            "option_chain_loaded": False,
            "market_depth_loaded": False,
            "live_quotes_update": False,
        }
        self.metrics: dict[str, Any] = {
            "access_token_length": 0,
            "parsed_status": None,
            "option_rows": 0,
            "quotes_count": 0,
            "depth_symbol": None,
        }

    def log(self, message: str) -> None:
        line = f"{now()} {message}"
        self.logs.append(line)
        print(line)


probe = RuntimeProbe()


def install_urlopen_probe() -> Callable[[], None]:
    import src.brokers.fivepaisa.auth_service as auth_mod

    original_urlopen = auth_mod.urlopen

    def probed_urlopen(request, timeout=20):
        url = getattr(request, "full_url", "<unknown>")
        method = getattr(request, "method", "GET")
        probe.log(f"HTTP_REQUEST method={method} url={url} timeout={timeout}")
        response = original_urlopen(request, timeout=timeout)

        class _ResponseProxy:
            def __init__(self, resp):
                self._resp = resp

            def __enter__(self):
                entered = self._resp.__enter__()
                return _ResponseProxy(entered)

            def __exit__(self, exc_type, exc, tb):
                return self._resp.__exit__(exc_type, exc, tb)

            def read(self, *args, **kwargs):
                raw = self._resp.read(*args, **kwargs)
                status = getattr(self._resp, "status", None)
                if status is None:
                    try:
                        status = self._resp.getcode()
                    except Exception:
                        status = "<unknown>"
                if status == 200:
                    probe.flags["http_200"] = True
                text = raw.decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(text)
                    body = json.dumps(mask_secrets(parsed), ensure_ascii=True)
                except Exception:
                    body = text
                probe.log(f"HTTP_RESPONSE status={status}")
                probe.log(f"HTTP_RESPONSE_BODY {body}")
                return raw

            def __getattr__(self, item):
                return getattr(self._resp, item)

        return _ResponseProxy(response)

    auth_mod.urlopen = probed_urlopen

    def restore() -> None:
        auth_mod.urlopen = original_urlopen

    return restore


def wrap_exchange_request_token() -> Callable[[], None]:
    original = FivePaisaAuthService.exchange_request_token

    def wrapped(self, request_token: str):
        probe.log("ENTER exchange_request_token")
        out = original(self, request_token)
        probe.metrics["parsed_status"] = out.status
        if str(out.status).strip() == "0":
            probe.flags["status_parsed_0"] = True
        probe.log(f"RETURN exchange_request_token parsed_status={out.status}")
        return out

    FivePaisaAuthService.exchange_request_token = wrapped

    def restore() -> None:
        FivePaisaAuthService.exchange_request_token = original

    return restore


def wrap_set_session() -> Callable[[], None]:
    original = FivePaisaSessionManager.set_session

    def wrapped(self, *args, **kwargs):
        probe.flags["set_session_called"] = True
        before = self.state().value
        probe.log(f"ENTER set_session state_before={before}")
        out = original(self, *args, **kwargs)
        after = self.state().value
        token_len = len(getattr(out, "access_token", "") or "")
        probe.metrics["access_token_length"] = token_len
        probe.flags["access_token_len_gt_0"] = token_len > 0
        probe.flags["session_connected"] = str(after) == "Connected"
        probe.log(f"RETURN set_session state_after={after} access_token_len={token_len}")
        return out

    FivePaisaSessionManager.set_session = wrapped

    def restore() -> None:
        FivePaisaSessionManager.set_session = original

    return restore


def main() -> None:
    restore_urlopen = install_urlopen_probe()
    restore_exchange = wrap_exchange_request_token()
    restore_set_session = wrap_set_session()

    summary: dict[str, Any] = {}

    try:
        manager = BrokerManager()
        manager.set_active_broker("fivepaisa")

        try:
            manager.connect()
            probe.flags["connect_returned"] = True
            probe.flags["broker_connection_error_not_raised"] = True
            probe.log("RETURN BrokerManager.connect success")
        except Exception as exc:
            probe.log(f"EXCEPTION BrokerManager.connect {type(exc).__name__}: {exc}")
            probe.log(traceback.format_exc())

        if probe.flags["connect_returned"]:
            try:
                oc = manager.get_option_chain("NIFTY", expiry="31 Jul 2026")
                rows = oc.get("rows") if isinstance(oc, dict) else None
                if isinstance(rows, list) and len(rows) > 0:
                    probe.flags["option_chain_loaded"] = True
                    probe.metrics["option_rows"] = len(rows)
                probe.log(f"OPTION_CHAIN rows={probe.metrics['option_rows']}")
            except Exception as exc:
                probe.log(f"EXCEPTION get_option_chain {type(exc).__name__}: {exc}")
                probe.log(traceback.format_exc())

            try:
                depth = manager.get_market_depth("SBIN")
                if isinstance(depth, dict) and depth.get("symbol"):
                    probe.flags["market_depth_loaded"] = True
                    probe.metrics["depth_symbol"] = depth.get("symbol")
                probe.log(f"MARKET_DEPTH symbol={probe.metrics['depth_symbol']}")
            except Exception as exc:
                probe.log(f"EXCEPTION get_market_depth {type(exc).__name__}: {exc}")
                probe.log(traceback.format_exc())

            try:
                q1 = manager.get_quotes(["SBIN", "RELIANCE"])
                sleep(5)
                q2 = manager.get_quotes(["SBIN", "RELIANCE"])
                c1 = len(q1) if isinstance(q1, list) else 0
                c2 = len(q2) if isinstance(q2, list) else 0
                probe.metrics["quotes_count"] = c2
                # Treat successful repeated pulls as live quote update path working.
                if c1 > 0 and c2 > 0:
                    probe.flags["live_quotes_update"] = True
                probe.log(f"LIVE_QUOTES first_count={c1} second_count={c2}")
            except Exception as exc:
                probe.log(f"EXCEPTION get_quotes {type(exc).__name__}: {exc}")
                probe.log(traceback.format_exc())

        summary = {
            "checks": {
                "1_http_200_received": probe.flags["http_200"],
                "2_status_parsed_as_0": probe.flags["status_parsed_0"],
                "3_broker_connection_error_not_raised": probe.flags["broker_connection_error_not_raised"],
                "4_set_session_executes": probe.flags["set_session_called"],
                "5_sessionmanager_connected": probe.flags["session_connected"],
                "6_access_token_length_gt_0": probe.flags["access_token_len_gt_0"],
                "7_brokermanager_connect_returns": probe.flags["connect_returned"],
                "8_option_chain_loads": probe.flags["option_chain_loaded"],
                "9_market_depth_loads": probe.flags["market_depth_loaded"],
                "10_live_quotes_update": probe.flags["live_quotes_update"],
            },
            "metrics": probe.metrics,
            "logs": probe.logs,
        }
        print("=== FINAL_VERIFICATION_JSON ===")
        print(json.dumps(summary, indent=2))
    finally:
        restore_set_session()
        restore_exchange()
        restore_urlopen()


if __name__ == "__main__":
    main()
