from __future__ import annotations

from dataclasses import dataclass

from app.repositories.models import WaitlistData
from app.schemas.waitlist import WaitlistCreate, WaitlistUpdate


@dataclass
class WaitlistResult:
    waitlist: WaitlistData | None
    conflict: bool = False


async def list_waitlists(store, *, include_inactive: bool = False) -> list[WaitlistData]:
    return await store.waitlists.list(include_inactive=include_inactive)


async def get_waitlist_by_slug(
    store, slug: str, *, include_inactive: bool = False
) -> WaitlistData | None:
    return await store.waitlists.get_by_slug(slug, include_inactive=include_inactive)


async def create_waitlist(store, payload: WaitlistCreate) -> WaitlistData:
    return await store.waitlists.create(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
    )


async def update_waitlist(store, slug: str, payload: WaitlistUpdate) -> WaitlistData | None:
    return await store.waitlists.update(
        slug,
        title=payload.title if payload.title is not None else None,
        description=payload.description if payload.description is not None else None,
    )


async def soft_delete_waitlist(store, slug: str) -> WaitlistData | None:
    return await store.waitlists.soft_delete(slug)
