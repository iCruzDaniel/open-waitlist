from __future__ import annotations

from app.repositories.redis.admin import RedisAdminRepo
from app.repositories.redis.entry import RedisEntryRepo
from app.repositories.redis.keys import RedisKeys
from app.repositories.redis.waitlist import RedisWaitlistRepo


class RedisStore:
    """Store backed by Upstash Redis (REST)."""

    def __init__(self, client, keys: RedisKeys) -> None:
        self._c = client
        self.waitlists = RedisWaitlistRepo(client, keys)
        self.entries = RedisEntryRepo(client, keys)
        self.admins = RedisAdminRepo(client, keys)

    async def healthcheck(self) -> bool:
        try:
            await self._c.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        return None
