from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.router import require_admin
from app.dependencies import StoreDep
from app.repositories.models import WaitlistData
from app.schemas.waitlist import WaitlistCreate, WaitlistRead, WaitlistUpdate
from app.services.waitlist import (
    create_waitlist,
    get_waitlist_by_slug,
    list_waitlists,
    soft_delete_waitlist,
    update_waitlist,
)

router = APIRouter(prefix="/waitlists", tags=["waitlists"], dependencies=[Depends(require_admin)])


def _waitlist_to_read(wl: WaitlistData) -> WaitlistRead:
    return WaitlistRead(
        id=wl.id,
        slug=wl.slug,
        title=wl.title,
        description=wl.description,
        is_active=wl.is_active,
        created_at=wl.created_at,
        updated_at=wl.updated_at,
        entry_count=wl.entry_count,
    )


@router.get("", response_model=list[WaitlistRead])
async def list_all(
    store: StoreDep,
) -> list[WaitlistRead]:
    waitlists = await list_waitlists(store)
    return [_waitlist_to_read(wl) for wl in waitlists]


@router.get("/{slug}", response_model=WaitlistRead)
async def get_one(
    slug: str,
    store: StoreDep,
) -> WaitlistRead:
    wl = await get_waitlist_by_slug(store, slug, include_inactive=True)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
    return _waitlist_to_read(wl)


@router.post("", response_model=WaitlistRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: WaitlistCreate,
    store: StoreDep,
) -> WaitlistRead:
    existing = await get_waitlist_by_slug(store, payload.slug, include_inactive=True)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A waitlist with this slug already exists",
        )
    wl = await create_waitlist(store, payload)
    return _waitlist_to_read(wl)


@router.patch("/{slug}", response_model=WaitlistRead)
async def update(
    slug: str,
    payload: WaitlistUpdate,
    store: StoreDep,
) -> WaitlistRead:
    wl = await update_waitlist(store, slug, payload)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
    return _waitlist_to_read(wl)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    slug: str,
    store: StoreDep,
) -> None:
    wl = await soft_delete_waitlist(store, slug)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
