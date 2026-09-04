from __future__ import annotations

from sqlalchemy import text

from app.repositories.sql.admin import SQLAdminRepo
from app.repositories.sql.entry import SQLEntryRepo
from app.repositories.sql.waitlist import SQLWaitlistRepo


class SQLStore:
    """Store backed by SQLAlchemy (SQLite or Postgres)."""

    def __init__(self, session_factory) -> None:
        self.waitlists = SQLWaitlistRepo(session_factory)
        self.entries = SQLEntryRepo(session_factory)
        self.admins = SQLAdminRepo(session_factory)
        self._factory = session_factory

    async def healthcheck(self) -> bool:
        try:
            async with self._factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def close(self) -> None:
        return None
