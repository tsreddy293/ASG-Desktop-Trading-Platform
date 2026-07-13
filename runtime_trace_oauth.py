import functools
import inspect
import threading
import traceback
import webbrowser
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QTimer


TRACE_FILE = Path("d:/Projects/ASG/logs/runtime_stack_calls.txt")
TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
TRACE_FILE.write_text("", encoding="utf-8")


def _dump(label: str) -> None:
    stack = inspect.stack()
    caller = stack[2] if len(stack) > 2 else stack[1]
    block = "\n".join(
        [
            "========================",
            f"TS: {datetime.now().isoformat()}",
            f"INSTRUMENTED CALL: {label}",
            f"CURRENT THREAD: {threading.current_thread().name}",
            "FULL PYTHON STACK TRACE",
            "".join(traceback.format_stack()),
            f"CALLER FUNCTION: {caller.function}",
            f"CALLER FILE: {caller.filename}",
            f"CALLER LINE: {caller.lineno}",
            "========================",
            "",
        ]
    )
    print(block, flush=True)
    with TRACE_FILE.open("a", encoding="utf-8") as handle:
        handle.write(block)


def _patch(owner, name: str, label: str) -> None:
    original = getattr(owner, name)

    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        _dump(label)
        return original(*args, **kwargs)

    setattr(owner, name, wrapped)


from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.login import FivePaisaLoginService
from src.brokers.broker_manager import BrokerManager
from src.brokers import broker_manager

_patch(webbrowser, "open", "webbrowser.open")
_patch(FivePaisaBrokerClient, "_authenticate_via_oauth_flow", "FivePaisaBrokerClient._authenticate_via_oauth_flow")
_patch(FivePaisaBrokerClient, "ensure_authenticated", "FivePaisaBrokerClient.ensure_authenticated")
_patch(FivePaisaLoginService, "login", "FivePaisaLoginService.login")
_patch(BrokerManager, "login", "BrokerManager.login")

from src.app import create_app

app = create_app()


def _trigger_connect() -> None:
    _dump("runtime_trace.trigger_connect")
    try:
        broker_manager.connect()
    except Exception:
        print(traceback.format_exc(), flush=True)


QTimer.singleShot(6000, _trigger_connect)
raise SystemExit(app.run())
