from __future__ import annotations

from sqlalchemy import func, select

from app.models.entry import Entry
from app.repositories.models import EntryData, EntryPageData
from app.repositories.sql.converters import entry_to_data


class SQLEntryRepo:
    def __init__(self, session_factory) -> None:
        self._factory = session_factory

    async def get(self, entry_id: int) -> EntryData | None:
        async with self._factory() as session:
            entry = await session.get(Entry, entry_id)
            return entry_to_data(entry) if entry is not None else None

    async def create(
        self,
        *,
        waitlist_id: int,
        data: dict,
        email: str | None,
        referrer: str | None,
    ) -> EntryData:
        async with self._factory() as session:
            entry = Entry(
                waitlist_id=waitlist_id,
                data=data,
                email=email,
                referrer=referrer,
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return entry_to_data(entry)

    async def list_by_waitlist(
        self, waitlist_id: int, *, skip: int = 0, limit: int = 50
    ) -> EntryPageData:
        async with self._factory() as session:
            count_q = select(func.count(Entry.id)).where(Entry.waitlist_id == waitlist_id)
            total = (await session.execute(count_q)).scalar_one()
            query = (
                select(Entry)
                .where(Entry.waitlist_id == waitlist_id)
                .order_by(Entry.created_at.desc())
                .offset(skip)
            )
            if limit > 0:
                query = query.limit(limit)
            result = await session.execute(query)
            items = [entry_to_data(e) for e in result.scalars().all()]
            return EntryPageData(items=items, total=total)

    async def data_keys(self, waitlist_id: int, *, batch_size: int = 1000) -> list[str]:
        data_keys: list[str] = []
        seen: set[str] = set()
        async for batch in self.iterate_by_waitlist(waitlist_id, batch_size=batch_size):
            for entry in batch:
                for key in entry.data:
                    if key not in seen:
                        seen.add(key)
                        data_keys.append(key)
        return data_keys

    async def iterate_by_waitlist(self, waitlist_id: int, *, batch_size: int = 1000):
        last_id = 0
        while True:
            async with self._factory() as session:
                result = await session.execute(
                    select(Entry)
                    .where(Entry.waitlist_id == waitlist_id, Entry.id > last_id)
                    .order_by(Entry.id)
                    .limit(batch_size)
                )
                entries = result.scalars().all()
            if not entries:
                break
            yield [entry_to_data(e) for e in entries]
            last_id = entries[-1].id

    async def mark_email_notified(self, entry_id: int) -> None:
        async with self._factory() as session:
            entry = await session.get(Entry, entry_id)
            if entry is None:
                return
            entry.notified_email = True
            await session.commit()

    async def mark_webhook_notified(self, entry_id: int) -> None:
        async with self._factory() as session:
            entry = await session.get(Entry, entry_id)
            if entry is None:
                return
            entry.notified_webhook = True
            await session.commit()
