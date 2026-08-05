from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.rate_limit import limiter
from app.schemas.entry import EntryCreate, EntryRead
from app.services.entry import create_entry
from app.services.notification import notify_new_entry
from app.services.turnstile import verify_turnstile

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


@router.post("", response_model=EntryRead, status_code=201)
@limiter.limit("10/minute")
async def add_entry(
    request: Request,  # needed by slowapi and for the client IP  # noqa: ARG001
    slug: str,
    payload: EntryCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EntryRead:
    # Runs after the rate limit above so bots can't flood Cloudflare's API.
    remote_ip = request.client.host if request.client else None
    await verify_turnstile(payload.turnstile_token, remote_ip)
    entry = await create_entry(session, slug, payload)
    background_tasks.add_task(notify_new_entry, entry.id)
    return _entry_to_read(entry)
