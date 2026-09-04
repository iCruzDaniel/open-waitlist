from __future__ import annotations

from app.repositories.models import AdminData
from app.repositories.redis.converters import admin_to_hash, hash_to_admin, utcnow
from app.repositories.redis.keys import RedisKeys


class RedisAdminRepo:
    def __init__(self, client, keys: RedisKeys) -> None:
        self._c = client
        self._k = keys

    async def get_by_email(self, email: str) -> AdminData | None:
        admin_id = await self._c.get(self._k.admin_by_email(email))
        if admin_id is None:
            return None
        raw = await self._c.hgetall(self._k.admin_by_id(int(admin_id)))
        if not raw:
            return None
        return hash_to_admin(raw)

    async def get_by_id(self, admin_id: int) -> AdminData | None:
        raw = await self._c.hgetall(self._k.admin_by_id(admin_id))
        if not raw:
            return None
        return hash_to_admin(raw)

    async def count(self) -> int:
        return await self._c.hlen(self._k.admins_by_email())

    async def create(self, *, email: str, password_hash: str) -> AdminData:
        now = utcnow()
        admin_id = await self._c.incr(self._k.admin_seq())
        admin = AdminData(
            id=admin_id,
            email=email,
            password_hash=password_hash,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        pipe = self._c.pipeline()
        pipe.hset(self._k.admin_by_id(admin_id), values=admin_to_hash(admin))
        pipe.set(self._k.admin_by_email(email), str(admin_id))
        pipe.hset(self._k.admins_by_email(), email.lower(), str(admin_id))
        await pipe.exec()
        return admin
