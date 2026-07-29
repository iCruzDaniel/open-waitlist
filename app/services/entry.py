from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.waitlist import Waitlist
from app.schemas.entry import EntryCreate


async def create_entry(
    session: AsyncSession, slug: str, payload: EntryCreate
) -> Entry:
    """Create an entry in a waitlist, auto-creating the waitlist if needed."""
    # Find or auto-create waitlist
    result = await session.execute(
        select(Waitlist).where(Waitlist.slug == slug)
    )
    wl = result.scalar_one_or_none()

    if wl is None:
        wl = Waitlist(
            slug=slug,
            title=slug,  # use slug as default display title
            description=None,
            is_active=True,
        )
        session.add(wl)
        await session.flush()  # get wl.id without full commit yet
    elif not wl.is_active:
        wl.is_active = True
        wl.deleted_at = None

    # Extract email from payload data if present
    email_raw = payload.data.get("email") if isinstance(payload.data, dict) else None
    email = str(email_raw).strip().lower() if email_raw and isinstance(email_raw, str) else None

    # Extract referrer from payload data if present
    referrer_raw = payload.data.get("referrer") if isinstance(payload.data, dict) else None
    referrer = str(referrer_raw).strip() if referrer_raw and isinstance(referrer_raw, str) else None

    entry = Entry(
        waitlist_id=wl.id,
        data=payload.data,
        email=email,
        referrer=referrer,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def list_entries(
    session: AsyncSession,
    slug: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Entry], int]:
    """List entries for a waitlist with pagination. Returns (items, total)."""
    result = await session.execute(
        select(Waitlist.id).where(Waitlist.slug == slug)
    )
    wl_id = result.scalar_one_or_none()
    if wl_id is None:
        return [], 0

    count_q = select(func.count(Entry.id)).where(Entry.waitlist_id == wl_id)
    total = (await session.execute(count_q)).scalar_one()

    query = (
        select(Entry)
        .where(Entry.waitlist_id == wl_id)
        .order_by(Entry.created_at.desc())
        .offset(skip)
    )
    if limit > 0:
        query = query.limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all()), total
