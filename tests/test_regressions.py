"""Regression tests for bugs found during the Redis-abstraction review."""

from __future__ import annotations

import pytest
from httpx import Response

from app.dependencies import close_store, init_store, reset_store_for_tests
from app.models import Base

pytestmark = pytest.mark.anyio

_engine = None


async def _fresh_store(monkeypatch: pytest.MonkeyPatch, **settings_kwargs):
    """Point the settings symbols used by dependencies/config at an in-memory
    SQLite, build a fresh global store via init_store(), and create the schema on
    the store's own engine."""
    global _engine

    from app.config import Settings

    monkeypatch.setattr(
        "app.dependencies.get_settings",
        lambda: Settings(
            database_type="sqlite", database_url="sqlite+aiosqlite://", **settings_kwargs
        ),
    )
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: Settings(
            database_type="sqlite", database_url="sqlite+aiosqlite://", **settings_kwargs
        ),
    )
    monkeypatch.setattr(
        "app.services.notification.get_settings",
        lambda: Settings(
            database_type="sqlite", database_url="sqlite+aiosqlite://", **settings_kwargs
        ),
    )

    reset_store_for_tests()
    store = await init_store()

    from app.dependencies import get_store_engine

    engine = get_store_engine()
    _engine = engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return store


async def test_notify_new_entry_resolves_store_and_sends_webhook(monkeypatch) -> None:
    """Regression: notify_new_entry used `await get_store()` (an async generator),
    which raised TypeError and silently skipped webhooks/email notifications."""
    from app.services import notification as notif

    store = await _fresh_store(monkeypatch, webhook_url="http://webhook.test/hook")

    wl = await store.waitlists.create(slug="reactivate", title="Re", description=None)
    entry = await store.entries.create(
        waitlist_id=wl.id, data={"email": "a@b.c"}, email="a@b.c", referrer=None
    )

    called = []

    async def fake_post(_self, url, **_kwargs):
        called.append(url)
        return Response(200, json={})

    monkeypatch.setattr(notif.httpx.AsyncClient, "post", fake_post)

    await notif.notify_new_entry(entry.id)

    assert called, "webhook was not invoked — store resolution likely failed"

    await close_store()
    await _engine.dispose()
    reset_store_for_tests()


async def test_entry_post_reactivates_soft_deleted_waitlist(monkeypatch) -> None:
    """Regression: create_entry used get_by_slug (inactive filtered by default), so a
    POST to a soft-deleted slug created a duplicate waitlist instead of reactivating."""
    from app.schemas.entry import EntryCreate
    from app.services.entry import create_entry

    store = await _fresh_store(monkeypatch)

    wl = await store.waitlists.create(slug="w", title="W", description=None)
    await store.waitlists.soft_delete("w")
    assert (await store.waitlists.get_by_slug("w", include_inactive=True)).is_active is False

    entry = await create_entry(store, "w", EntryCreate(data={"email": "x@y.z"}))

    reactivated = await store.waitlists.get_by_slug("w", include_inactive=True)
    assert reactivated is not None
    assert reactivated.id == wl.id, "expected reactivation, not a duplicate waitlist"
    assert reactivated.is_active is True
    assert entry.waitlist_id == wl.id

    await close_store()
    await _engine.dispose()
    reset_store_for_tests()
