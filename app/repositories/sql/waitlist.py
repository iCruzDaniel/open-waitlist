from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.waitlist import Waitlist
from app.repositories.models import WaitlistData
from app.repositories.sql.converters import waitlist_to_data


class SQLWaitlistRepo:
    def __init__(self, session_factory) -> None:
        self._factory = session_factory

    async def get_by_slug(
        self, slug: str, *, include_inactive: bool = False
    ) -> WaitlistData | None:
        async with self._factory() as session:
            query = select(Waitlist).options(selectinload(Waitlist.entries))
            if not include_inactive:
                query = query.where(Waitlist.is_active.is_(True))
            query = query.where(Waitlist.slug == slug)
            result = await session.execute(query)
            wl = result.scalar_one_or_none()
            return waitlist_to_data(wl) if wl is not None else None

    async def list(self, *, include_inactive: bool = False) -> list[WaitlistData]:
        async with self._factory() as session:
            query = select(Waitlist).options(selectinload(Waitlist.entries))
            if not include_inactive:
                query = query.where(Waitlist.is_active.is_(True))
            query = query.order_by(Waitlist.created_at.desc())
            result = await session.execute(query)
            return [waitlist_to_data(wl) for wl in result.scalars().all()]

    async def create(self, *, slug: str, title: str, description: str | None) -> WaitlistData:
        async with self._factory() as session:
            wl = Waitlist(slug=slug, title=title, description=description)
            session.add(wl)
            await session.commit()
            await session.refresh(wl)
            return waitlist_to_data(wl)

    async def update(
        self, slug: str, *, title: str | None = None, description: str | None = None
    ) -> WaitlistData | None:
        values: dict = {}
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if values:
            async with self._factory() as session:
                await session.execute(
                    update(Waitlist)
                    .where(Waitlist.slug == slug, Waitlist.is_active.is_(True))
                    .values(**values)
                )
                await session.commit()
        return await self.get_by_slug(slug)

    async def soft_delete(self, slug: str) -> WaitlistData | None:
        wl = await self.get_by_slug(slug)
        if wl is None:
            return None
        async with self._factory() as session:
            result = await session.execute(select(Waitlist).where(Waitlist.slug == slug))
            obj = result.scalar_one_or_none()
            if obj is None:
                return None
            obj.is_active = False
            obj.deleted_at = datetime.now(UTC)
            await session.commit()
        return wl

    async def touch_active(self, slug: str) -> WaitlistData | None:
        async with self._factory() as session:
            result = await session.execute(select(Waitlist).where(Waitlist.slug == slug))
            obj = result.scalar_one_or_none()
            if obj is None:
                return None
            obj.is_active = True
            obj.deleted_at = None
            await session.commit()
            # updated_at is server-side onupdate — refresh so it's loaded before conversion.
            await session.refresh(obj)
            return waitlist_to_data(obj)
