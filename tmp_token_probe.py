from urllib.error import HTTPError

from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
import src.brokers.fivepaisa.auth_service as auth_module

service = FivePaisaAuthService()
request_token = service._dotenv_values.get("FIVEPAISA_REQUEST_TOKEN", "").strip()

captured = {}
original_urlopen = auth_module.urlopen


def wrapped_urlopen(req, timeout=20):
    captured["url"] = req.full_url
    captured["method"] = req.get_method()
    captured["headers"] = dict(req.header_items())
    captured["body"] = req.data.decode("utf-8", errors="replace") if getattr(req, "data", None) else ""

    try:
        response = original_urlopen(req, timeout=timeout)
        status_code = getattr(response, "status", None) or response.getcode()
        raw = response.read().decode("utf-8", errors="replace")
        captured["http_status"] = status_code
        captured["response_body"] = raw

        class _ResponseProxy:
            status = status_code

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return raw.encode("utf-8")

        return _ResponseProxy()
    except HTTPError as exc:
        captured["http_status"] = exc.code
        try:
            captured["response_body"] = exc.read().decode("utf-8", errors="replace")
        except Exception:
            captured["response_body"] = ""
        raise
    except Exception as exc:
        captured["exception"] = repr(exc)
        raise


auth_module.urlopen = wrapped_urlopen

try:
    service.exchange_request_token(request_token)
    captured["result"] = "success"
except Exception as exc:
    captured["result"] = f"{type(exc).__name__}: {exc}"

print("URL=", captured.get("url"))
print("METHOD=", captured.get("method"))
print("HEADERS=", captured.get("headers"))
print("BODY=", captured.get("body"))
print("HTTP_STATUS=", captured.get("http_status"))
print("RESPONSE_BODY=", captured.get("response_body"))
print("EXCEPTION=", captured.get("result"))
