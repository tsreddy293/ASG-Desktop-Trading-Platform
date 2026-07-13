from __future__ import annotations

import json
from pathlib import Path

src = Path("tmp_session_manager_lifecycle_trace_output.json")
raw = src.read_bytes()
text = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8", errors="replace")

decoder = json.JSONDecoder()
data, _ = decoder.raw_decode(text.lstrip("\ufeff\r\n\t "))

lines = []
lines.append("instances_created=")
for i in data.get("instances_created", []):
    lines.append(f"id(self)={i.get('id(self)')}|file={i.get('file')}|line={i.get('line')}|caller={i.get('caller')}")

lines.append("calls=")
for c in data.get("calls", []):
    lines.append(
        f"method={c.get('method')}|id(self)={c.get('id(self)')}|session_object_id={c.get('session_object_id')}|access_token_length={c.get('access_token_length')}|session_state={c.get('session_state')}|return_value={c.get('return_value')}"
    )

Path("tmp_session_manager_lifecycle_trace_compact.txt").write_text("\n".join(lines), encoding="utf-8")
print("wrote tmp_session_manager_lifecycle_trace_compact.txt")
