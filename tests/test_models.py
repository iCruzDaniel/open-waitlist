"""Verify that models can be imported and DB session works."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from app.models import Base, Entry, Waitlist


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.mark.anyio
async def test_create_waitlist(session: AsyncSession) -> None:
    wl = Waitlist(slug="early-birds", title="Early Birds")
    session.add(wl)
    await session.commit()
    await session.refresh(wl)

    assert wl.id is not None
    assert wl.slug == "early-birds"
    assert wl.is_active is True
    assert wl.deleted_at is None
    assert wl.created_at is not None


@pytest.mark.anyio
async def test_create_entry(session: AsyncSession) -> None:
    wl = Waitlist(slug="test-list", title="Test List")
    session.add(wl)
    await session.commit()

    entry = Entry(waitlist_id=wl.id, data={"email": "a@b.com", "name": "Alice"})
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    assert entry.id is not None
    assert entry.data["email"] == "a@b.com"
    assert entry.notified_email is False


@pytest.mark.anyio
async def test_waitlist_entries_relationship(session: AsyncSession) -> None:
    wl = Waitlist(slug="rel-test", title="Rel Test")
    session.add(wl)
    await session.commit()

    for i in range(3):
        session.add(Entry(waitlist_id=wl.id, data={"n": i}))
    await session.commit()

    result = await session.execute(
        select(Waitlist)
        .where(Waitlist.slug == "rel-test")
        .options(selectinload(Waitlist.entries))
    )
    loaded = result.scalar_one()
    assert len(loaded.entries) == 3


@pytest.mark.anyio
async def test_entry_freeform_data(session: AsyncSession) -> None:
    wl = Waitlist(slug="freeform", title="Freeform")
    session.add(wl)
    await session.commit()

    payloads = [
        {"email": "a@b.com"},
        {"phone": "+1234567890", "country": "CO"},
        {},
        {"items": [1, 2, 3], "nested": {"key": "val"}},
    ]
    for data in payloads:
        session.add(Entry(waitlist_id=wl.id, data=data))
    await session.commit()

    result = await session.execute(
        select(Entry).where(Entry.waitlist_id == wl.id)
    )
    entries = list(result.scalars().all())
    assert len(entries) == 4
    assert entries[0].data == {"email": "a@b.com"}
    assert entries[3].data == {"items": [1, 2, 3], "nested": {"key": "val"}}
