from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
REQUEST_TIMEOUT = 5.0


class TurnstileVerifyResponse(BaseModel):
    success: bool
    challenge_ts: str | None = None
    hostname: str | None = None
    action: str | None = None
    cdata: str | None = None
    error_codes: list[str] | None = Field(default=None, alias="error-codes")


async def verify_turnstile(
    token: str | None,
    remote_ip: str | None = None,
    *,
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    """Verify a Turnstile token with Cloudflare's Siteverify API.

    No-op when no secret key is configured (dev mode). Fail-closed: missing
    or invalid tokens raise 400, upstream errors raise 503.
    """
    settings = settings or get_settings()
    if not settings.turnstile_secret_key:
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Turnstile token",
        )

    body: dict[str, str] = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        body["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=transport,
        ) as client:
            response = await client.post(SITEVERIFY_URL, data=body)
            result = TurnstileVerifyResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Turnstile siteverify request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification service unavailable",
        ) from None

    # A non-200 status means Cloudflare rejected the request itself (e.g. an
    # invalid or missing secret key) — a server misconfiguration, not a bad
    # visitor token. Fail closed and surface the error codes in the logs.
    if response.status_code != 200:
        logger.error(
            "Turnstile siteverify rejected the request (HTTP %s): error_codes=%s",
            response.status_code,
            result.error_codes,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification service unavailable",
        )

    if not result.success:
        logger.warning(
            "Turnstile verification failed: error_codes=%s hostname=%s",
            result.error_codes,
            result.hostname,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Turnstile verification failed",
        )

    if settings.turnstile_allowed_hostnames:
        allowed = {h.strip() for h in settings.turnstile_allowed_hostnames.split(",") if h.strip()}
        if not result.hostname or result.hostname not in allowed:
            logger.warning(
                "Turnstile token hostname not allowed: %s",
                result.hostname,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Turnstile verification failed",
            )
