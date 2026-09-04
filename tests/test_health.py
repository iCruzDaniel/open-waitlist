"""Tests for the /health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Safe deployment diagnostics (no secrets): whether the admin panel flag is
    # on and which dist paths exist in the runtime filesystem.
    diag = body["admin_panel"]
    assert isinstance(diag["enabled"], bool)
    assert isinstance(diag["dist_found"], bool)
    assert isinstance(diag["dist_paths"], list)
    # dist_found must be consistent with the resolved paths.
    assert diag["dist_found"] == bool(diag["dist_paths"])


@pytest.mark.anyio
async def test_health_has_security_headers() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/nonexistent-route")
    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.anyio
async def test_request_body_too_large() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        large_str = "x" * 2_200_000  # >2MB raw, well over 1MB limit
        response = await client.post(
            "/waitlists/test/entries",
            content=large_str,
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 413
