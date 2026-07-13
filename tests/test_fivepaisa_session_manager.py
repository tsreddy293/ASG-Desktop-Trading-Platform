from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event as ThreadEvent, Thread

import pytest

from src.brokers.fivepaisa.session_manager import (
    BrokerSession,
    FivePaisaSessionManager,
    LoginState,
    SessionEventType,
)


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    FivePaisaSessionManager._reset_singleton_for_tests()
    yield
    FivePaisaSessionManager._reset_singleton_for_tests()


def test_singleton_thread_safety() -> None:
    created: list[FivePaisaSessionManager] = []

    def build() -> None:
        created.append(FivePaisaSessionManager())

    workers = [Thread(target=build) for _ in range(10)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert created
    first = created[0]
    assert all(item is first for item in created)


def test_login_success_sets_connected_state() -> None:
    manager = FivePaisaSessionManager()

    session = manager.set_session("token", "client", "Success", refresh_token="refresh", user_id="user-1")

    assert session.client_code == "client"
    assert session.user_id == "user-1"
    assert manager.state() == LoginState.CONNECTED
    assert manager.is_connected() is True


def test_login_failure_transitions_failed_state() -> None:
    manager = FivePaisaSessionManager()

    manager.mark_authentication_failed()

    assert manager.state() == LoginState.AUTHENTICATION_FAILED


def test_expired_session_state() -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")
    loaded = manager.get_session()
    assert loaded is not None
    loaded.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    expired = manager.needs_refresh()

    assert expired is True
    assert manager.state() == LoginState.SESSION_EXPIRED


def test_refresh_success_updates_last_refresh_time() -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")
    loaded = manager.get_session()
    assert loaded is not None
    loaded.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    before = loaded.last_refresh_time

    def _refresh() -> bool:
        manager.set_session("token-2", "client", "Success", refresh_token="r")
        return True

    manager.set_refresh_callback(_refresh)
    ok = manager.refresh_if_needed(force=True)

    assert ok is True
    updated = manager.get_session()
    assert updated is not None
    assert updated.access_token == "token-2"
    assert before != updated.last_refresh_time
    assert manager.state() == LoginState.CONNECTED


def test_retry_logic_exhaustion_marks_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")
    loaded = manager.get_session()
    assert loaded is not None
    loaded.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    manager._retry_backoff_seconds = [0, 0, 0, 0, 0]
    manager._max_retries = 5
    attempts = {"refresh": 0}

    def _refresh() -> bool:
        attempts["refresh"] += 1
        return False

    manager.set_refresh_callback(_refresh)

    ok = manager._attempt_reconnect()

    assert ok is False
    assert manager.state() == LoginState.AUTHENTICATION_FAILED
    assert attempts["refresh"] == 5


def test_reconnect_emits_reconnecting_and_connected_events(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = FivePaisaSessionManager()
    manager.set_session("token", "client", "Success")
    loaded = manager.get_session()
    assert loaded is not None
    loaded.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    manager._retry_backoff_seconds = [0]
    manager._max_retries = 1

    events: list[SessionEventType] = []

    def _handler(event) -> None:
        events.append(event.event_type)

    manager.subscribe(_handler)

    def _refresh() -> bool:
        manager.set_session("token2", "client", "Success")
        return True

    manager.set_refresh_callback(_refresh)
    monkeypatch.setattr("src.brokers.fivepaisa.session_manager.sleep", lambda _seconds: None)

    ok = manager._attempt_reconnect()

    assert ok is True
    assert SessionEventType.SESSION_RECONNECTING in events
    assert SessionEventType.SESSION_CONNECTED in events


def test_validation_loop_runs_and_can_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = FivePaisaSessionManager()
    manager._validation_interval_seconds = 0.01
    manager.set_session("token", "client", "Success")

    ran = ThreadEvent()

    def _reachable() -> bool:
        ran.set()
        return True

    manager.set_reachability_callback(_reachable)

    def _fast_sleep(_seconds: float) -> None:
        if ran.is_set():
            manager._stop_event.set()

    monkeypatch.setattr("src.brokers.fivepaisa.session_manager.sleep", _fast_sleep)

    manager.start_validation()
    ran.wait(0.2)
    manager.stop_validation()

    assert ran.is_set()


def test_set_session_remains_backward_compatible_signature() -> None:
    manager = FivePaisaSessionManager()
    session = manager.set_session("token", "client", "Success")
    assert isinstance(session, BrokerSession)
    assert session.client_code == "client"
