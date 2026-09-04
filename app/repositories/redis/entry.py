from __future__ import annotations

from app.repositories.models import EntryData, EntryPageData
from app.repositories.redis.converters import (
    entry_to_hash,
    hash_to_entry,
    utcnow,
)
from app.repositories.redis.keys import RedisKeys


class RedisEntryRepo:
    def __init__(self, client, keys: RedisKeys) -> None:
        self._c = client
        self._k = keys

    async def get(self, entry_id: int) -> EntryData | None:
        raw = await self._c.hgetall(self._k.entry_by_id(entry_id))
        if not raw:
            return None
        return hash_to_entry(raw)

    async def create(
        self,
        *,
        waitlist_id: int,
        data: dict,
        email: str | None,
        referrer: str | None,
    ) -> EntryData:
        now = utcnow()
        entry_id = await self._c.incr(self._k.entry_seq())
        entry = EntryData(
            id=entry_id,
            waitlist_id=waitlist_id,
            data=data,
            email=email,
            referrer=referrer,
            notified_email=False,
            notified_webhook=False,
            created_at=now,
            updated_at=now,
        )
        score = now.timestamp()
        pipe = self._c.pipeline()
        pipe.hset(self._k.entry_by_id(entry_id), values=entry_to_hash(entry))
        pipe.zadd(self._k.entries_by_waitlist(waitlist_id), {str(entry_id): score})
        if email:
            pipe.sadd(self._k.entry_emails(waitlist_id), email)
        await pipe.exec()
        return entry

    async def list_by_waitlist(
        self, waitlist_id: int, *, skip: int = 0, limit: int = 50
    ) -> EntryPageData:
        total = await self._c.zcard(self._k.entries_by_waitlist(waitlist_id))
        stop = skip + limit - 1 if limit > 0 else -1
        member_ids = await self._c.zrevrange(self._k.entries_by_waitlist(waitlist_id), skip, stop)
        items: list[EntryData] = []
        for member_id in member_ids:
            raw = await self._c.hgetall(self._k.entry_by_id(int(member_id)))
            if raw:
                items.append(hash_to_entry(raw))
        return EntryPageData(items=items, total=total)

    async def data_keys(self, waitlist_id: int, *, batch_size: int = 1000) -> list[str]:
        data_keys: list[str] = []
        seen: set[str] = set()
        async for batch in self.iterate_by_waitlist(waitlist_id, batch_size=batch_size):
            for entry in batch:
                for key in entry.data:
                    if key not in seen:
                        seen.add(key)
                        data_keys.append(key)
        return data_keys

    async def iterate_by_waitlist(self, waitlist_id: int, *, batch_size: int = 1000):
        member_ids = await self._c.zrange(self._k.entries_by_waitlist(waitlist_id), 0, -1)
        batch: list[EntryData] = []
        for member_id in member_ids:
            raw = await self._c.hgetall(self._k.entry_by_id(int(member_id)))
            if raw:
                batch.append(hash_to_entry(raw))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def mark_email_notified(self, entry_id: int) -> None:
        await self._c.hset(self._k.entry_by_id(entry_id), "notified_email", "true")

    async def mark_webhook_notified(self, entry_id: int) -> None:
        await self._c.hset(self._k.entry_by_id(entry_id), "notified_webhook", "true")
