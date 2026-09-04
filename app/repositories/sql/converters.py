from __future__ import annotations

from app.models.admin import Admin
from app.models.entry import Entry
from app.models.waitlist import Waitlist
from app.repositories.models import AdminData, EntryData, WaitlistData


def waitlist_to_data(wl: Waitlist, entry_count: int = 0) -> WaitlistData:
    has_entries = hasattr(wl, "entries") and wl.entries is not None
    return WaitlistData(
        id=wl.id,
        slug=wl.slug,
        title=wl.title,
        description=wl.description,
        is_active=wl.is_active,
        created_at=wl.created_at,
        updated_at=wl.updated_at,
        deleted_at=wl.deleted_at,
        entry_count=len(wl.entries) if has_entries else entry_count,
    )


def entry_to_data(entry: Entry) -> EntryData:
    return EntryData(
        id=entry.id,
        waitlist_id=entry.waitlist_id,
        data=entry.data,
        email=entry.email,
        referrer=entry.referrer,
        notified_email=entry.notified_email,
        notified_webhook=entry.notified_webhook,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def admin_to_data(admin: Admin) -> AdminData:
    return AdminData(
        id=admin.id,
        email=admin.email,
        password_hash=admin.password_hash,
        last_login_at=admin.last_login_at,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
    )
