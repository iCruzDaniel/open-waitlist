"""In-memory fake of the Upstash async Redis client for repository unit tests."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class FakePipeline:
    def __init__(self, store: FakeRedis) -> None:
        self._store = store
        self._cmds: list[tuple[Any, ...]] = []

    def __getattr__(self, name: str):
        def _cmd(*args: Any, **kwargs: Any) -> FakePipeline:
            self._cmds.append((name, args, kwargs))
            return self

        return _cmd

    async def exec(self) -> list[Any]:
        results: list[Any] = []
        for name, args, kwargs in self._cmds:
            results.append(await self._store._run(name, args, kwargs))
        return results


class FakeRedis:
    def __init__(self) -> None:
        self._strings: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = defaultdict(dict)
        self._zsets: dict[str, dict[str, float]] = defaultdict(dict)
        self._sets: dict[str, set[str]] = defaultdict(set)
        self._counters: dict[str, int] = defaultdict(int)

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    async def _run(self, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        handler = getattr(self, name)
        return await handler(*args, **kwargs)

    # --- string ---
    async def set(self, key: str, value: str, **kwargs: Any) -> bool:  # noqa: ARG002
        self._strings[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self._strings.get(key)

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._strings:
                del self._strings[key]
                count += 1
            self._hashes.pop(key, None)
            self._zsets.pop(key, None)
            self._sets.pop(key, None)
        return count

    async def incr(self, key: str) -> int:
        self._counters[key] += 1
        return self._counters[key]

    # --- hash ---
    async def hset(
        self,
        key: str,
        field: str | None = None,
        value: str | None = None,
        values: dict[str, str] | None = None,
    ) -> int:
        bucket = self._hashes[key]
        if values:
            bucket.update(values)
        elif field is not None and value is not None:
            bucket[field] = value
        return len(bucket)

    async def hget(self, key: str, field: str) -> str | None:
        return self._hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hdel(self, key: str, *fields: str) -> int:
        bucket = self._hashes.get(key)
        if not bucket:
            return 0
        count = 0
        for f in fields:
            if f in bucket:
                del bucket[f]
                count += 1
        return count

    async def hlen(self, key: str) -> int:
        return len(self._hashes.get(key, {}))

    # --- sorted set ---
    async def zadd(self, key: str, scores: dict[str, float], **kwargs: Any) -> int:  # noqa: ARG002
        zset = self._zsets[key]
        added = 0
        for member, score in scores.items():
            if member not in zset:
                added += 1
            zset[member] = score
        return added

    async def zcard(self, key: str) -> int:
        return len(self._zsets.get(key, {}))

    async def zrange(self, key: str, start: int, stop: int, **kwargs: Any) -> list[str]:  # noqa: ARG002
        zset = self._zsets.get(key, {})
        ordered = sorted(zset.items(), key=lambda kv: (kv[1], kv[0]))
        members = [m for m, _ in ordered]
        return members[start : stop + 1 if stop >= 0 else None]

    async def zrevrange(self, key: str, start: int, stop: int, **kwargs: Any) -> list[str]:  # noqa: ARG002
        zset = self._zsets.get(key, {})
        ordered = sorted(zset.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        members = [m for m, _ in ordered]
        if stop < 0:
            return members[start:]
        return members[start : stop + 1]

    async def zrem(self, key: str, *members: str) -> int:
        zset = self._zsets.get(key)
        if not zset:
            return 0
        count = 0
        for m in members:
            if m in zset:
                del zset[m]
                count += 1
        return count

    # --- set ---
    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets[key]
        added = 0
        for m in members:
            if m not in s:
                s.add(m)
                added += 1
        return added

    async def smembers(self, key: str) -> set[str]:
        return set(self._sets.get(key, set()))

    async def scard(self, key: str) -> int:
        return len(self._sets.get(key, set()))

    # --- misc ---
    async def exists(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._strings or key in self._zsets:
                count += 1
        return count

    async def ping(self) -> bool:
        return True

    async def expire(self, key: str, seconds: int, **kwargs: Any) -> bool:  # noqa: ARG002
        return key in self._strings or key in self._hashes
