from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from src.brokers.base_broker import BrokerConnectionError
from src.core.logger import app_logger


@dataclass(slots=True)
class XStreamCredentials:
    api_key: str
    user_id: str
    encryption_key: str
    app_password: str
    callback_url: str
    login_url: str
    token_url: str
    state: str


@dataclass(slots=True)
class AccessTokenResponse:
    access_token: str
    refresh_token: str
    client_code: str
    status: str
    raw_response: dict[str, Any]


class FivePaisaAuthService:
    """Implements 5paisa XStream OAuth request-token to access-token flow."""

    def __init__(self) -> None:
        self._dotenv_values = self._load_dotenv_if_present()

    def generate_login_url(self) -> str:
        creds = self._load_credentials()
        if not creds.callback_url:
            app_logger.warning("5paisa callback URL missing in .env")
            raise BrokerConnectionError("Broker connection unavailable.")
        query = {
            "VendorKey": creds.api_key,
            "ResponseURL": creds.callback_url,
        }
        if creds.state:
            query["State"] = creds.state
        return f"{creds.login_url}?{urlencode(query)}"

    def extract_request_token(self, callback_url: str) -> str:
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        for key in ("RequestToken", "requestToken", "token"):
            values = params.get(key)
            if values and values[0].strip():
                return values[0].strip()
        raise BrokerConnectionError("Broker connection unavailable.")

    def exchange_request_token(self, request_token: str) -> AccessTokenResponse:
        creds = self._load_credentials()
        if not request_token or not request_token.strip():
            raise BrokerConnectionError("Broker connection unavailable.")

        payload = {
            "head": {
                "Key": creds.api_key,
            },
            "body": {
                "RequestToken": request_token.strip(),
                "EncryKey": creds.encryption_key,
                "UserId": creds.user_id,
            },
        }

        response = self._post_json(creds.token_url, payload)
        body = response.get("body", response)
        access_token = str(body.get("AccessToken", "") or "").strip()
        refresh_token = str(body.get("RefreshToken", "") or "").strip()
        client_code = str(body.get("ClientCode", "") or "").strip()
        raw_status = body.get("Status", "")
        status = str(raw_status).strip()

        normalized_status = status.lower()
        if not access_token or normalized_status not in {"success", "ok", "true", "0"}:
            app_logger.warning("5paisa token exchange returned non-success status")
            raise BrokerConnectionError("Broker connection unavailable.")

        app_logger.info("Access Token generated")
        return AccessTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            client_code=client_code,
            status=status,
            raw_response=response,
        )

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            url=url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:
            app_logger.error(f"5paisa token exchange failed: {exc}")
            raise BrokerConnectionError("Broker connection unavailable.") from exc

        try:
            parsed = json.loads(raw)
        except Exception as exc:
            app_logger.error("5paisa token exchange returned invalid JSON")
            raise BrokerConnectionError("Broker connection unavailable.") from exc

        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _load_dotenv_if_present() -> dict[str, str]:
        values: dict[str, str] = {}
        dotenv_path = ".env"
        if not os.path.exists(dotenv_path):
            return values

        try:
            with open(dotenv_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    text = line.strip()
                    if not text or text.startswith("#") or "=" not in text:
                        continue
                    key, value = text.split("=", 1)
                    env_key = key.strip()
                    env_val = value.strip().strip('"').strip("'")
                    if env_key:
                        values[env_key] = env_val
                    if env_key and env_key not in os.environ:
                        os.environ[env_key] = env_val
        except Exception:
            # Keep auth robust even if .env cannot be parsed.
            return {}
        return values

    def _load_credentials(self) -> XStreamCredentials:
        api_key = (self._dotenv_values.get("FIVEPAISA_API_KEY", "") or "").strip()
        user_id = (self._dotenv_values.get("FIVEPAISA_USER_ID", "") or "").strip()
        encryption_key = (self._dotenv_values.get("FIVEPAISA_ENCRYPTION_KEY", "") or "").strip()
        app_password = (self._dotenv_values.get("FIVEPAISA_APP_PASSWORD", "") or "").strip()
        callback_url = (self._dotenv_values.get("FIVEPAISA_CALLBACK_URL", "") or "").strip()
        login_url = (self._dotenv_values.get("FIVEPAISA_AUTH_URL", "") or "").strip()
        token_url = (self._dotenv_values.get("FIVEPAISA_TOKEN_URL", "") or "").strip()
        state = (self._dotenv_values.get("FIVEPAISA_STATE", "") or "").strip()

        if not all([api_key, user_id, encryption_key, app_password]):
            app_logger.warning("5paisa credentials missing in .env")
            raise BrokerConnectionError("Broker connection unavailable.")
        if not login_url or not token_url:
            app_logger.warning("5paisa OAuth URLs missing in .env")
            raise BrokerConnectionError("Broker connection unavailable.")

        return XStreamCredentials(
            api_key=api_key,
            user_id=user_id,
            encryption_key=encryption_key,
            app_password=app_password,
            callback_url=callback_url,
            login_url=login_url,
            token_url=token_url,
            state=state,
        )
