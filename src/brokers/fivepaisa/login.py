from __future__ import annotations

import inspect
import threading
import traceback
from datetime import datetime, timezone

from src.brokers.base_broker import BrokerConnectionError, BrokerNotLoggedIn
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.core.logger import app_logger


class FivePaisaLoginService:
    """Compatibility login service backed by new XStream client/session flow."""

    _login_trace_lock = threading.Lock()

    def __init__(self) -> None:
        self._broker_client = FivePaisaBrokerClient()
        self._client = None

    def login(self) -> None:
        stack = inspect.stack(context=0)
        frame = stack[1] if len(stack) > 1 else stack[0]
        with self._login_trace_lock:
            current = getattr(self, "_login_call_sequence", 0) + 1
            self._login_call_sequence = current
        app_logger.info(
            f"AUTH_PROBE event=FivePaisaLoginService.login seq={current} ts={datetime.now(timezone.utc).isoformat()} "
            f"thread={threading.current_thread().name} caller_file={frame.filename} caller_line={frame.lineno}\n"
            f"{''.join(traceback.format_stack(limit=10))}"
        )
        if self._broker_client.authentication_in_progress():
            app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
            return
        app_logger.info(f"AUTH_STACK label=login_entered\n{''.join(traceback.format_stack(limit=10))}")
        # Auto-authenticates via OAuth callback flow when no valid session exists.
        self._broker_client.ensure_authenticated()
        app_logger.info("5paisa session validated")

    def logout(self) -> None:
        self._broker_client.logout()
        self._client = None

    def is_logged_in(self) -> bool:
        return self._broker_client.is_authenticated()

    def login_url(self) -> str:
        return self._broker_client.generate_login_url()

    def authenticate_callback(self, callback_url: str) -> None:
        self._broker_client.authenticate_from_callback(callback_url)

    def client(self):
        if not self._broker_client.is_authenticated():
            raise BrokerNotLoggedIn("Session expired. Please click Connect.")
        raise BrokerConnectionError("Broker connection unavailable.")
