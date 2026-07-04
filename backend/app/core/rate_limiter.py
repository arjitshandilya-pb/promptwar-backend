"""
Sliding-window rate limiter backed by in-process counters.
Per-IP, per-endpoint category (AI vs. general).
Thread-safe via asyncio locks for async contexts.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from app.core.config import get_settings
from app.core.exceptions import RateLimitError


@dataclass
class _Window:
    """Sliding window of request timestamps."""

    timestamps: Deque[float] = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RateLimiter:
    """
    Sliding-window rate limiter.

    Two tiers:
    - ``ai``:      stricter limit for LLM endpoints (expensive)
    - ``general``: looser limit for non-AI endpoints
    """

    def __init__(self) -> None:
        self._windows: dict[str, _Window] = {}
        self._global_lock = asyncio.Lock()

    async def _get_window(self, key: str) -> _Window:
        async with self._global_lock:
            if key not in self._windows:
                self._windows[key] = _Window()
            return self._windows[key]

    async def check(self, ip: str, tier: str = "general") -> None:
        """
        Check if the IP is within rate limits for the given tier.
        Raises RateLimitError if the limit is exceeded.
        """
        settings = get_settings()
        limit = (
            settings.rate_limit_ai_rpm if tier == "ai" else settings.rate_limit_general_rpm
        )
        window_secs = 60.0
        key = f"{ip}:{tier}"

        win = await self._get_window(key)
        now = time.monotonic()

        async with win.lock:
            # Evict timestamps outside the window
            while win.timestamps and win.timestamps[0] < now - window_secs:
                win.timestamps.popleft()

            if len(win.timestamps) >= limit:
                retry_after = window_secs - (now - win.timestamps[0])
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after:.1f}s.",
                    {"retry_after": retry_after, "limit": limit, "tier": tier},
                )

            win.timestamps.append(now)

    async def cleanup_old_windows(self) -> None:
        """Periodically called to free memory for inactive IPs."""
        async with self._global_lock:
            cutoff = time.monotonic() - 120
            stale = [
                k
                for k, w in self._windows.items()
                if not w.timestamps or w.timestamps[-1] < cutoff
            ]
            for k in stale:
                del self._windows[k]


# Singleton instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter
