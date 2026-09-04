from __future__ import annotations

import asyncio
import contextlib
import csv
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.protocols import Store


class ExportUnavailableError(RuntimeError):
    """Raised when CSV export cannot be used (e.g. read-only filesystem in serverless)."""


@dataclass
class ExportJob:
    job_id: str
    slug: str
    status: str  # "pending" | "processing" | "done" | "error"
    progress: int  # 0-100
    processed: int
    total: int
    message: str  # error detail when status == "error"
    file_path: Path | None
    created_at: datetime
    updated_at: datetime
    condition: asyncio.Condition = field(default_factory=asyncio.Condition)
    waitlist_id: int = 0


class ExportJobManager:
    def __init__(
        self,
        export_dir: Path,
        ttl_minutes: int,
        store: Store,
    ) -> None:
        self.export_dir = export_dir
        self.ttl_minutes = ttl_minutes
        self._store = store
        self._jobs: dict[str, ExportJob] = {}
        # Detect whether the export dir is actually writable. Serverless
        # runtimes (Vercel) have a read-only filesystem, so fails gracefully if not.
        self._writable: bool = False
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            probe = export_dir / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            self._writable = True
        except OSError:
            self._writable = False

    async def start_export(self, slug: str) -> ExportJob:
        if not self._writable:
            raise ExportUnavailableError(
                "CSV export is not available in this environment (read-only filesystem). "
                "Use an always-on deployment (Docker/VPS) for exports."
            )

        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)

        # Sweep old jobs
        await self._sweep()

        # Check waitlist exists and get its ID
        wl = await self._store.waitlists.get_by_slug(slug)
        if wl is None:
            raise LookupError("Waitlist not found")

        # Count total entries
        page = await self._store.entries.list_by_waitlist(wl.id, skip=0, limit=1)
        total = page.total

        # Idempotency: return existing pending/processing job for same slug
        for job in self._jobs.values():
            if job.slug == slug and job.status in ("pending", "processing"):
                return job

        # Create new job
        job = ExportJob(
            job_id=uuid.uuid4().hex,
            slug=slug,
            status="pending",
            progress=0,
            processed=0,
            total=total,
            message="",
            file_path=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            waitlist_id=wl.id,
        )
        self._jobs[job.job_id] = job
        asyncio.create_task(self._run(job))
        return job

    async def get(self, job_id: str) -> ExportJob | None:
        return self._jobs.get(job_id)

    async def subscribe(self, job: ExportJob):
        while True:
            async with job.condition:
                yield job
                if job.status in ("done", "error"):
                    return
                try:
                    await asyncio.wait_for(job.condition.wait(), timeout=15.0)
                except TimeoutError:
                    yield None  # route emits SSE keepalive comment

    async def _run(self, job: ExportJob) -> None:
        try:
            await self._run_export(job)
        except Exception as exc:
            async with job.condition:
                job.status = "error"
                job.message = str(exc)
                job.updated_at = datetime.now()
                job.condition.notify_all()

    async def _run_export(self, job: ExportJob) -> None:
        batch_size = 1000
        wl_id = job.waitlist_id

        # Phase SCAN: collect union of keys across all entries' data dicts
        data_keys = await self._store.entries.data_keys(wl_id, batch_size=batch_size)

        # Update status to processing
        async with job.condition:
            job.status = "processing"
            job.updated_at = datetime.now()
            job.condition.notify_all()

        # Phase WRITE: stream rows to CSV
        tmp_path = self.export_dir / f"{job.job_id}.csv.tmp"
        final_path = self.export_dir / f"{job.job_id}.csv"

        # Sanitize header keys
        sanitized_data_keys = [sanitize(key) for key in data_keys]
        header = ["id", "email", "referrer", "created_at", *sanitized_data_keys]

        with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)

            if job.total == 0:
                # Empty waitlist - header only
                pass
            else:
                async for batch in self._store.entries.iterate_by_waitlist(
                    wl_id, batch_size=batch_size
                ):
                    for entry in batch:
                        row = [
                            entry.id,
                            sanitize(entry.email or ""),
                            sanitize(entry.referrer or ""),
                            entry.created_at.isoformat() if entry.created_at else "",
                            *[sanitize(flatten(entry.data.get(k))) for k in data_keys],
                        ]
                        writer.writerow(row)
                        job.processed += 1

                    # Update progress
                    progress = 10 + round(90 * job.processed / job.total) if job.total > 0 else 100
                    async with job.condition:
                        job.progress = progress
                        job.updated_at = datetime.now()
                        job.condition.notify_all()

        # Atomic replace
        os.replace(tmp_path, final_path)

        async with job.condition:
            job.status = "done"
            job.progress = 100
            job.file_path = final_path
            job.updated_at = datetime.now()
            job.condition.notify_all()

    async def _sweep(self) -> None:
        if not self._writable:
            return
        cutoff = datetime.now() - timedelta(minutes=self.ttl_minutes)
        to_remove = [job_id for job_id, job in self._jobs.items() if job.created_at < cutoff]
        for job_id in to_remove:
            job = self._jobs.pop(job_id)
            if job.file_path and job.file_path.exists():
                with contextlib.suppress(OSError):
                    job.file_path.unlink()


def flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def sanitize(value: str) -> str:
    if isinstance(value, str) and value and value[0] in "=+-@\t\r":
        return "'" + value
    return value
