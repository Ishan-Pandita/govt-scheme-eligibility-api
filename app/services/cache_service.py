"""
Eligibility result caching service.

Caches eligibility results using a hash of the user profile as the key.
Cache entries expire after a configurable TTL (default: 1 hour).
"""

import hashlib
import json
from contextlib import suppress
from typing import Optional


class CacheService:
    """
    Async cache for eligibility query results.

    Cache key is derived from a SHA-256 hash of the sorted, serialized
    user profile dict — identical profiles always hit the same cache entry.
    """

    DEFAULT_TTL = 3600  # 1 hour in seconds
    KEY_PREFIX = "eligibility:"

    def __init__(self, redis):
        self.redis = redis

    @staticmethod
    def _make_key(profile: dict) -> str:
        """
        Generate a deterministic cache key from a user profile.

        Sorts the dict and hashes it so field ordering doesn't matter.
        """
        # Convert enum values to strings for consistent hashing
        serializable = {}
        for k, v in profile.items():
            if v is None:
                continue
            if hasattr(v, "value"):
                serializable[k] = v.value
            else:
                serializable[k] = v

        payload = json.dumps(serializable, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"{CacheService.KEY_PREFIX}{digest}"

    async def get(self, profile: dict) -> Optional[list[dict]]:
        """
        Retrieve cached eligibility results for a profile.

        Returns:
            Deserialized list of matched schemes, or None on cache miss.
        """
        key = self._make_key(profile)
        try:
            cached = await self.redis.get(key)
        except Exception:
            return None

        if cached is None:
            return None

        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None

    async def set(self, profile: dict, results: list[dict], ttl: int = None) -> None:
        """
        Store eligibility results in cache.

        Args:
            profile: The user profile dict used as the cache key source.
            results: List of matched scheme dicts to cache.
            ttl: Time-to-live in seconds. Defaults to 1 hour.
        """
        key = self._make_key(profile)
        value = json.dumps(results, default=str)
        with suppress(Exception):
            await self.redis.set(key, value, ex=ttl or self.DEFAULT_TTL)

    async def delete(self, profile: dict) -> None:
        """Invalidate cached results for a specific profile."""
        key = self._make_key(profile)
        with suppress(Exception):
            await self.redis.delete(key)

    async def flush_all(self) -> int:
        """
        Flush all eligibility cache entries.

        Returns:
            Number of keys deleted.
        """
        pattern = f"{self.KEY_PREFIX}*"
        keys = []
        try:
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)
        except Exception:
            return 0

        if keys:
            with suppress(Exception):
                await self.redis.delete(*keys)

        return len(keys)

    async def health_check(self) -> bool:
        """Check if the configured cache backend is reachable."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
