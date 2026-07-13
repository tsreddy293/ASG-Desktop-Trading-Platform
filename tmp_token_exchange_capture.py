import json
from urllib.error import HTTPError

from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
import src.brokers.fivepaisa.auth_service as auth_module


def _mask(value: str) -> str:
    text = str(value or "")
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


service = FivePaisaAuthService()
request_token = service._dotenv_values.get("FIVEPAISA_REQUEST_TOKEN", "").strip()
original_urlopen = auth_module.urlopen
captured = {}


def wrapped_urlopen(req, timeout=20):
    captured["endpoint"] = req.full_url
    captured["method"] = req.get_method()
    captured["request_headers"] = dict(req.header_items())
    raw_body = req.data.decode("utf-8", errors="replace") if getattr(req, "data", None) else ""
    try:
        parsed_body = json.loads(raw_body) if raw_body else {}
    except Exception:
        parsed_body = raw_body
    if isinstance(parsed_body, dict):
        masked_body = json.loads(json.dumps(parsed_body))
        try:
            masked_body["head"]["Key"] = _mask(masked_body["head"].get("Key", ""))
        except Exception:
            pass
        try:
            masked_body["body"]["RequestToken"] = _mask(masked_body["body"].get("RequestToken", ""))
        except Exception:
            pass
        try:
            masked_body["body"]["EncryKey"] = _mask(masked_body["body"].get("EncryKey", ""))
        except Exception:
            pass
        try:
            masked_body["body"]["UserId"] = _mask(masked_body["body"].get("UserId", ""))
        except Exception:
            pass
        captured["request_body_masked"] = json.dumps(masked_body, separators=(",", ":"))
    else:
        captured["request_body_masked"] = raw_body

    try:
        response = original_urlopen(req, timeout=timeout)
        status_code = getattr(response, "status", None) or response.getcode()
        response_headers = dict(response.headers.items())
        response_body = response.read().decode("utf-8", errors="replace")
        captured["http_status"] = status_code
        captured["response_headers"] = response_headers
        captured["response_body"] = response_body

        class _ResponseProxy:
            status = status_code
            headers = response.headers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return response_body.encode("utf-8")

            def getcode(self):
                return status_code

        return _ResponseProxy()
    except HTTPError as exc:
        captured["http_status"] = exc.code
        captured["response_headers"] = dict(exc.headers.items()) if exc.headers else {}
        try:
            captured["response_body"] = exc.read().decode("utf-8", errors="replace")
        except Exception:
            captured["response_body"] = ""
        raise


auth_module.urlopen = wrapped_urlopen

try:
    service.exchange_request_token(request_token)
except Exception:
    pass

print("HTTP_STATUS_CODE:")
print(captured.get("http_status"))
print("RESPONSE_HEADERS:")
print(json.dumps(captured.get("response_headers", {}), indent=2, sort_keys=True))
print("FULL_JSON_RESPONSE_BODY:")
print(captured.get("response_body"))
print("STATUS_VALUE:")
try:
    parsed = json.loads(captured.get("response_body") or "{}")
    body = parsed.get("body", parsed)
except Exception:
    body = {}
print(body.get("Status"))
print("MESSAGE_VALUE:")
print(body.get("Message"))
print("ACCESSTOKEN_VALUE:")
print(body.get("AccessToken"))
print("REFRESHTOKEN_VALUE:")
print(body.get("RefreshToken"))
print("ENDPOINT:")
print(captured.get("endpoint"))
print("HTTP_METHOD:")
print(captured.get("method"))
print("REQUEST_HEADERS:")
print(json.dumps(captured.get("request_headers", {}), indent=2, sort_keys=True))
print("REQUEST_PAYLOAD_MASKED:")
print(captured.get("request_body_masked"))
