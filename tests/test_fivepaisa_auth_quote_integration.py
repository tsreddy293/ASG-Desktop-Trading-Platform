from __future__ import annotations

import os

import pytest

from src.brokers.base_broker import BrokerConnectionError
from src.brokers.fivepaisa.broker_client import FivePaisaBrokerClient
from src.brokers.fivepaisa.market_data_service import MarketDataService


def test_auth_login_and_live_hdfcbank_quote_integration() -> None:
    """Integration test for live NSE quote pull through MarketDataService.

    This test intentionally uses live credentials from .env and skips when
    the required callback/request token fields are unavailable.
    """

    if not os.path.exists(".env"):
        pytest.skip(".env not found for live 5paisa integration test")

    # Instantiating client loads .env into process environment through auth service.
    client = FivePaisaBrokerClient()

    if not client.is_authenticated():
        request_token = os.getenv("FIVEPAISA_REQUEST_TOKEN", "").strip()
        if not request_token:
            pytest.skip("No active 5paisa session and FIVEPAISA_REQUEST_TOKEN missing for re-auth")
        try:
            result = client.reauthenticate_from_request_token(request_token)
        except BrokerConnectionError:
            pytest.skip("Unable to refresh 5paisa session from request token for live quote check")
        assert result.access_token

    market = MarketDataService(broker_client=client, session_manager=client._session_manager)

    try:
        quote = market.get_quote("HDFCBANK")
    except BrokerConnectionError:
        pytest.skip("Live HDFCBANK quote not available in current environment")

    assert quote["symbol"] == "HDFCBANK"
    assert quote["exchange"] == "NSE"
    assert isinstance(quote["ltp"], float)
    assert quote["ltp"] >= 0.0
