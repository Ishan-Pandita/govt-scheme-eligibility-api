"""Small Redis-compatible in-memory cache for local development."""

import time
from fnmatch import fnmatch
from typing import AsyncIterator


class MemoryRedis:
    """
    Minimal async cache stand-in.

    It supports only the methods this API uses: get, set, delete, scan_iter,
    ping, and close.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None

        value, expires_at = item
        if expires_at is not None and expires_at <= time.time():
            del self._data[key]
            return None

        return value

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        expires_at = time.time() + ex if ex else None
        self._data[key] = (value, expires_at)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                deleted += 1
        return deleted

    async def scan_iter(
        self,
        match: str | None = None,
        count: int = 100,
    ) -> AsyncIterator[str]:
        for key in list(self._data):
            if match is None or fnmatch(key, match):
                yield key

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._data.clear()
