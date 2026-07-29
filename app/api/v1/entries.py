from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.api_key import verify_api_key
from app.middleware.rate_limit import limiter
from app.schemas.entry import EntryCreate, EntryRead, PaginatedEntries
from app.services.entry import create_entry, list_entries
from app.services.notification import notify_new_entry

router = APIRouter(
    prefix="/waitlists/{slug}/entries",
    tags=["entries"],
    dependencies=[Depends(verify_api_key)],
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
    request: Request,  # needed by slowapi  # noqa: ARG001
    slug: str,
    payload: EntryCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EntryRead:
    entry = await create_entry(session, slug, payload)
    background_tasks.add_task(notify_new_entry, entry.id)
    return _entry_to_read(entry)


@router.get("", response_model=PaginatedEntries)
async def list_all(
    slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PaginatedEntries:
    items, total = await list_entries(session, slug, skip=skip, limit=limit)
    return PaginatedEntries(
        items=[_entry_to_read(e) for e in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/csv")
async def export_csv(
    slug: str,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> StreamingResponse:
    """Export all entries for a waitlist as CSV."""
    items, _ = await list_entries(session, slug, skip=0, limit=0)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["id", "email", "referrer", "created_at", "data"])
    for entry in items:
        writer.writerow([
            entry.id,
            entry.email or "",
            entry.referrer or "",
            entry.created_at.isoformat() if entry.created_at else "",
            _serialize_data(entry.data),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{slug}-entries.csv"',
        },
    )


def _serialize_data(data: Any) -> str:
    """Safely serialize entry data to a compact JSON string for CSV."""
    import json

    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return str(data)
