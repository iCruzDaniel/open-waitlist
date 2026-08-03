"""Docs pages (/docs, /redoc) must be served from local assets, not CDNs.

The Content-Security-Policy middleware only allows same-origin resources
(``script-src 'self'``), so the docs pages can never reference jsdelivr or
run inline scripts.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.docs import STATIC_DIR
from app.config import get_settings
from app.main import create_app


def _docs_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("ENABLE_DOCS", "true")
    get_settings.cache_clear()
    docs_app = create_app()
    get_settings.cache_clear()
    return docs_app


@pytest.mark.anyio
async def test_docs_uses_only_local_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_docs_app(monkeypatch)),
        base_url="http://test",
    ) as client:
        response = await client.get("/docs")
    assert response.status_code == 200
    html = response.text
    assert "cdn.jsdelivr.net" not in html
    assert "fastapi.tiangolo.com" not in html
    assert "/static/swagger-ui/swagger-ui-bundle.js" in html
    assert "/static/swagger-ui/swagger-ui-standalone-preset.js" in html
    assert "/static/swagger-ui/swagger-ui.css" in html
    assert "/static/swagger-ui/swagger-init.js" in html
    # No inline <script> (would be blocked by script-src 'self')
    assert "<script>" not in html


@pytest.mark.anyio
async def test_redoc_uses_only_local_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_docs_app(monkeypatch)),
        base_url="http://test",
    ) as client:
        response = await client.get("/redoc")
    assert response.status_code == 200
    assert "cdn.jsdelivr.net" not in response.text
    assert "/static/redoc/redoc.standalone.js" in response.text
    assert "/openapi.json" in response.text


@pytest.mark.anyio
async def test_docs_static_assets_are_served(monkeypatch: pytest.MonkeyPatch) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_docs_app(monkeypatch)),
        base_url="http://test",
    ) as client:
        bundle = await client.get("/static/swagger-ui/swagger-ui-bundle.js")
        css = await client.get("/static/swagger-ui/swagger-ui.css")
        redoc = await client.get("/static/redoc/redoc.standalone.js")
        init = await client.get("/static/swagger-ui/swagger-init.js")
        openapi = await client.get("/openapi.json")
    assert bundle.status_code == 200
    assert "javascript" in bundle.headers["content-type"]
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert redoc.status_code == 200
    assert init.status_code == 200
    assert openapi.status_code == 200
    spec = openapi.json()
    assert spec["info"]["x-logo"] == {"url": "/static/swagger-ui/favicon.png"}
    assert "logo" not in spec["info"]


@pytest.mark.anyio
async def test_docs_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_DOCS", "false")
    get_settings.cache_clear()
    plain_app = create_app()
    get_settings.cache_clear()
    async with AsyncClient(
        transport=ASGITransport(app=plain_app),
        base_url="http://test",
    ) as client:
        assert (await client.get("/docs")).status_code == 404
        assert (await client.get("/redoc")).status_code == 404


def test_vendored_redoc_bundle_has_no_cdn_references() -> None:
    """ReDoc must not request cdn.redoc.ly (patched to the local favicon)."""
    bundle = (STATIC_DIR / "redoc" / "redoc.standalone.js").read_text()
    assert "cdn.redoc.ly" not in bundle
    assert "logo-mini.svg" not in bundle
    assert "/static/swagger-ui/favicon.png" in bundle
