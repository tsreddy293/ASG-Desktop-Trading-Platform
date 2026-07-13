import base64
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QTimer

from src.app import create_app
from src.brokers import broker_manager
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
import src.brokers.fivepaisa.auth_service as auth_module
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient

OUT = Path("d:/Projects/ASG/logs/outbound_http_audit.json")

result = {
    "url": None,
    "headers": None,
    "request_body": None,
    "http_status": None,
    "raw_json_response": None,
    "callback_ts_ms": None,
    "post_ts_ms": None,
    "elapsed_ms": None,
    "local_system_time": None,
    "jwt_iat": None,
    "jwt_exp": None,
}


def _mask(v: str) -> str:
    s = "" if v is None else str(v)
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "..." + s[-4:]


def _decode_jwt_times(token: str):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        return payload.get("iat"), payload.get("exp")
    except Exception:
        return None, None


orig_build = FivePaisaBrokerClient._build_callback_handler
orig_urlopen = auth_module.urlopen


def wrapped_build(self, state, host, port, callback_path):
    handler = orig_build(self, state, host, port, callback_path)
    orig_do_get = handler.do_GET

    def audited_do_get(handler_self):
        parsed = urlparse(handler_self.path)
        if parsed.path == callback_path:
            params = parse_qs(parsed.query)
            token_values = params.get("RequestToken", [])
            token = token_values[0].strip() if token_values else ""
            result["callback_ts_ms"] = int(time.time() * 1000)
            iat, exp = _decode_jwt_times(token)
            result["jwt_iat"] = iat
            result["jwt_exp"] = exp
            OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return orig_do_get(handler_self)

    handler.do_GET = audited_do_get
    return handler


def wrapped_urlopen(req, timeout=20):
    result["post_ts_ms"] = int(time.time() * 1000)
    result["url"] = req.full_url
    result["headers"] = dict(req.header_items())

    raw_body = req.data.decode("utf-8", errors="replace") if getattr(req, "data", None) else ""
    try:
        body = json.loads(raw_body) if raw_body else {}
    except Exception:
        body = raw_body

    if isinstance(body, dict):
        masked = json.loads(json.dumps(body))
        if isinstance(masked.get("head"), dict) and "Key" in masked["head"]:
            masked["head"]["Key"] = _mask(masked["head"]["Key"])
        if isinstance(masked.get("body"), dict) and "EncryKey" in masked["body"]:
            masked["body"]["EncryKey"] = _mask(masked["body"]["EncryKey"])
        result["request_body"] = masked
    else:
        result["request_body"] = body

    try:
        resp = orig_urlopen(req, timeout=timeout)
        result["http_status"] = getattr(resp, "status", None) or resp.getcode()
        raw = resp.read().decode("utf-8", errors="replace")
        result["raw_json_response"] = raw

        class _Resp:
            status = result["http_status"]
            headers = getattr(resp, "headers", {})

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return raw.encode("utf-8")

            def getcode(self):
                return self.status

        return _Resp()
    except HTTPError as exc:
        result["http_status"] = exc.code
        try:
            result["raw_json_response"] = exc.read().decode("utf-8", errors="replace")
        except Exception:
            result["raw_json_response"] = ""
        raise


FivePaisaBrokerClient._build_callback_handler = wrapped_build
auth_module.urlopen = wrapped_urlopen

app = create_app()


def trigger_connect():
    try:
        broker_manager.connect()
    except Exception:
        pass


QTimer.singleShot(3000, trigger_connect)
QTimer.singleShot(130000, app.app.quit)
app.run()

result["local_system_time"] = datetime.now().astimezone().isoformat()
if isinstance(result["callback_ts_ms"], int) and isinstance(result["post_ts_ms"], int):
    result["elapsed_ms"] = result["post_ts_ms"] - result["callback_ts_ms"]

OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
