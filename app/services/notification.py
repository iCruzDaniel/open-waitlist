"""Background notification tasks for new entries.

Notifications run as FastAPI BackgroundTasks — they never add latency to the
response and their failure never propagates to the client.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from app.config import get_settings

if TYPE_CHECKING:
    from app.models.entry import Entry

logger = logging.getLogger(__name__)


async def notify_new_entry(entry: Entry) -> None:
    """Dispatch email notification and webhook for a new entry.

    Both notifications are fire-and-forget. Failures are logged but never
    raise an exception.
    """
    settings = get_settings()

    if settings.notify_email_to:
        try:
            await _send_email_notification(settings, entry)
            logger.info("Email notification sent for entry %d", entry.id)
        except Exception:
            logger.exception("Failed to send email notification for entry %d", entry.id)

    if settings.webhook_url:
        try:
            await _send_webhook(settings, entry)
            logger.info("Webhook sent for entry %d", entry.id)
        except Exception:
            logger.exception("Failed to send webhook for entry %d", entry.id)


async def _send_email_notification(settings, entry: Entry) -> None:
    """Placeholder for actual SMTP delivery.

    For the MVP this logs the intention. Real SMTP integration will be added
    when an outgoing SMTP server is configured.
    """
    logger.info(
        "Would send email to %s about entry %d in waitlist %d",
        settings.notify_email_to,
        entry.id,
        entry.waitlist_id,
    )


async def _send_webhook(settings, entry: Entry) -> None:
    """POST entry payload to the configured webhook URL."""
    payload = {
        "event": "entry.created",
        "entry_id": entry.id,
        "waitlist_id": entry.waitlist_id,
        "email": entry.email,
        "data": entry.data,
        "referrer": entry.referrer,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.webhook_url,
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
