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

from sqlalchemy import func, select

from app.models.entry import Entry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


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
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.export_dir = export_dir
        self.ttl_minutes = ttl_minutes
        self._session_factory = session_factory
        self._jobs: dict[str, ExportJob] = {}

    async def start_export(self, slug: str) -> ExportJob:
        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)

        # Sweep old jobs
        await self._sweep()

        # Check waitlist exists and get its ID
        async with self._session_factory() as session:
            from app.models.waitlist import Waitlist

            result = await session.execute(select(Waitlist.id).where(Waitlist.slug == slug))
            wl_id = result.scalar_one_or_none()
            if wl_id is None:
                raise LookupError("Waitlist not found")

            # Count total entries
            count_q = select(func.count(Entry.id)).where(Entry.waitlist_id == wl_id)
            total = (await session.execute(count_q)).scalar_one()

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
            waitlist_id=wl_id,
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
        async with self._session_factory() as session:
            data_keys: list[str] = []
            seen_keys: set[str] = set()
            last_id = 0

            while True:
                result = await session.execute(
                    select(Entry.id, Entry.data)
                    .where(Entry.waitlist_id == wl_id, Entry.id > last_id)
                    .order_by(Entry.id)
                    .limit(batch_size)
                )
                rows = result.all()
                if not rows:
                    break
                for _entry_id, data in rows:
                    if isinstance(data, dict):
                        for key in data:
                            if key not in seen_keys:
                                seen_keys.add(key)
                                data_keys.append(key)
                last_id = rows[-1][0]

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
                    last_id = 0
                    while True:
                        result = await session.execute(
                            select(Entry)
                            .where(Entry.waitlist_id == wl_id, Entry.id > last_id)
                            .order_by(Entry.id)
                            .limit(batch_size)
                        )
                        entries = result.scalars().all()
                        if not entries:
                            break

                        for entry in entries:
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
                        progress = (
                            10 + round(90 * job.processed / job.total) if job.total > 0 else 100
                        )
                        async with job.condition:
                            job.progress = progress
                            job.updated_at = datetime.now()
                            job.condition.notify_all()

                        last_id = entries[-1].id

            # Atomic replace
            os.replace(tmp_path, final_path)

            async with job.condition:
                job.status = "done"
                job.progress = 100
                job.file_path = final_path
                job.updated_at = datetime.now()
                job.condition.notify_all()

    async def _sweep(self) -> None:
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
