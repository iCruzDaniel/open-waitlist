"""Test configuration — override settings and DB session for tests."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth.service import hash_password
from app.database import get_session
from app.main import app
from app.middleware.rate_limit import limiter
from app.models import Admin, Base
from app.services.export import ExportJobManager

_TEST_DB_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Create tables, seed admin, override DB, return test client."""
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed the default admin
    async with factory() as session:
        admin = Admin(
            email="admin@example.com",
            password_hash=hash_password("changeme-admin-password"),
        )
        session.add(admin)
        await session.commit()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Reset the global slowapi rate-limit storage so each test starts clean
    limiter.reset()

    # Set up export manager with test session factory and temp export dir
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    app.state.export_manager = ExportJobManager(
        export_dir=export_dir,
        ttl_minutes=60,
        session_factory=factory,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Get JWT token for admin user (cached per test session)."""
    response = await client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "changeme-admin-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def admin_headers(admin_token: str) -> dict[str, str]:
    """Get JWT auth headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}
