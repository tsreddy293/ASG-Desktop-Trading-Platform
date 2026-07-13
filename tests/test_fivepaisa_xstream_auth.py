from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Thread
from typing import Generator

import pytest

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.auth_service import FivePaisaAuthService
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.login import FivePaisaLoginService
from src.brokers.fivepaisa.market import FivePaisaMarketService
from src.brokers.fivepaisa.session_manager import BrokerSession, FivePaisaSessionManager


@pytest.fixture(autouse=True)
def _reset_session_singleton() -> Generator[None, None, None]:
    FivePaisaSessionManager._reset_singleton_for_tests()
    yield
    FivePaisaSessionManager._reset_singleton_for_tests()


def _set_required_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "FIVEPAISA_API_KEY=api-key",
                "FIVEPAISA_USER_ID=user-id",
                "FIVEPAISA_ENCRYPTION_KEY=enc-key",
                "FIVEPAISA_APP_PASSWORD=secret",
                "FIVEPAISA_CALLBACK_URL=https://localhost/callback",
                "FIVEPAISA_AUTH_URL=https://dev-openapi.5paisa.com/WebVendorLogin/VLogin/Index",
                "FIVEPAISA_TOKEN_URL=https://Openapi.5paisa.com/VendorsAPI/Service1.svc/GetAccessToken",
                "FIVEPAISA_STATE=ASG",
            ]
        ),
        encoding="utf-8",
    )


def test_generate_login_url_includes_vendor_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_required_env(monkeypatch, tmp_path)
    service = FivePaisaAuthService()

    url = service.generate_login_url()

    assert "VendorKey=api-key" in url
    assert "ResponseURL=https%3A%2F%2Flocalhost%2Fcallback" in url
    assert "State=ASG" in url


def test_extract_request_token_from_callback() -> None:
    service = FivePaisaAuthService()

    token = service.extract_request_token("https://localhost/callback?RequestToken=req-123")

    assert token == "req-123"


def test_exchange_request_token_parses_access_token(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_required_env(monkeypatch, tmp_path)
    service = FivePaisaAuthService()

    def fake_post(url: str, payload: dict) -> dict:
        assert payload["head"]["Key"] == "api-key"
        assert payload["body"]["RequestToken"] == "req-123"
        return {
            "body": {
                "AccessToken": "access-xyz",
                "ClientCode": "C123",
                "Status": "Success",
            }
        }

    monkeypatch.setattr(FivePaisaAuthService, "_post_json", staticmethod(fake_post))

    response = service.exchange_request_token("req-123")

    assert response.access_token == "access-xyz"
    assert response.client_code == "C123"
    assert response.status == "Success"


def test_session_manager_marks_refresh_after_one_day() -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")

    session = manager.get_session()
    assert session is not None
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert manager.needs_refresh() is True


def test_broker_client_authenticate_callback(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _set_required_env(monkeypatch, tmp_path)
    client = FivePaisaBrokerClient()

    monkeypatch.setattr(client._auth_service, "extract_request_token", lambda callback_url: "req-123")

    class _Resp:
        access_token = "token-1"
        refresh_token = "refresh-1"
        client_code = "client-1"
        status = "Success"

    monkeypatch.setattr(client._auth_service, "exchange_request_token", lambda request_token: _Resp())

    result = client.authenticate_from_callback("https://localhost/callback?RequestToken=req-123")

    assert result.access_token == "token-1"
    assert result.client_code == "client-1"
    assert client.is_authenticated() is True


def test_broker_client_ensure_authenticated_raises_when_expired() -> None:
    session_manager = FivePaisaSessionManager()
    auth_service = FivePaisaAuthService()
    client = FivePaisaBrokerClient(auth_service=auth_service, session_manager=session_manager)

    expired_session = BrokerSession(
        access_token="old-token",
        refresh_token="",
        client_code="client",
        status="Success",
        issued_at=datetime.now(timezone.utc) - timedelta(days=2),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    session_manager._session = expired_session

    with pytest.raises(BrokerConnectionError):
        client._authenticate_via_oauth_flow = lambda: (_ for _ in ()).throw(BrokerConnectionError("Broker connection unavailable."))
        client.ensure_authenticated()


def test_ensure_authenticated_logs_skip_when_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")
    client = FivePaisaBrokerClient(auth_service=FivePaisaAuthService(), session_manager=manager)
    logs: list[str] = []

    monkeypatch.setattr("src.brokers.fivepaisa.broker_client.app_logger.info", lambda message: logs.append(str(message)))

    _ = client.ensure_authenticated()

    assert any("LOGIN_SKIPPED_ALREADY_CONNECTED" in row for row in logs)


def test_duplicate_oauth_windows_are_prevented() -> None:
    manager = FivePaisaSessionManager()
    client = FivePaisaBrokerClient(auth_service=FivePaisaAuthService(), session_manager=manager)
    calls = {"oauth": 0}

    def _fake_oauth_flow() -> None:
        calls["oauth"] += 1
        manager.set_session("token", "client", "Success")

    client._authenticate_via_oauth_flow = _fake_oauth_flow  # type: ignore[method-assign]

    worker_1 = Thread(target=client.ensure_authenticated)
    worker_2 = Thread(target=client.ensure_authenticated)
    worker_1.start()
    worker_2.start()
    worker_1.join()
    worker_2.join()

    assert calls["oauth"] == 1


def test_login_service_skips_when_authentication_in_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FivePaisaLoginService()
    monkeypatch.setattr(service._broker_client, "authentication_in_progress", lambda: True)
    called = {"ensure": 0}
    logs: list[str] = []

    def _fake_ensure() -> None:
        called["ensure"] += 1

    monkeypatch.setattr(service._broker_client, "ensure_authenticated", _fake_ensure)
    monkeypatch.setattr("src.brokers.fivepaisa.login.app_logger.info", lambda message: logs.append(str(message)))

    service.login()

    assert called["ensure"] == 0
    assert any("LOGIN_SKIPPED_ALREADY_CONNECTED" in row for row in logs)


def test_historical_data_requires_ready_session_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FivePaisaLoginService()
    market = FivePaisaMarketService(service)

    monkeypatch.setattr(service._broker_client.session_manager, "is_connected", lambda: False)
    monkeypatch.setattr(service._broker_client, "authentication_in_progress", lambda: False)
    monkeypatch.setattr(
        market._market_data,
        "get_historical_candles",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("historical request should not run")),
    )

    with pytest.raises(BrokerConnectionError, match="Session expired\\. Please click Connect\\."):
        market.get_historical_data("SBIN", exchange="NSE", timeframe="15 Minute")
