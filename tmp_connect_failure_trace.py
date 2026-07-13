from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.broker_manager import BrokerManager
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.login import FivePaisaLoginService
from src.brokers.fivepaisa.session_manager import FivePaisaSessionManager


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_secrets(value: Any) -> Any:
    secret_keys = {
        "AccessToken",
        "access_token",
        "RefreshToken",
        "refresh_token",
        "RequestToken",
        "request_token",
        "Authorization",
        "EncryKey",
        "key",
        "Key",
    }

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if str(k) in secret_keys:
                text = str(v or "")
                out[k] = f"***MASKED(len={len(text)})***"
            else:
                out[k] = mask_secrets(v)
        return out
    if isinstance(value, list):
        return [mask_secrets(v) for v in value]
    return value


def session_state_from_self(obj: Any) -> str:
    try:
        if isinstance(obj, FivePaisaSessionManager):
            return str(obj.state().value)
        session_manager = getattr(obj, "_session_manager", None)
        if session_manager is not None:
            return str(session_manager.state().value)
        broker_client = getattr(obj, "_broker_client", None)
        if broker_client is not None:
            sm = getattr(broker_client, "session_manager", None)
            if sm is not None:
                return str(sm.state().value)
        login_service = getattr(obj, "_login_service", None)
        if login_service is not None:
            bc = getattr(login_service, "_broker_client", None)
            if bc is not None:
                sm = getattr(bc, "session_manager", None)
                if sm is not None:
                    return str(sm.state().value)
    except Exception:
        return "<state-error>"
    return "<state-unavailable>"


def trace_wrapper(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(*args, **kwargs):
        self_obj = args[0] if args else None
        before = session_state_from_self(self_obj)
        print(f"[{now()}] ENTER {name}")
        print(f"  session_state_before={before}")
        try:
            result = fn(*args, **kwargs)
            after = session_state_from_self(self_obj)
            print(f"[{now()}] RETURN {name}")
            print(f"  session_state_after={after}")
            return result
        except Exception as exc:
            after = session_state_from_self(self_obj)
            print(f"[{now()}] EXCEPTION {name}: {type(exc).__name__}: {exc}")
            print(f"  session_state_after={after}")
            print(traceback.format_exc())
            raise

    return wrapped


def install_urlopen_probe() -> Callable[[], None]:
    import src.brokers.fivepaisa.auth_service as auth_mod

    original_urlopen = auth_mod.urlopen

    def probed_urlopen(request, timeout=20):
        url = getattr(request, "full_url", "<unknown>")
        method = getattr(request, "method", "GET")
        print(f"[{now()}] HTTP REQUEST method={method} url={url} timeout={timeout}")

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
                text = raw.decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(text)
                    masked = mask_secrets(parsed)
                    body = json.dumps(masked, ensure_ascii=True)
                except Exception:
                    body = text
                print(f"[{now()}] HTTP RESPONSE status={status}")
                print(f"[{now()}] HTTP RESPONSE BODY {body}")
                return raw

            def __getattr__(self, item):
                return getattr(self._resp, item)

        return _ResponseProxy(response)

    auth_mod.urlopen = probed_urlopen

    def restore() -> None:
        auth_mod.urlopen = original_urlopen

    return restore


def main() -> None:
    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")

    broker = manager.active_broker()
    login_service = broker._login_service
    broker_client = login_service._broker_client

    originals: list[tuple[Any, str, Any]] = []

    def patch(obj: Any, attr: str, wrapper_name: str) -> None:
        orig = getattr(obj, attr)
        originals.append((obj, attr, orig))
        setattr(obj, attr, trace_wrapper(wrapper_name, orig))

    patch(BrokerManager, "connect", "BrokerManager.connect")
    patch(type(broker), "login", "FivePaisaBroker.login")
    patch(FivePaisaLoginService, "login", "FivePaisaLoginService.login")
    patch(FivePaisaBrokerClient, "ensure_authenticated", "FivePaisaBrokerClient.ensure_authenticated")
    patch(FivePaisaAuthService, "exchange_request_token", "FivePaisaAuthService.exchange_request_token")
    patch(FivePaisaSessionManager, "set_session", "FivePaisaSessionManager.set_session")

    restore_urlopen = install_urlopen_probe()

    print(f"[{now()}] TRACE START")
    print(f"[{now()}] initial_session_state={broker_client.session_manager.state().value}")

    try:
        manager.connect()
        print(f"[{now()}] TRACE END connect returned successfully")
    except BrokerConnectionError as exc:
        print(f"[{now()}] STOP FIRST BrokerConnectionError: {exc}")
        print(traceback.format_exc())
    except Exception as exc:
        print(f"[{now()}] STOP FIRST non-BrokerConnectionError: {type(exc).__name__}: {exc}")
        print(traceback.format_exc())
    finally:
        restore_urlopen()
        for obj, attr, orig in reversed(originals):
            setattr(obj, attr, orig)


if __name__ == "__main__":
    main()
