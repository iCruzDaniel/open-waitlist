from __future__ import annotations

from sqlalchemy import select
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
