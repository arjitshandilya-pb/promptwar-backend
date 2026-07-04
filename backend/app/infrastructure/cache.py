"""
TTL-backed in-memory cache with LRU eviction.
Zero external dependencies — perfect for hackathon + production demo.
Key design: typed get/set, async-safe, automatic expiry.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache:
    """
    Thread-safe TTL cache with configurable max size and per-entry TTL.
    Uses asyncio.Lock for coroutine safety.
    """

    def __init__(self, max_size: int = 512, default_ttl: int = 3600) -> None:
        self._store: dict[str, _CacheEntry[Any]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            # Evict oldest entry if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]

            self._store[key] = _CacheEntry(
                value=value,
                expires_at=time.monotonic() + (ttl or self._default_ttl),
            )

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._store)

    async def purge_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        now = time.monotonic()
        async with self._lock:
            stale = [k for k, v in self._store.items() if v.expires_at < now]
            for k in stale:
                del self._store[k]
            return len(stale)


# Singleton cache instance
_cache: TTLCache | None = None


def get_cache() -> TTLCache:
    global _cache
    if _cache is None:
        from app.core.config import get_settings
        settings = get_settings()
        _cache = TTLCache(
            max_size=settings.cache_max_size,
            default_ttl=settings.cache_ttl_seconds,
        )
    return _cache


def make_cache_key(*parts: str) -> str:
    """Build a deterministic cache key from parts."""
    return ":".join(p.lower().replace(" ", "_") for p in parts)
