"""Unit tests for the Cloudflare Turnstile verification service."""

import httpx
import pytest
from fastapi import HTTPException
from httpx import MockTransport

from app.config import Settings
from app.services.turnstile import SITEVERIFY_URL, verify_turnstile


def _settings(**overrides: object) -> Settings:
    return Settings(turnstile_secret_key="test-secret", **overrides)


@pytest.mark.anyio
async def test_dev_mode_skips_verification() -> None:
    """No secret key configured -> verification is a no-op, even without a token."""
    await verify_turnstile(None, settings=Settings(turnstile_secret_key=""))


@pytest.mark.anyio
async def test_missing_token_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile(None, settings=_settings())
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_valid_token_passes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == SITEVERIFY_URL
        body = request.content.decode()
        assert "secret=test-secret" in body
        assert "response=valid-token" in body
        assert "remoteip=1.2.3.4" in body
        return httpx.Response(200, json={"success": True})

    transport = MockTransport(handler)
    await verify_turnstile(
        "valid-token",
        remote_ip="1.2.3.4",
        settings=_settings(),
        transport=transport,
    )


@pytest.mark.anyio
async def test_invalid_token_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"success": False, "error-codes": ["invalid-input-response"]},
        )

    transport = MockTransport(handler)
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("bad-token", settings=_settings(), transport=transport)
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_upstream_error_fails_closed() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = MockTransport(handler)
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("token", settings=_settings(), transport=transport)
    assert exc.value.status_code == 503


@pytest.mark.anyio
async def test_hostname_not_allowed_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "hostname": "evil.com"})

    transport = MockTransport(handler)
    settings = _settings(turnstile_allowed_hostnames="good.com")
    with pytest.raises(HTTPException) as exc:
        await verify_turnstile("token", settings=settings, transport=transport)
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_allowed_hostname_passes() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "hostname": "good.com"})

    transport = MockTransport(handler)
    settings = _settings(turnstile_allowed_hostnames="good.com")
    await verify_turnstile("token", settings=settings, transport=transport)
