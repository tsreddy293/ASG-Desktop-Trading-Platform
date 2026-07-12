from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta, timezone
import os
from threading import Event, Lock, RLock, Thread
from time import sleep
from typing import Callable

from src.brokers.base_broker import BrokerConnectionError
from src.core.logger import app_logger


class LoginState(str, Enum):
    NOT_CONNECTED = "Not Connected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    SESSION_EXPIRED = "Session Expired"
    RECONNECTING = "Reconnecting"
    AUTHENTICATION_FAILED = "Authentication Failed"


class SessionEventType(str, Enum):
    SESSION_CONNECTED = "SESSION_CONNECTED"
    SESSION_DISCONNECTED = "SESSION_DISCONNECTED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_REFRESHED = "SESSION_REFRESHED"
    SESSION_RECONNECTING = "SESSION_RECONNECTING"
    SESSION_FAILED = "SESSION_FAILED"


@dataclass(slots=True)
class BrokerSession:
    access_token: str
    refresh_token: str
    client_code: str
    status: str
    issued_at: datetime
    expires_at: datetime
    user_id: str = ""
    login_time: datetime | None = None
    expiry_time: datetime | None = None
    last_refresh_time: datetime | None = None


@dataclass(slots=True)
class SessionEvent:
    event_type: SessionEventType
    state: LoginState
    timestamp: datetime
    message: str
    session: BrokerSession | None
    retry_count: int = 0


SessionEventHandler = Callable[[SessionEvent], None]
RefreshCallback = Callable[[], bool]
ReachabilityCallback = Callable[[], bool]


class FivePaisaSessionManager:
    """Stores and refreshes access token session metadata.

    Attempts secure OS keychain storage via keyring when available.
    Falls back to in-memory storage if keyring is unavailable.
    """

    _instance: FivePaisaSessionManager | None = None
    _instance_lock = Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._session: BrokerSession | None = None
        self._service_name = "asg-fivepaisa"
        self._token_key = "access_token"
        self._refresh_key = "refresh_token"
        self._client_key = "client_code"
        self._expires_key = "expires_at"
        self._user_key = "user_id"
        self._state: LoginState = LoginState.NOT_CONNECTED
        self._lock = RLock()
        self._auth_lock = Lock()
        self._handlers: list[SessionEventHandler] = []
        self._refresh_callback: RefreshCallback | None = None
        self._reachability_callback: ReachabilityCallback | None = None
        self._retry_backoff_seconds = self._parse_retry_backoff(
            os.getenv("FIVEPAISA_RECONNECT_BACKOFF_SECONDS", "5,10,20,40,60")
        )
        self._validation_interval_seconds = max(
            5.0,
            float(os.getenv("FIVEPAISA_SESSION_VALIDATION_SECONDS", "60") or "60"),
        )
        self._max_retries = min(5, len(self._retry_backoff_seconds))
        self._stop_event = Event()
        self._reconnect_interrupt = Event()
        self._validator_thread: Thread | None = None

    def set_refresh_callback(self, callback: RefreshCallback | None) -> None:
        with self._lock:
            self._refresh_callback = callback

    def set_reachability_callback(self, callback: ReachabilityCallback | None) -> None:
        with self._lock:
            self._reachability_callback = callback

    def start_validation(self) -> None:
        with self._lock:
            if self._validator_thread is not None and self._validator_thread.is_alive():
                return
            self._stop_event.clear()
            self._validator_thread = Thread(target=self._run_validation_loop, daemon=True)
            self._validator_thread.start()

    def stop_validation(self) -> None:
        with self._lock:
            self._stop_event.set()
            worker = self._validator_thread
        if worker is not None and worker.is_alive():
            worker.join(timeout=1.5)

    def subscribe(self, handler: SessionEventHandler) -> None:
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)

    def unsubscribe(self, handler: SessionEventHandler) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def state(self) -> LoginState:
        with self._lock:
            return self._state

    def is_connected(self) -> bool:
        with self._lock:
            if self._state != LoginState.CONNECTED:
                return False
        return not self.needs_refresh()

    def refresh_if_needed(self, force: bool = False) -> bool:
        if not force and not self.needs_refresh():
            return True

        with self._auth_lock:
            if not force and not self.needs_refresh():
                return True

            callback: RefreshCallback | None
            with self._lock:
                callback = self._refresh_callback

            if callback is None:
                self._set_state(LoginState.SESSION_EXPIRED)
                self._publish(SessionEventType.SESSION_FAILED, "No refresh callback registered")
                return False

            self._set_state(LoginState.RECONNECTING)
            self._publish(SessionEventType.SESSION_RECONNECTING, "Refreshing session", retry_count=0)

            ok = False
            try:
                ok = bool(callback())
            except Exception as exc:
                app_logger.error(f"5paisa session refresh failed: {exc}")
                ok = False

            if ok:
                now = datetime.now(timezone.utc)
                with self._lock:
                    if self._session is not None:
                        self._session.last_refresh_time = now
                        self._session.status = "Success"
                self._set_state(LoginState.CONNECTED)
                self._publish(SessionEventType.SESSION_REFRESHED, "Session refreshed")
                app_logger.info("5paisa session refreshed")
                return True

            self._set_state(LoginState.AUTHENTICATION_FAILED)
            self._publish(SessionEventType.SESSION_FAILED, "Session refresh failed")
            return False

    def set_session(
        self,
        access_token: str,
        client_code: str,
        status: str,
        refresh_token: str = "",
        user_id: str = "",
    ) -> BrokerSession:
        now = datetime.now(timezone.utc)
        ttl_hours = float(os.getenv("FIVEPAISA_SESSION_TTL_HOURS", "24") or "24")
        expires_at = now + timedelta(hours=max(1.0, ttl_hours))
        session = BrokerSession(
            access_token=access_token,
            refresh_token=refresh_token,
            client_code=client_code,
            status=status,
            issued_at=now,
            expires_at=expires_at,
            user_id=user_id,
            login_time=now,
            expiry_time=expires_at,
            last_refresh_time=now,
        )
        with self._lock:
            self._session = session
        self._store_secure(session)
        self._reconnect_interrupt.set()
        self._set_state(LoginState.CONNECTED)
        self._publish(SessionEventType.SESSION_CONNECTED, "Login successful")
        app_logger.info("5paisa session connected")
        return session

    def clear(self) -> None:
        with self._lock:
            self._session = None
        self._clear_secure()
        self._reconnect_interrupt.set()
        self._set_state(LoginState.NOT_CONNECTED)
        self._publish(SessionEventType.SESSION_DISCONNECTED, "Session cleared")
        app_logger.info("5paisa session disconnected")

    def get_session(self) -> BrokerSession | None:
        with self._lock:
            if self._session is not None:
                return self._session
        loaded = self._load_secure()
        if loaded is not None:
            with self._lock:
                self._session = loaded
        with self._lock:
            return self._session

    def get_access_token(self) -> str:
        session = self.get_session()
        if session is None or not session.access_token:
            raise BrokerConnectionError("Broker connection unavailable.")
        return session.access_token

    def needs_refresh(self) -> bool:
        session = self.get_session()
        if session is None:
            return True
        buffer_minutes = float(os.getenv("FIVEPAISA_REFRESH_BUFFER_MINUTES", "5") or "5")
        refresh_at = session.expires_at - timedelta(minutes=max(0.0, buffer_minutes))
        expired = datetime.now(timezone.utc) >= refresh_at
        if expired and self.state() == LoginState.CONNECTED:
            self._set_state(LoginState.SESSION_EXPIRED)
            self._publish(SessionEventType.SESSION_EXPIRED, "Session expired")
        return expired

    def require_valid_session(self) -> BrokerSession:
        session = self.get_session()
        if session is None or not session.access_token:
            raise BrokerConnectionError("Broker connection unavailable.")
        if self.needs_refresh():
            raise BrokerConnectionError("Broker connection unavailable.")
        return session

    def mark_connecting(self) -> None:
        self._set_state(LoginState.CONNECTING)

    def mark_authentication_failed(self) -> None:
        self._set_state(LoginState.AUTHENTICATION_FAILED)
        self._publish(SessionEventType.SESSION_FAILED, "Authentication failed")

    def connection_status_label(self) -> str:
        current = self.state()
        if current in {LoginState.CONNECTED, LoginState.CONNECTING}:
            return current.value
        if current == LoginState.SESSION_EXPIRED:
            return "Expired"
        return "Disconnected"

    def _set_state(self, state: LoginState) -> None:
        with self._lock:
            self._state = state

    def _publish(self, event_type: SessionEventType, message: str, retry_count: int = 0) -> None:
        event = SessionEvent(
            event_type=event_type,
            state=self.state(),
            timestamp=datetime.now(timezone.utc),
            message=message,
            session=self.get_session(),
            retry_count=retry_count,
        )
        with self._lock:
            handlers = list(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                app_logger.error(f"5paisa session event handler error: {exc}")

    def _run_validation_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                session = self.get_session()
                if session is None:
                    self._set_state(LoginState.NOT_CONNECTED)
                elif self.needs_refresh():
                    self._set_state(LoginState.SESSION_EXPIRED)
                    self._publish(SessionEventType.SESSION_EXPIRED, "Session expired")
                    self._attempt_reconnect()
                else:
                    reachable = True
                    with self._lock:
                        callback = self._reachability_callback
                    if callback is not None:
                        try:
                            reachable = bool(callback())
                        except Exception:
                            reachable = False
                    if not reachable:
                        self._attempt_reconnect()
                    else:
                        self._set_state(LoginState.CONNECTED)
            except Exception as exc:
                app_logger.error(f"5paisa session validation failed: {exc}")
                self._set_state(LoginState.AUTHENTICATION_FAILED)
                self._publish(SessionEventType.SESSION_FAILED, str(exc))
            sleep(self._validation_interval_seconds)

    def _attempt_reconnect(self) -> bool:
        retries = min(self._max_retries, len(self._retry_backoff_seconds))
        self._reconnect_interrupt.clear()
        for attempt in range(retries):
            if self._stop_event.is_set():
                return False
            delay_seconds = self._retry_backoff_seconds[attempt]
            self._set_state(LoginState.RECONNECTING)
            self._publish(
                SessionEventType.SESSION_RECONNECTING,
                f"Reconnect attempt {attempt + 1}/{retries} in {int(delay_seconds)}s",
                retry_count=attempt + 1,
            )
            app_logger.warning(f"5paisa reconnect attempt {attempt + 1}/{retries}")
            if self._reconnect_interrupt.wait(timeout=delay_seconds):
                session = self.get_session()
                if session is not None and not self.needs_refresh():
                    self._set_state(LoginState.CONNECTED)
                    self._publish(SessionEventType.SESSION_CONNECTED, "Reconnected")
                    app_logger.info("5paisa session reconnected")
                    return True
                continue
            if self.refresh_if_needed(force=True):
                self._set_state(LoginState.CONNECTED)
                self._publish(SessionEventType.SESSION_CONNECTED, "Reconnected")
                app_logger.info("5paisa session reconnected")
                return True

        self._set_state(LoginState.AUTHENTICATION_FAILED)
        self._publish(SessionEventType.SESSION_FAILED, "Reconnect attempts exhausted", retry_count=retries)
        app_logger.error("5paisa reconnect failed after max retries")
        return False

    @staticmethod
    def _parse_retry_backoff(raw: str) -> list[float]:
        parsed: list[float] = []
        for chunk in str(raw or "").split(","):
            text = chunk.strip()
            if not text:
                continue
            try:
                value = float(text)
            except Exception:
                continue
            parsed.append(max(1.0, value))
        return parsed or [5.0, 10.0, 20.0, 40.0, 60.0]

    def _store_secure(self, session: BrokerSession) -> None:
        try:
            import keyring  # type: ignore

            keyring.set_password(self._service_name, self._token_key, session.access_token)
            keyring.set_password(self._service_name, self._refresh_key, session.refresh_token)
            keyring.set_password(self._service_name, self._client_key, session.client_code)
            keyring.set_password(self._service_name, self._expires_key, session.expires_at.isoformat())
            keyring.set_password(self._service_name, self._user_key, session.user_id)
        except Exception:
            app_logger.warning("Secure keyring unavailable; 5paisa session kept in memory only")

    def _load_secure(self) -> BrokerSession | None:
        try:
            import keyring  # type: ignore

            token = keyring.get_password(self._service_name, self._token_key) or ""
            if not token:
                return None
            refresh_token = keyring.get_password(self._service_name, self._refresh_key) or ""
            client_code = keyring.get_password(self._service_name, self._client_key) or ""
            expires_raw = keyring.get_password(self._service_name, self._expires_key) or ""
            user_id = keyring.get_password(self._service_name, self._user_key) or ""
            expires_at = datetime.fromisoformat(expires_raw) if expires_raw else datetime.now(timezone.utc)
            issued_at = expires_at - timedelta(days=1)
            return BrokerSession(
                access_token=token,
                refresh_token=refresh_token,
                client_code=client_code,
                status="Success",
                issued_at=issued_at,
                expires_at=expires_at,
                user_id=user_id,
                login_time=issued_at,
                expiry_time=expires_at,
                last_refresh_time=issued_at,
            )
        except Exception:
            return None

    def _clear_secure(self) -> None:
        try:
            import keyring  # type: ignore

            keyring.delete_password(self._service_name, self._token_key)
            keyring.delete_password(self._service_name, self._refresh_key)
            keyring.delete_password(self._service_name, self._client_key)
            keyring.delete_password(self._service_name, self._expires_key)
            keyring.delete_password(self._service_name, self._user_key)
        except Exception:
            pass

    @classmethod
    def _reset_singleton_for_tests(cls) -> None:
        with cls._instance_lock:
            if cls._instance is not None:
                try:
                    cls._instance.stop_validation()
                except Exception:
                    pass
            cls._instance = None
