"""Tests for the /health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_health_has_security_headers() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-xss-protection"] == "0"
    assert "referrer-policy" in response.headers
    assert "content-security-policy" in response.headers
    assert "permissions-policy" in response.headers


@pytest.mark.anyio
async def test_security_headers_on_404() -> None:
    """Non-existent routes should still get security headers."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/nonexistent-route")
    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"
