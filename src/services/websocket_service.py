from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from time import sleep
from typing import Callable


@dataclass(slots=True)
class WebSocketState:
    connected: bool
    reconnecting: bool
    message: str


class WebSocketService:
    """Small reconnect loop for provider websocket lifecycle coordination."""

    def __init__(self, connect_cb: Callable[[], None], disconnect_cb: Callable[[], None], interval_seconds: float = 2.0) -> None:
        self._connect_cb = connect_cb
        self._disconnect_cb = disconnect_cb
        self._interval = max(1.0, float(interval_seconds))
        self._stop = Event()
        self._worker: Thread | None = None
        self._connected = False
        self._reconnecting = False
        self._message = ""

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=1.5)
        try:
            self._disconnect_cb()
        except Exception:
            pass
        self._connected = False
        self._reconnecting = False
        self._message = ""

    def state(self) -> WebSocketState:
        return WebSocketState(self._connected, self._reconnecting, self._message)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect_cb()
                self._connected = True
                self._reconnecting = False
                self._message = ""
                while not self._stop.is_set():
                    sleep(self._interval)
            except Exception:
                self._connected = False
                self._reconnecting = True
                self._message = "Live connection lost. Reconnecting..."
                sleep(self._interval)
