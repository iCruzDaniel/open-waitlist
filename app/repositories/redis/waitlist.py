from __future__ import annotations

from app.repositories.models import WaitlistData
from app.repositories.redis.converters import (
    hash_to_waitlist,
    utcnow,
    waitlist_to_hash,
)
from app.repositories.redis.keys import RedisKeys


class RedisWaitlistRepo:
    def __init__(self, client, keys: RedisKeys) -> None:
        self._c = client
        self._k = keys

    async def _entry_count(self, waitlist_id: int) -> int:
        try:
            return await self._c.zcard(self._k.entries_by_waitlist(waitlist_id))
        except Exception:
            return 0

    async def get_by_slug(
        self, slug: str, *, include_inactive: bool = False
    ) -> WaitlistData | None:
        waitlist_id = await self._c.get(self._k.waitlist_by_slug(slug))
        if waitlist_id is None:
            return None
        raw = await self._c.hgetall(self._k.waitlist_by_id(int(waitlist_id)))
        if not raw:
            return None
        wl = hash_to_waitlist(raw)
        if not include_inactive and not wl.is_active:
            return None
        wl.entry_count = await self._entry_count(wl.id)
        return wl

    async def list(self, *, include_inactive: bool = False) -> list[WaitlistData]:
        slug_ids = await self._c.hgetall(self._k.waitlist_slug_index())
        waitlists: list[WaitlistData] = []
        for waitlist_id in slug_ids.values():
            raw = await self._c.hgetall(self._k.waitlist_by_id(int(waitlist_id)))
            if not raw:
                continue
            wl = hash_to_waitlist(raw)
            if not include_inactive and not wl.is_active:
                continue
            wl.entry_count = await self._entry_count(wl.id)
            waitlists.append(wl)
        waitlists.sort(key=lambda w: w.created_at, reverse=True)
        return waitlists

    async def create(self, *, slug: str, title: str, description: str | None) -> WaitlistData:
        now = utcnow()
        waitlist_id = await self._c.incr(self._k.waitlist_seq())
        wl = WaitlistData(
            id=waitlist_id,
            slug=slug,
            title=title,
            description=description,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            entry_count=0,
        )
        pipe = self._c.pipeline()
        pipe.hset(self._k.waitlist_by_id(waitlist_id), values=waitlist_to_hash(wl))
        pipe.set(self._k.waitlist_by_slug(slug), str(waitlist_id))
        pipe.hset(self._k.waitlist_slug_index(), slug, str(waitlist_id))
        pipe.hset(self._k.waitlist_id_index(), str(waitlist_id), slug)
        await pipe.exec()
        return wl

    async def update(
        self, slug: str, *, title: str | None = None, description: str | None = None
    ) -> WaitlistData | None:
        wl = await self.get_by_slug(slug)
        if wl is None:
            return None
        if title is not None:
            wl.title = title
        if description is not None:
            wl.description = description
        wl.updated_at = utcnow()
        pipe = self._c.pipeline()
        pipe.hset(self._k.waitlist_by_id(wl.id), values=waitlist_to_hash(wl))
        await pipe.exec()
        return wl

    async def soft_delete(self, slug: str) -> WaitlistData | None:
        wl = await self.get_by_slug(slug)
        if wl is None:
            return None
        wl.is_active = False
        wl.deleted_at = utcnow()
        wl.updated_at = utcnow()
        pipe = self._c.pipeline()
        pipe.hset(self._k.waitlist_by_id(wl.id), values=waitlist_to_hash(wl))
        await pipe.exec()
        return wl

    async def touch_active(self, slug: str) -> WaitlistData | None:
        waitlist_id = await self._c.get(self._k.waitlist_by_slug(slug))
        if waitlist_id is None:
            return None
        wl = hash_to_waitlist(await self._c.hgetall(self._k.waitlist_by_id(int(waitlist_id))))
        wl.is_active = True
        wl.deleted_at = None
        wl.updated_at = utcnow()
        pipe = self._c.pipeline()
        pipe.hset(self._k.waitlist_by_id(wl.id), values=waitlist_to_hash(wl))
        await pipe.exec()
        return wl
