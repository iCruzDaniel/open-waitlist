"""Unit tests for the Redis repository layer using an in-memory fake client."""

from __future__ import annotations

import pytest

from app.repositories.redis.admin import RedisAdminRepo
from app.repositories.redis.entry import RedisEntryRepo
from app.repositories.redis.keys import RedisKeys
from app.repositories.redis.store import RedisStore
from app.repositories.redis.waitlist import RedisWaitlistRepo
from tests.fake_redis import FakeRedis


@pytest.fixture
def store() -> RedisStore:
    client = FakeRedis()
    keys = RedisKeys("testorg")
    return RedisStore(client, keys)


@pytest.fixture
def waitlists(store: RedisStore) -> RedisWaitlistRepo:
    return store.waitlists


@pytest.fixture
def entries(store: RedisStore) -> RedisEntryRepo:
    return store.entries


@pytest.fixture
def admins(store: RedisStore) -> RedisAdminRepo:
    return store.admins


async def test_waitlist_create_and_get(waitlists: RedisWaitlistRepo) -> None:
    wl = await waitlists.create(slug="launch", title="Launch", description="Desc")
    assert wl.id == 1
    fetched = await waitlists.get_by_slug("launch")
    assert fetched is not None
    assert fetched.slug == "launch"
    assert fetched.title == "Launch"
    assert fetched.description == "Desc"
    assert fetched.is_active is True


async def test_waitlist_get_missing(waitlists: RedisWaitlistRepo) -> None:
    assert await waitlists.get_by_slug("nope") is None


async def test_waitlist_inactive_hidden(waitlists: RedisWaitlistRepo) -> None:
    await waitlists.create(slug="a", title="A", description=None)
    await waitlists.soft_delete("a")
    assert await waitlists.get_by_slug("a") is None
    assert await waitlists.get_by_slug("a", include_inactive=True) is not None


async def test_waitlist_update(waitlists: RedisWaitlistRepo) -> None:
    await waitlists.create(slug="a", title="A", description=None)
    updated = await waitlists.update("a", title="B", description="new")
    assert updated is not None
    assert updated.title == "B"
    assert updated.description == "new"


async def test_waitlist_touch_active_reactivates(waitlists: RedisWaitlistRepo) -> None:
    await waitlists.create(slug="a", title="A", description=None)
    await waitlists.soft_delete("a")
    reactivated = await waitlists.touch_active("a")
    assert reactivated is not None
    assert reactivated.is_active is True
    assert await waitlists.get_by_slug("a") is not None


async def test_waitlist_list(store: RedisStore) -> None:
    repo = store.waitlists
    await repo.create(slug="b", title="B", description=None)
    await repo.create(slug="a", title="A", description=None)
    items = await repo.list()
    assert [w.slug for w in items] == ["a", "b"]  # newest first


async def test_entry_create_and_list(store: RedisStore) -> None:
    wl = await store.waitlists.create(slug="launch", title="Launch", description=None)
    await store.entries.create(
        waitlist_id=wl.id, data={"email": "a@b.com", "name": "A"}, email="a@b.com", referrer=None
    )
    await store.entries.create(
        waitlist_id=wl.id, data={"email": "c@d.com"}, email="c@d.com", referrer="twitter"
    )
    page = await store.entries.list_by_waitlist(wl.id, skip=0, limit=50)
    assert page.total == 2
    # Newest first
    assert page.items[0].id == 2
    assert page.items[1].id == 1


async def test_entry_pagination(store: RedisStore) -> None:
    wl = await store.waitlists.create(slug="launch", title="Launch", description=None)
    for i in range(5):
        await store.entries.create(
            waitlist_id=wl.id, data={"email": f"u{i}@b.com"}, email=f"u{i}@b.com", referrer=None
        )
    page = await store.entries.list_by_waitlist(wl.id, skip=1, limit=3)
    assert page.total == 5
    assert len(page.items) == 3
    assert [e.id for e in page.items] == [4, 3, 2]


async def test_entry_get_and_notify_flags(store: RedisStore) -> None:
    wl = await store.waitlists.create(slug="launch", title="Launch", description=None)
    entry = await store.entries.create(waitlist_id=wl.id, data={}, email=None, referrer=None)
    assert entry.notified_email is False
    await store.entries.mark_email_notified(entry.id)
    await store.entries.mark_webhook_notified(entry.id)
    fetched = await store.entries.get(entry.id)
    assert fetched is not None
    assert fetched.notified_email is True
    assert fetched.notified_webhook is True


async def test_data_keys(store: RedisStore) -> None:
    wl = await store.waitlists.create(slug="launch", title="Launch", description=None)
    await store.entries.create(
        waitlist_id=wl.id,
        data={"email": "a@b.com", "name": "A", "role": "dev"},
        email=None,
        referrer=None,
    )
    await store.entries.create(
        waitlist_id=wl.id, data={"email": "c@d.com", "role": "pm"}, email=None, referrer=None
    )
    keys = await store.entries.data_keys(wl.id)
    assert set(keys) == {"email", "name", "role"}


async def test_store_healthcheck(store: RedisStore) -> None:
    assert await store.healthcheck() is True


async def test_admin_create_and_by_email(store: RedisStore) -> None:
    admin = await store.admins.create(email="Admin@Example.com", password_hash="hash")
    assert admin.id == 1
    # Email lookup is normalized to lowercase
    fetched = await store.admins.get_by_email("admin@example.com")
    assert fetched is not None
    assert fetched.email == "Admin@Example.com"
    assert fetched.password_hash == "hash"


async def test_admin_count_and_by_id(store: RedisStore) -> None:
    await store.admins.create(email="a@b.com", password_hash="h1")
    await store.admins.create(email="c@d.com", password_hash="h2")
    assert await store.admins.count() == 2
    second = await store.admins.get_by_id(2)
    assert second is not None
    assert second.email == "c@d.com"
