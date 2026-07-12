from __future__ import annotations

from dataclasses import dataclass
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Lock, Thread
from urllib.parse import parse_qs, urlparse
import webbrowser

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

    def generate_login_url(self) -> str:
        return self._auth_service.generate_login_url()

    def authenticate_from_callback(self, callback_url: str) -> AuthResult:
        request_token = self._auth_service.extract_request_token(callback_url)
        token_response = self._auth_service.exchange_request_token(request_token)
        self._session_manager.set_session(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
        )
        app_logger.info("Login successful")
        return AuthResult(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
        )

    def reauthenticate_from_request_token(self, request_token: str) -> AuthResult:
        token_response = self._auth_service.exchange_request_token(request_token)
        self._session_manager.set_session(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            client_code=token_response.client_code,
            status=token_response.status,
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
        request_token = os.getenv("FIVEPAISA_REQUEST_TOKEN", "").strip()
        if not request_token:
            return False
        self.reauthenticate_from_request_token(request_token)
        return True

    def ensure_authenticated(self) -> BrokerSession:
        session = self._session_manager.get_session()
        if session is not None and not self._session_manager.needs_refresh():
            return self._session_manager.require_valid_session()

        with self._auth_lock:
            session = self._session_manager.get_session()
            if session is not None and not self._session_manager.needs_refresh():
                return self._session_manager.require_valid_session()

            app_logger.warning("5paisa access token expired or missing; authenticating automatically")
            if self.try_reauthenticate_from_env():
                return self._session_manager.require_valid_session()

            self._authenticate_via_oauth_flow()
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

        app_logger.info(f"5paisa callback server listening on http://{host}:{port}{callback_path}")
        webbrowser.open(login_url, new=2)
        app_logger.info("Waiting for 5paisa OAuth callback")

        try:
            if not state.event.wait(timeout=300):
                raise BrokerConnectionError("Broker connection unavailable.")
            if not state.request_token:
                raise BrokerConnectionError("Broker connection unavailable.")
            self.reauthenticate_from_request_token(state.request_token)
        finally:
            try:
                server.shutdown()
            except Exception:
                pass
            server.server_close()

    @staticmethod
    def _extract_callback_url(login_url: str) -> str:
        parsed = urlparse(login_url)
        query = parse_qs(parsed.query)
        response = query.get("ResponseURL", [""])
        callback_url = (response[0] or "").strip()
        if not callback_url:
            raise BrokerConnectionError("Broker connection unavailable.")
        return callback_url

    @staticmethod
    def _build_callback_handler(state: _OAuthCallbackState, host: str, port: int, callback_path: str):
        class _CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
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
                    state.request_token = token
                    state.callback_url = f"http://{host}:{port}{callback_path}?{parsed.query}"
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

        return _CallbackHandler
