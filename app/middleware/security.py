import logging
from collections.abc import Awaitable, Callable

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds OWASP-recommended security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message.get("headers", []))
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("X-XSS-Protection", "0")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), microphone=(), geolocation=(), interest-cohort=()",
                )
                if settings.content_security_policy:
                    headers.setdefault(
                        "Content-Security-Policy",
                        settings.content_security_policy,
                    )
                message["headers"] = headers.raw
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestBodySizeMiddleware:
    """Reject requests with body larger than ``max_bytes``."""

    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int = 1_048_576,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = 0
        for header, value in scope.get("headers", []):
            if header == b"content-length":
                content_length = int(value)
                break

        if content_length > self.max_bytes:
            from fastapi.responses import PlainTextResponse

            response = PlainTextResponse(
                "Request body too large",
                status_code=413,
            )
            await response(scope, receive, send)
            return

        original_receive: Callable[[], Awaitable[Message]] = receive

        async def sized_receive() -> Message:
            msg = await original_receive()
            return msg

        await self.app(scope, sized_receive, send)


SENSITIVE_FIELDS = frozenset({
    "api_key", "API_KEY",
    "jwt_secret", "JWT_SECRET",
    "admin_password", "ADMIN_PASSWORD",
    "smtp_password", "SMTP_PASSWORD",
    "password",
    "password_hash",
    "secret",
    "token",
    "authorization",
    "x-api-key",
})


class SensitiveDataFilter(logging.Filter):
    """Redact sensitive field values from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "msg") or not isinstance(record.msg, str):
            return True

        for field in SENSITIVE_FIELDS:
            record.msg = record.msg.replace(field, f"{field[:4]}...")
            # Also redact values passed as args for %-style formatting
            if record.args:
                record.args = tuple(
                    str(a).replace(field, f"{field[:4]}...")
                    if isinstance(a, str) else a
                    for a in record.args
                )
        return True
