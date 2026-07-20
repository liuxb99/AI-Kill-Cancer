"""
Evidence cache — in-memory TTL cache for evidence queries.

Prevents redundant API calls for recently-accessed genes/variants.
"""

from __future__ import annotations

import time
from typing import Any, Optional


class TTLCache:
    """Simple TTL cache with max size."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._cache: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, value = entry
        if time.monotonic() - timestamp > self._ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self._max_size:
            # Evict oldest 20%
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])
            for k in sorted_keys[:len(sorted_keys) // 5]:
                del self._cache[k]
        self._cache[key] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# Global evidence cache instances
gene_cache = TTLCache(ttl_seconds=300)    # 5 min
variant_cache = TTLCache(ttl_seconds=300)  # 5 min
