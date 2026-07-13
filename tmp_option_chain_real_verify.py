from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError

from src.brokers.broker_manager import BrokerManager


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]
    out: dict[str, object] = {
        "timestamp": now(),
        "connect": {"ok": False},
        "symbols": {},
    }

    manager = BrokerManager()
    manager.set_active_broker("fivepaisa")

    try:
        manager.connect()
        out["connect"] = {"ok": True}
    except Exception as exc:
        out["connect"] = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}
        print(json.dumps(out, indent=2))
        return

    broker = manager.active_broker()
    market_data = broker._market._market_data

    import src.brokers.fivepaisa.market_data_service as md_mod

    original_urlopen = md_mod.urlopen
    request_log: list[dict[str, object]] = []

    def traced_urlopen(request, timeout=20):
        record = {
            "url": getattr(request, "full_url", ""),
            "method": getattr(request, "method", "GET"),
            "status": None,
        }
        try:
            resp = original_urlopen(request, timeout=timeout)
            status = getattr(resp, "status", None)
            if status is None:
                try:
                    status = resp.getcode()
                except Exception:
                    status = None
            record["status"] = status
            request_log.append(record)
            return resp
        except HTTPError as exc:
            record["status"] = getattr(exc, "code", None)
            request_log.append(record)
            raise

    md_mod.urlopen = traced_urlopen

    try:
        for symbol in symbols:
            symbol_logs_start = len(request_log)
            result: dict[str, object] = {
                "ok": False,
                "http_status": [],
                "number_of_expiries": 0,
                "number_of_strikes": 0,
                "sample_ce": {},
                "sample_pe": {},
            }
            try:
                payload = market_data.get_option_chain(symbol, expiry=None)
                result["ok"] = True
                expiries = payload.get("expiries", []) if isinstance(payload, dict) else []
                rows = payload.get("rows", []) if isinstance(payload, dict) else []
                result["number_of_expiries"] = len(expiries) if isinstance(expiries, list) else 0
                result["number_of_strikes"] = len(rows) if isinstance(rows, list) else 0

                sample_row = {}
                if isinstance(rows, list) and rows:
                    sample_row = max(
                        (row for row in rows if isinstance(row, dict)),
                        key=lambda row: float(row.get("ce_oi", 0) or 0)
                        + float(row.get("pe_oi", 0) or 0)
                        + float(row.get("ce_ltp", 0.0) or 0.0)
                        + float(row.get("pe_ltp", 0.0) or 0.0),
                        default=rows[0],
                    )
                if isinstance(sample_row, dict):
                    result["sample_ce"] = {
                        "ltp": sample_row.get("ce_ltp", 0.0),
                        "oi": sample_row.get("ce_oi", 0),
                        "volume": sample_row.get("ce_volume", 0),
                        "iv": sample_row.get("ce_iv", sample_row.get("iv", 0.0)),
                        "bid": sample_row.get("ce_bid", 0.0),
                        "ask": sample_row.get("ce_ask", 0.0),
                        "delta": sample_row.get("ce_delta", 0.0),
                        "gamma": sample_row.get("ce_gamma", 0.0),
                        "theta": sample_row.get("ce_theta", 0.0),
                        "vega": sample_row.get("ce_vega", 0.0),
                        "rho": sample_row.get("ce_rho", 0.0),
                    }
                    result["sample_pe"] = {
                        "ltp": sample_row.get("pe_ltp", 0.0),
                        "oi": sample_row.get("pe_oi", 0),
                        "volume": sample_row.get("pe_volume", 0),
                        "iv": sample_row.get("pe_iv", sample_row.get("iv", 0.0)),
                        "bid": sample_row.get("pe_bid", 0.0),
                        "ask": sample_row.get("pe_ask", 0.0),
                        "delta": sample_row.get("pe_delta", 0.0),
                        "gamma": sample_row.get("pe_gamma", 0.0),
                        "theta": sample_row.get("pe_theta", 0.0),
                        "vega": sample_row.get("pe_vega", 0.0),
                        "rho": sample_row.get("pe_rho", 0.0),
                    }
            except Exception as exc:
                result["error_type"] = type(exc).__name__
                result["error"] = str(exc)

            symbol_logs = request_log[symbol_logs_start:]
            result["http_status"] = [
                {
                    "method": item.get("method"),
                    "url": item.get("url"),
                    "status": item.get("status"),
                }
                for item in symbol_logs
            ]
            out["symbols"][symbol] = result
    finally:
        md_mod.urlopen = original_urlopen

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
