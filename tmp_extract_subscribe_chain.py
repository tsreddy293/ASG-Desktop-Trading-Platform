from __future__ import annotations

import json
from pathlib import Path

src = Path("tmp_subscribe_chain_trace_output.json")
raw = src.read_bytes()
text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8", errors="replace")
decoder = json.JSONDecoder()
data, _end = decoder.raw_decode(text.lstrip("\ufeff\r\n\t "))

lines = []
lines.append(f"stop_reason={data.get('stop_reason')}")
lines.append(f"exception={data.get('exception')}")
lines.append("flags=")
for k in [
    "WebSocketService.started",
    "WebSocketClient.connected",
    "MarketDataEngine.running",
    "MarketDataService.running",
]:
    lines.append(f"{k}={data.get(k)}")
lines.append("branches=")
for b in data.get("branches", []):
    lines.append(
        f"{b.get('file')}|{b.get('line')}|{b.get('function')}|condition={b.get('condition')}|evaluated={b.get('evaluated_value')}|branch_skipped={b.get('branch_skipped')}"
    )
lines.append("steps=")
for s in data.get("steps", []):
    exc = s.get("exception")
    exc_text = "None" if exc is None else f"{exc.get('type')}:{exc.get('message')}"
    lines.append(
        f"{s.get('file')}|{s.get('line')}|{s.get('function')}|entered={s.get('entered')}|exited={s.get('exited')}|return_value={s.get('return_value')}|exception={exc_text}"
    )

Path("tmp_subscribe_chain_trace_compact.txt").write_text("\n".join(lines), encoding="utf-8")
print("wrote tmp_subscribe_chain_trace_compact.txt")
