from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os

from src.brokers.base_broker import BrokerConnectionError
from src.core.logger import app_logger


@dataclass(slots=True)
class BrokerSession:
    access_token: str
    refresh_token: str
    client_code: str
    status: str
    issued_at: datetime
    expires_at: datetime


class FivePaisaSessionManager:
    """Stores and refreshes access token session metadata.

    Attempts secure OS keychain storage via keyring when available.
    Falls back to in-memory storage if keyring is unavailable.
    """

    def __init__(self) -> None:
        self._session: BrokerSession | None = None
        self._service_name = "asg-fivepaisa"
        self._token_key = "access_token"
        self._refresh_key = "refresh_token"
        self._client_key = "client_code"
        self._expires_key = "expires_at"

    def set_session(self, access_token: str, client_code: str, status: str, refresh_token: str = "") -> BrokerSession:
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
        )
        self._session = session
        self._store_secure(session)
        return session

    def clear(self) -> None:
        self._session = None
        self._clear_secure()

    def get_session(self) -> BrokerSession | None:
        if self._session is not None:
            return self._session
        loaded = self._load_secure()
        if loaded is not None:
            self._session = loaded
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
        return datetime.now(timezone.utc) >= refresh_at

    def require_valid_session(self) -> BrokerSession:
        session = self.get_session()
        if session is None or not session.access_token:
            raise BrokerConnectionError("Broker connection unavailable.")
        return session

    def _store_secure(self, session: BrokerSession) -> None:
        try:
            import keyring  # type: ignore

            keyring.set_password(self._service_name, self._token_key, session.access_token)
            keyring.set_password(self._service_name, self._refresh_key, session.refresh_token)
            keyring.set_password(self._service_name, self._client_key, session.client_code)
            keyring.set_password(self._service_name, self._expires_key, session.expires_at.isoformat())
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
            expires_at = datetime.fromisoformat(expires_raw) if expires_raw else datetime.now(timezone.utc)
            issued_at = expires_at - timedelta(days=1)
            return BrokerSession(
                access_token=token,
                refresh_token=refresh_token,
                client_code=client_code,
                status="Success",
                issued_at=issued_at,
                expires_at=expires_at,
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
        except Exception:
            pass
