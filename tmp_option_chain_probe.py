from __future__ import annotations

import json
import socket
import traceback
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse

from src.brokers.broker_manager import BrokerManager


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_secret_value(key: str, value: Any) -> Any:
    key_l = key.lower()
    if key_l in {"authorization", "accesstoken", "refreshtoken", "requesttoken", "encrykey", "key", "x-clientcode"}:
        text = str(value or "")
        return f"***MASKED(len={len(text)})***"
    return value


def mask_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = mask_dict(v)
        elif isinstance(v, list):
            out[k] = [mask_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = mask_secret_value(str(k), v)
    return out


def main() -> None:
    out: dict[str, Any] = {
        "timestamp": now(),
        "connect": {},
        "request": {},
        "dns": {},
        "response": {},
        "exception": None,
    }

    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")

    connect_ok = False
    try:
        manager.connect()
        connect_ok = True
        out["connect"] = {"ok": True}
    except Exception as exc:
        out["connect"] = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    if not connect_ok:
        print(json.dumps(out, indent=2))
        return

    broker = manager.active_broker()
    market_data = broker._market._market_data

    import src.brokers.fivepaisa.market_data_service as md_mod

    original_urlopen = md_mod.urlopen

    def traced_urlopen(request, timeout=20):
        url = getattr(request, "full_url", "")
        method = getattr(request, "method", "GET")
        headers = dict(getattr(request, "headers", {}) or {})
        body_raw = getattr(request, "data", None)
        body_text = None
        if body_raw is not None:
            try:
                body_text = body_raw.decode("utf-8", errors="replace")
            except Exception:
                body_text = str(body_raw)

        parsed = urlparse(url)
        out["request"] = {
            "url": url,
            "method": method,
            "headers": mask_dict(headers),
            "body": body_text,
            "hostname": parsed.hostname,
        }

        # DNS resolution from client side
        try:
            host = parsed.hostname or ""
            infos = socket.getaddrinfo(host, parsed.port or 443)
            addrs = []
            for info in infos:
                sockaddr = info[4]
                if sockaddr and isinstance(sockaddr, tuple):
                    addrs.append(sockaddr[0])
            out["dns"] = {
                "hostname": host,
                "resolved_addresses": sorted(list(set(addrs))),
            }
        except Exception as dns_exc:
            out["dns"] = {
                "hostname": parsed.hostname,
                "error_type": type(dns_exc).__name__,
                "error": str(dns_exc),
                "traceback": traceback.format_exc(),
            }

        try:
            resp = original_urlopen(request, timeout=timeout)
            body_bytes = resp.read()
            body = body_bytes.decode("utf-8", errors="replace")
            status = getattr(resp, "status", None)
            if status is None:
                try:
                    status = resp.getcode()
                except Exception:
                    status = None
            headers_raw = str(getattr(resp, "headers", ""))
            final_url = ""
            try:
                final_url = resp.geturl()
            except Exception:
                final_url = url

            out["response"] = {
                "status": status,
                "final_url": final_url,
                "headers": headers_raw,
                "body": body,
            }

            class _ResponseProxy:
                def __init__(self, status_code, body_data, headers_obj, final):
                    self.status = status_code
                    self._body = body_data
                    self.headers = headers_obj
                    self._url = final

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return self._body

                def getcode(self):
                    return self.status

                def geturl(self):
                    return self._url

            return _ResponseProxy(status, body_bytes, resp.headers, final_url)
        except HTTPError as exc:
            err_body = ""
            try:
                if exc.fp is not None:
                    err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            final_url = ""
            try:
                final_url = exc.geturl()
            except Exception:
                final_url = url
            out["response"] = {
                "status": getattr(exc, "code", None),
                "final_url": final_url,
                "headers": str(getattr(exc, "headers", "")),
                "body": err_body,
            }
            out["exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            raise
        except Exception as exc:
            out["exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            raise

    md_mod.urlopen = traced_urlopen

    try:
        # Real API call path; no stubs.
        _ = market_data.get_option_chain("NIFTY", expiry="31 Jul 2026")
    except Exception:
        pass
    finally:
        md_mod.urlopen = original_urlopen

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
