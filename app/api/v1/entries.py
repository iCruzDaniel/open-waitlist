from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.api_key import verify_api_key
from app.middleware.rate_limit import limiter
from app.schemas.entry import EntryCreate, EntryRead
from app.services.entry import create_entry

router = APIRouter(
    prefix="/waitlists/{slug}/entries",
    tags=["entries"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=EntryRead, status_code=201)
@limiter.limit("10/minute")
async def add_entry(
    request: Request,  # needed by slowapi  # noqa: ARG001
    slug: str,
    payload: EntryCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EntryRead:
    """Add an entry to a waitlist.

    Auto-creates the waitlist if the slug does not exist.
    Notifications (email + webhook) are dispatched as background tasks.
    """
    entry = await create_entry(session, slug, payload)

    return EntryRead(
        id=entry.id,
        waitlist_id=entry.waitlist_id,
        data=entry.data,
        email=entry.email,
        referrer=entry.referrer,
        created_at=entry.created_at,
    )
