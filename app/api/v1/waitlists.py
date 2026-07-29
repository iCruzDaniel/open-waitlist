from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.api_key import verify_api_key
from app.schemas.waitlist import WaitlistCreate, WaitlistRead, WaitlistUpdate
from app.services.waitlist import (
    create_waitlist,
    get_waitlist_by_slug,
    list_waitlists,
    soft_delete_waitlist,
    update_waitlist,
)

router = APIRouter(prefix="/waitlists", tags=["waitlists"], dependencies=[Depends(verify_api_key)])


def _waitlist_to_read(wl, entry_count: int = 0) -> WaitlistRead:
    return WaitlistRead(
        id=wl.id,
        slug=wl.slug,
        title=wl.title,
        description=wl.description,
        is_active=wl.is_active,
        created_at=wl.created_at,
        updated_at=wl.updated_at,
        entry_count=len(wl.entries) if hasattr(wl, "entries") else entry_count,
    )


@router.get("", response_model=list[WaitlistRead])
async def list_all(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[WaitlistRead]:
    waitlists = await list_waitlists(session)
    return [_waitlist_to_read(wl) for wl in waitlists]


@router.get("/{slug}", response_model=WaitlistRead)
async def get_one(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> WaitlistRead:
    wl = await get_waitlist_by_slug(session, slug, include_inactive=True)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
    return _waitlist_to_read(wl)


@router.post("", response_model=WaitlistRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: WaitlistCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> WaitlistRead:
    existing = await get_waitlist_by_slug(session, payload.slug, include_inactive=True)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A waitlist with this slug already exists",
        )
    wl = await create_waitlist(session, payload)
    return _waitlist_to_read(wl)


@router.put("/{slug}", response_model=WaitlistRead)
async def update(
    slug: str,
    payload: WaitlistUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> WaitlistRead:
    wl = await update_waitlist(session, slug, payload)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
    return _waitlist_to_read(wl)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    wl = await soft_delete_waitlist(session, slug)
    if wl is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        )
