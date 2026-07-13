from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen

from src.brokers.broker_manager import BrokerManager


def post(url: str, headers: dict[str, str], body: dict) -> dict:
    req = Request(url=url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")
    manager.connect()
    broker = manager.active_broker()

    md = broker._market._market_data
    sm = broker._login_service._broker_client.session_manager
    session = sm.require_valid_session()

    headers = {
        "Authorization": f"Bearer {session.access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if md._api_key:
        headers["x-clientcode"] = md._api_key

    exp = post(
        "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/V2/GetExpiryForSymbolOptions",
        headers,
        {"head": {"key": md._api_key}, "body": {"Exch": "N", "Symbol": "NIFTY", "ClientCode": session.client_code}},
    )
    expiry_list = exp.get("body", {}).get("Expiry", [])
    first_exp = expiry_list[0]["ExpiryDate"]
    match = re.search(r"/Date\((\d+)", str(first_exp))
    first_exp_norm = f"/Date({match.group(1)})/" if match else str(first_exp)

    opt = post(
        "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/GetOptionsForSymbol",
        headers,
        {
            "head": {"key": md._api_key},
            "body": {"Exch": "N", "Symbol": "NIFTY", "ExpiryDate": first_exp_norm, "ClientCode": session.client_code},
        },
    )

    body = opt.get("body", {})
    options = body.get("Options", [])
    sample = options[0] if options else {}

    print(json.dumps({
        "expiry_count": len(expiry_list),
        "options_count": len(options),
        "sample_keys": sorted(list(sample.keys())) if isinstance(sample, dict) else [],
        "sample": sample,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
