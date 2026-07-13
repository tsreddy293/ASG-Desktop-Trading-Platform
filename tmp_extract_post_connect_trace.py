from __future__ import annotations

import json
from pathlib import Path

src = Path("tmp_post_connect_startup_trace_output.json")
raw = src.read_bytes()

if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
    text = raw.decode("utf-16")
else:
    text = raw.decode("utf-8", errors="replace")

data = json.loads(text)

lines = []
lines.append(f"connect_success={data.get('connect_success')}")
lines.append(f"connect_bypassed={data.get('connect_bypassed')}")
lines.append(f"connect_exception={data.get('connect_exception')}")
lines.append(f"stop_reason={data.get('stop_reason')}")
lines.append("states=")
for k, v in data.get("states", {}).items():
    lines.append(f"{k}={v}")

lines.append("execution_chain=")
for r in data.get("records", []):
    exc = r.get("exception")
    exc_text = "None" if exc is None else f"{exc.get('type')}:{exc.get('message')}"
    lines.append(
        f"{r.get('file')}|{r.get('line')}|{r.get('function_name')}|entered={r.get('entered')}|exited={r.get('exited')}|exception={exc_text}"
    )

Path("tmp_post_connect_startup_trace_compact.txt").write_text("\n".join(lines), encoding="utf-8")
print("wrote tmp_post_connect_startup_trace_compact.txt")
