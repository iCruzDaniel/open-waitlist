from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import require_admin
from app.database import get_session
from app.middleware.rate_limit import limiter
from app.schemas.entry import EntryRead, PaginatedEntries
from app.services.entry import list_entries

router = APIRouter(
    prefix="/waitlists/{slug}/entries",
    tags=["exports"],
    dependencies=[Depends(require_admin)],
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


@router.get("", response_model=PaginatedEntries)
async def list_all(
    request: Request,  # noqa: ARG001
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


@router.post("/export")
@limiter.limit("10/minute")
async def trigger_export(
    request: Request,
    slug: str,
) -> JSONResponse:
    manager = request.app.state.export_manager
    try:
        job = await manager.start_export(slug)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found",
        ) from None
    return JSONResponse(status_code=202, content={"job_id": job.job_id})


@router.get("/export/{job_id}/status")
async def export_status(
    request: Request,
    slug: str,  # noqa: ARG001
    job_id: str,
) -> StreamingResponse:
    manager = request.app.state.export_manager
    job = await manager.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    async def event_generator():
        async for snap in manager.subscribe(job):
            if snap is None:
                yield ": keepalive\n\n"
                continue

            payload = {
                "job_id": snap.job_id,
                "slug": snap.slug,
                "status": snap.status,
                "progress": snap.progress,
                "processed": snap.processed,
                "total": snap.total,
            }
            if snap.status == "error":
                payload["message"] = snap.message
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                return
            if snap.status == "done":
                payload["download_url"] = f"/waitlists/{slug}/entries/export/{job_id}/download"
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                return
            yield f"event: progress\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/export/{job_id}/download")
async def export_download(
    request: Request,
    slug: str,
    job_id: str,
) -> FileResponse:
    manager = request.app.state.export_manager
    job = await manager.get(job_id)
    if job is None or job.status != "done" or job.file_path is None or not job.file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found",
        )

    filename = f"{re.sub(r'[^A-Za-z0-9._-]', '-', slug)}-entries.csv"
    return FileResponse(
        job.file_path,
        media_type="text/csv",
        filename=filename,
    )
