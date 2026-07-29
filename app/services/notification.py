from __future__ import annotations

import logging
from email.mime.text import MIMEText

import httpx

from app.config import get_settings
from app.database import _SessionFactory
from app.models.entry import Entry

logger = logging.getLogger(__name__)


async def notify_new_entry(entry_id: int) -> None:
    """Dispatch email and webhook notifications for a new entry.

    Runs as a FastAPI BackgroundTask — creates its own DB session so it's
    fully independent of the request lifecycle. Failures are logged but
    never propagated.
    """
    async with _SessionFactory() as session:
        entry = await session.get(Entry, entry_id)
        if entry is None:
            logger.warning("notify_new_entry: entry %d not found", entry_id)
            return

        settings = get_settings()

        if settings.notify_email_to and not entry.notified_email:
            try:
                await _send_email(settings, entry)
                entry.notified_email = True
                logger.info(
                    "Email sent to %s for entry %d",
                    settings.notify_email_to,
                    entry.id,
                )
            except Exception:
                logger.exception("Failed to send email for entry %d", entry.id)

        if settings.webhook_url and not entry.notified_webhook:
            try:
                await _send_webhook(settings, entry)
                entry.notified_webhook = True
                logger.info("Webhook sent for entry %d", entry.id)
            except Exception:
                logger.exception("Failed to send webhook for entry %d", entry.id)

        await session.commit()


async def _send_email(settings, entry: Entry) -> None:
    """Send notification email via SMTP."""
    subject = f"New waitlist entry #{entry.id}"
    body = (
        f"A new entry has been submitted.\n\n"
        f"Entry ID: {entry.id}\n"
        f"Waitlist ID: {entry.waitlist_id}\n"
        f"Email: {entry.email or '—'}\n"
        f"Referrer: {entry.referrer or '—'}\n"
        f"Data: {entry.data!s}\n"
    )

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = settings.notify_email_to

    if settings.smtp_host:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_port == 587,
            timeout=15,
        )
    else:
        logger.info(
            "SMTP not configured — would send email to %s: %s",
            settings.notify_email_to,
            subject,
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
