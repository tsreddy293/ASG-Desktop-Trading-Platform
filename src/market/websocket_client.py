from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Thread
from time import sleep
from typing import Callable

from src.core.logger import app_logger


MessageHandler = Callable[[str], None]
StateHandler = Callable[[str], None]


@dataclass(slots=True)
class WebSocketClient:
    """Small reconnect-capable websocket scaffold for future broker streaming feeds."""

    url: str
    on_message: MessageHandler | None = None
    on_state: StateHandler | None = None
    reconnect_delay_seconds: float = 2.0
    _connected: bool = field(default=False, init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _thread: Thread | None = field(default=None, init=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self.on_state:
            self.on_state("disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._connected = True
                if self.on_state:
                    self.on_state("connected")
                while not self._stop_event.is_set():
                    sleep(0.25)
            except Exception as exc:  # pragma: no cover - defensive fallback
                app_logger.error(f"WebSocket loop error: {exc}")
                self._connected = False
                if self.on_state:
                    self.on_state("reconnecting")
                sleep(self.reconnect_delay_seconds)

    def push_message(self, payload: str) -> None:
        if self.on_message:
            self.on_message(payload)
