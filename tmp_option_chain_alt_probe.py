from __future__ import annotations

import json
import traceback
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.brokers.broker_manager import BrokerManager


def req(method: str, url: str, headers: dict, body: dict | None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    r = Request(url=url, data=data, headers=headers, method=method)
    try:
        with urlopen(r, timeout=20) as resp:
            return {
                "ok": True,
                "status": getattr(resp, "status", None),
                "final_url": resp.geturl(),
                "headers": str(resp.headers),
                "body": resp.read().decode("utf-8", errors="replace"),
            }
    except Exception as exc:
        body_text = ""
        hdr = ""
        code = None
        final_url = url
        try:
            code = getattr(exc, "code", None)
            hdr = str(getattr(exc, "headers", ""))
            final_url = exc.geturl()
            body_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "status": code,
            "final_url": final_url,
            "headers": hdr,
            "body": body_text,
            "traceback": traceback.format_exc(),
        }


def main():
    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")
    manager.connect()

    broker = manager.active_broker()
    sm = broker._login_service._broker_client.session_manager
    token = sm.get_access_token()
    api_key = broker._market._market_data._api_key

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["x-clientcode"] = api_key

    out = {}

    # Current app endpoint
    app_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/OptionChain?" + urlencode({"Symbol": "NIFTY", "Expiry": "31 Jul 2026"})
    out["current_get_optionchain"] = req("GET", app_url, headers, None)

    # py5paisa documented route pattern
    alt_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/GetOptionsForSymbol"
    out["alt_post_getoptionsforsymbol"] = req(
        "POST",
        alt_url,
        headers,
        {
            "head": {"key": api_key} if api_key else {},
            "body": {"Exch": "N", "Symbol": "NIFTY", "ExpiryDate": "/Date(1785456000000)/"},
        },
    )

    exp_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V2/GetExpiryForSymbolOptions"
    out["alt_post_getexpiry"] = req(
        "POST",
        exp_url,
        headers,
        {
            "head": {"key": api_key} if api_key else {},
            "body": {"Exch": "N", "Symbol": "NIFTY"},
        },
    )

    # Mask token lengths only
    out["auth"] = {
        "authorization_len": len(headers.get("Authorization", "")),
        "x_clientcode_len": len(headers.get("x-clientcode", "")),
    }

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
