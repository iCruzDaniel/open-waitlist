"""Integration tests for demo mode (form route + lead submission)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.dependencies import get_store, reset_store_for_tests
from app.models import Base
from app.repositories.sql.store import SQLStore


def test_demo_html_has_fill_button() -> None:
    demo_dir = Path(__file__).resolve().parent.parent / "app" / "demo"
    html = (demo_dir / "index.html").read_text(encoding="utf-8")
    assert "fill-btn" in html
    assert "__SLUG__" in html  # placeholder for runtime substitution
    assert 'src="/demo.js"' in html  # external script (CSP blocks inline JS)
    # The submission logic lives in the external, same-origin script.
    js = (demo_dir / "demo.js").read_text(encoding="utf-8")
    assert "/waitlists/" in js


@pytest.fixture
async def app_with_demo():
    """Build a fresh app with demo_mode via create_app(), store overridden."""
    import app.main as main_module
    from app.config import Settings
    from app.main import create_app

    real_settings = main_module.get_settings
    main_module.get_settings = lambda: Settings(
        demo_mode=True,
        demo_slug="demo",
        admin_email="admin@example.com",
        admin_password="changeme-admin-password",
        turnstile_secret_key="",
    )
    app = create_app()
    main_module.get_settings = real_settings

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = SQLStore(factory)

    reset_store_for_tests()

    async def override_get_store() -> AsyncIterator[SQLStore]:
        yield store

    app.dependency_overrides[get_store] = override_get_store

    yield app, store

    app.dependency_overrides.clear()
    reset_store_for_tests()
    await engine.dispose()


@pytest.fixture
async def demo_client(app_with_demo) -> AsyncIterator[AsyncClient]:
    app, _store = app_with_demo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_demo_form_served(demo_client: AsyncClient) -> None:
    resp = await demo_client.get("/")
    assert resp.status_code == 200
    assert "fill-btn" in resp.text  # random-data button present
    assert "demo" in resp.text  # slug substituted into the form action


async def test_demo_form_submits_lead(app_with_demo, demo_client: AsyncClient) -> None:
    _app, store = app_with_demo

    from app.auth.service import hash_password

    await store.admins.create(
        email="admin@example.com", password_hash=hash_password("changeme-admin-password")
    )

    resp = await demo_client.post(
        "/waitlists/demo/entries",
        json={"name": "Ana", "email": "ana@example.com", "referrer": "demo-form"},
    )
    assert resp.status_code == 201

    login = await demo_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "changeme-admin-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    page = await demo_client.get("/waitlists/demo/entries", headers=headers)
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 1
    assert body["items"][0]["data"]["email"] == "ana@example.com"
