from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.waitlist import Waitlist
from app.schemas.waitlist import WaitlistCreate, WaitlistUpdate


async def list_waitlists(
    session: AsyncSession, *, include_inactive: bool = False
) -> list[Waitlist]:
    query = select(Waitlist).options(selectinload(Waitlist.entries))
    if not include_inactive:
        query = query.where(Waitlist.is_active.is_(True))
    query = query.order_by(Waitlist.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_waitlist_by_slug(
    session: AsyncSession, slug: str, *, include_inactive: bool = False
) -> Waitlist | None:
    query = select(Waitlist).options(selectinload(Waitlist.entries))
    if not include_inactive:
        query = query.where(Waitlist.is_active.is_(True))
    query = query.where(Waitlist.slug == slug)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_waitlist(session: AsyncSession, payload: WaitlistCreate) -> Waitlist:
    wl = Waitlist(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
    )
    session.add(wl)
    await session.commit()
    await session.refresh(wl)
    return wl


async def update_waitlist(
    session: AsyncSession, slug: str, payload: WaitlistUpdate
) -> Waitlist | None:
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return await get_waitlist_by_slug(session, slug)

    await session.execute(
        update(Waitlist).where(Waitlist.slug == slug, Waitlist.is_active.is_(True)).values(**values)
    )
    await session.commit()
    return await get_waitlist_by_slug(session, slug)


async def soft_delete_waitlist(session: AsyncSession, slug: str) -> Waitlist | None:
    wl = await get_waitlist_by_slug(session, slug)
    if wl is None:
        return None
    wl.is_active = False
    wl.deleted_at = datetime.now(UTC)
    await session.commit()
    return wl
