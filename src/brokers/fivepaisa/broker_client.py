from __future__ import annotations

from dataclasses import dataclass
import os
import inspect
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Lock, Thread
from urllib.parse import parse_qs, urlparse
import webbrowser
import traceback
import threading
from datetime import datetime, timezone

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
from src.brokers.fivepaisa.session_manager import BrokerSession, FivePaisaSessionManager
from src.core.logger import app_logger


@dataclass(slots=True)
class AuthResult:
    access_token: str
    refresh_token: str
    client_code: str
    status: str


@dataclass(slots=True)
class _OAuthCallbackState:
    event: Event
    request_token: str = ""
    callback_url: str = ""
    server: HTTPServer | None = None
    authenticated: bool = False
    auth_error: str = ""
    completed: bool = False


class FivePaisaBrokerClient:
    """High-level 5paisa XStream OAuth client orchestration."""

    def __init__(
        self,
        auth_service: FivePaisaAuthService | None = None,
        session_manager: FivePaisaSessionManager | None = None,
    ) -> None:
        self._auth_service = auth_service or FivePaisaAuthService()
        self._session_manager = session_manager or FivePaisaSessionManager()
        self._auth_lock = Lock()
        self._authentication_in_progress = False

    def authentication_in_progress(self) -> bool:
        return bool(self._authentication_in_progress)

    def _trace_auth_event(self, event_name: str) -> None:
        stack = inspect.stack(context=0)
        frame = stack[2] if len(stack) > 2 else stack[1]
        timer_state = {
            "validator_thread_alive": bool(getattr(self._session_manager, "_validator_thread", None) and getattr(self._session_manager, "_validator_thread", None).is_alive()),
            "stop_event": bool(getattr(self._session_manager, "_stop_event", None) and getattr(self._session_manager, "_stop_event", None).is_set()),
            "reconnect_interrupt": bool(getattr(self._session_manager, "_reconnect_interrupt", None) and getattr(self._session_manager, "_reconnect_interrupt", None).is_set()),
        }
        app_logger.info(
            f"AUTH_TRACE event={event_name} ts={datetime.now(timezone.utc).isoformat()} thread={threading.current_thread().name} "
            f"caller={frame.function} file={frame.filename} line={frame.lineno} session_state={self._session_manager.state().value} "
            f"auth_in_progress={self._authentication_in_progress} reconnect_timer={timer_state}"
        )

    def _trace_stack(self, label: str) -> None:
        app_logger.info(f"AUTH_STACK label={label}\n{''.join(traceback.format_stack())}")

    def _probe(self, event_name: str) -> None:
        stack = inspect.stack(context=0)
        frame = stack[2] if len(stack) > 2 else stack[1]
        current = getattr(self, "_auth_probe_sequence", 0) + 1
        self._auth_probe_sequence = current
        app_logger.info(
            f"AUTH_PROBE event={event_name} seq={current} ts={datetime.now(timezone.utc).isoformat()} "
            f"thread={threading.current_thread().name} caller_file={frame.filename} caller_line={frame.lineno}\n"
            f"{''.join(traceback.format_stack(limit=10))}"
        )

    def generate_login_url(self) -> str:
        return self._auth_service.generate_login_url()

    def authenticate_from_callback(self, callback_url: str) -> AuthResult:
        self._probe("broker_client.authenticate")
        self._probe("request_token.handle.callback_url")
        self._trace_auth_event("broker_client.authenticate")
        self._session_manager.mark_connecting()
        request_token = self._auth_service.extract_request_token(callback_url)
        self._probe("request_token.extracted")
        token_response = self._auth_service.exchange_request_token(request_token)
        self._session_manager.set_session(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
            user_id=os.getenv("FIVEPAISA_USER_ID", "").strip(),
        )
        app_logger.info("Login successful")
        return AuthResult(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
        )

    def reauthenticate_from_request_token(self, request_token: str) -> AuthResult:
        self._probe("broker_client.authenticate")
        self._probe("request_token.handle.reauthenticate")
        self._trace_auth_event("broker_client.authenticate")
        self._session_manager.mark_connecting()
        token_response = self._auth_service.exchange_request_token(request_token)
        self._session_manager.set_session(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
            user_id=os.getenv("FIVEPAISA_USER_ID", "").strip(),
        )
        app_logger.info("Access Token generated")
        app_logger.info("Login successful")
        return AuthResult(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
        )

    def try_reauthenticate_from_env(self) -> bool:
        self._probe("request_token.handle.env")
        self._trace_auth_event("broker_client.authenticate")
        request_token = os.getenv("FIVEPAISA_REQUEST_TOKEN", "").strip()
        if not request_token:
            return False
        self.reauthenticate_from_request_token(request_token)
        return True

    def ensure_authenticated(self) -> BrokerSession:
        self._probe("broker_client.connect")
        self._trace_auth_event("broker_client.ensure_authenticated")
        if self._session_manager.state().value == "Connected":
            app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
            return self._session_manager.require_valid_session()

        session = self._session_manager.get_session()
        if session is not None and not self._session_manager.needs_refresh():
            app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
            return self._session_manager.require_valid_session()

        with self._auth_lock:
            session = self._session_manager.get_session()
            if session is not None and not self._session_manager.needs_refresh():
                app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
                return self._session_manager.require_valid_session()

            if self._authentication_in_progress:
                app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
                return self._session_manager.require_valid_session()

            app_logger.warning("5paisa access token expired or missing; connect required")
            self._session_manager.mark_connecting()
            try:
                self._authentication_in_progress = True
                self._authenticate_via_oauth_flow()
            except Exception:
                self._session_manager.clear()
                raise
            finally:
                self._authentication_in_progress = False
            return self._session_manager.require_valid_session()

    def logout(self) -> None:
        self._session_manager.clear()

    def is_authenticated(self) -> bool:
        try:
            return not self._session_manager.needs_refresh()
        except Exception:
            return False

    @property
    def session_manager(self) -> FivePaisaSessionManager:
        return self._session_manager

    def _authenticate_via_oauth_flow(self) -> None:
        self._probe("broker_client._authenticate_via_oauth_flow")
        self._probe("broker_client.connect")
        self._trace_auth_event("broker_client.connect")
        if self._authentication_in_progress is False:
            self._authentication_in_progress = True

        if self._session_manager.state().value == "Connected":
            app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
            return

        session = self._session_manager.get_session()
        if session is not None and not self._session_manager.needs_refresh():
            app_logger.info("LOGIN_SKIPPED_ALREADY_CONNECTED")
            return

        login_url = self.generate_login_url()
        callback_url = self._extract_callback_url(login_url)

        parsed = urlparse(callback_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        callback_path = parsed.path or "/callback"

        state = _OAuthCallbackState(event=Event())
        handler = self._build_callback_handler(state, host, port, callback_path)
        try:
            server = HTTPServer((host, port), handler)
        except OSError as exc:
            raise BrokerConnectionError("Broker connection unavailable.") from exc
        state.server = server

        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        app_logger.info("LOGIN_STARTED")
        app_logger.info(f"5paisa callback server listening on http://{host}:{port}{callback_path}")
        self._probe("browser.open")
        webbrowser.open(login_url, new=2)
        app_logger.info("Waiting for 5paisa OAuth callback")

        try:
            if not state.event.wait(timeout=300):
                raise BrokerConnectionError("Broker connection unavailable.")
            if state.auth_error:
                self._session_manager.clear()
                raise BrokerConnectionError("Broker connection unavailable.")
            if state.authenticated:
                self._authentication_in_progress = False
                return
            if not state.request_token:
                self._session_manager.clear()
                raise BrokerConnectionError("Broker connection unavailable.")
            self.reauthenticate_from_request_token(state.request_token)
            self._authentication_in_progress = False
        finally:
            try:
                server.shutdown()
            except Exception:
                pass
            server.server_close()

    def _is_session_reachable(self) -> bool:
        session = self._session_manager.get_session()
        if session is None:
            return False
        return not self._session_manager.needs_refresh()

    @staticmethod
    def _extract_callback_url(login_url: str) -> str:
        parsed = urlparse(login_url)
        query = parse_qs(parsed.query)
        response = query.get("ResponseURL", [""])
        callback_url = (response[0] or "").strip()
        if not callback_url:
            raise BrokerConnectionError("Broker connection unavailable.")
        return callback_url

    def _build_callback_handler(self, state: _OAuthCallbackState, host: str, port: int, callback_path: str):
        class _CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                self._outer_client._probe("oauth.callback")  # type: ignore[attr-defined]
                parsed = urlparse(self.path)
                if parsed.path != callback_path:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    return

                params = parse_qs(parsed.query)
                token_values = params.get("RequestToken", [])
                token = token_values[0].strip() if token_values else ""
                if token:
                    self._outer_client._probe("request_token.handle.callback")  # type: ignore[attr-defined]
                    app_logger.info("CALLBACK_RECEIVED")
                    state.request_token = token
                    state.callback_url = f"http://{host}:{port}{callback_path}?{parsed.query}"
                    if not state.completed:
                        try:
                            self._outer_client._trace_auth_event("callback_exchange")  # type: ignore[attr-defined]
                            self._outer_client.reauthenticate_from_request_token(token)  # type: ignore[attr-defined]
                            state.authenticated = True
                            app_logger.info("TOKEN_EXCHANGED")
                            app_logger.info("SESSION_CONNECTED")
                        except Exception as exc:
                            state.auth_error = str(exc)
                        finally:
                            state.completed = True
                    state.event.set()

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    (
                        "<html>"
                        "<body>"
                        "<h2>Login Successful</h2>"
                        "You may close this browser."
                        "</body>"
                        "</html>"
                    ).encode("utf-8")
                )

                if token and state.server is not None:
                    Thread(target=state.server.shutdown, daemon=True).start()

            def log_message(self, fmt: str, *args) -> None:
                return

        _CallbackHandler._outer_client = self
        return _CallbackHandler
