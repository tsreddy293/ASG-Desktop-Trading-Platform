from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class CacheItem(Generic[T]):
    value: T
    updated_at: datetime


class MarketCache:
    """Thread-safe market cache with per-key TTL support."""

    def __init__(self, ttl_seconds: float = 2.5) -> None:
        self._ttl = max(1.0, float(ttl_seconds))
        self._data: dict[str, CacheItem[object]] = {}
        self._lock = RLock()

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._data[key] = CacheItem(value=value, updated_at=datetime.now(timezone.utc))

    def get(self, key: str):
        with self._lock:
            item = self._data.get(key)
            return item.value if item is not None else None

    def get_fresh(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            if datetime.now(timezone.utc) - item.updated_at > timedelta(seconds=self._ttl):
                return None
            return item.value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())
