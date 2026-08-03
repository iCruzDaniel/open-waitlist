from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.api_key import verify_api_key
from app.middleware.rate_limit import limiter
from app.schemas.entry import EntryCreate, EntryRead
from app.services.entry import create_entry
from app.services.notification import notify_new_entry

router = APIRouter(
    prefix="/waitlists/{slug}/entries",
    tags=["entries"],
)


def _entry_to_read(entry) -> EntryRead:
    return EntryRead(
        id=entry.id,
        waitlist_id=entry.waitlist_id,
        data=entry.data,
        email=entry.email,
        referrer=entry.referrer,
        created_at=entry.created_at,
    )


@router.post("", response_model=EntryRead, status_code=201, dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def add_entry(
    request: Request,  # needed by slowapi  # noqa: ARG001
    slug: str,
    payload: EntryCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EntryRead:
    entry = await create_entry(session, slug, payload)
    background_tasks.add_task(notify_new_entry, entry.id)
    return _entry_to_read(entry)
