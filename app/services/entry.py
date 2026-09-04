from __future__ import annotations

from app.repositories.models import EntryData, EntryPageData
from app.schemas.entry import EntryCreate


def _extract_email(data: dict) -> str | None:
    email_raw = data.get("email") if isinstance(data, dict) else None
    if email_raw and isinstance(email_raw, str):
        cleaned = email_raw.strip().lower()
        return cleaned or None
    return None


def _extract_referrer(data: dict) -> str | None:
    referrer_raw = data.get("referrer") if isinstance(data, dict) else None
    if referrer_raw and isinstance(referrer_raw, str):
        cleaned = referrer_raw.strip()
        return cleaned or None
    return None


async def create_entry(store, slug: str, payload: EntryCreate) -> EntryData:
    # Look up including soft-deleted waitlists so a new entry POST reactivates
    # an existing waitlist (same id) instead of silently creating a duplicate.
    wl = await store.waitlists.get_by_slug(slug, include_inactive=True)
    if wl is None:
        wl = await store.waitlists.create(
            slug=slug,
            title=slug,
            description=None,
        )
    elif not wl.is_active:
        wl = await store.waitlists.touch_active(slug)

    email = _extract_email(payload.data)
    referrer = _extract_referrer(payload.data)

    return await store.entries.create(
        waitlist_id=wl.id,
        data=payload.data,
        email=email,
        referrer=referrer,
    )


async def get_waitlist_id(store, slug: str) -> int | None:
    wl = await store.waitlists.get_by_slug(slug)
    return wl.id if wl is not None else None


async def list_entries(
    store,
    slug: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> EntryPageData:
    wl = await store.waitlists.get_by_slug(slug)
    if wl is None:
        return EntryPageData(items=[], total=0)
    return await store.entries.list_by_waitlist(wl.id, skip=skip, limit=limit)
