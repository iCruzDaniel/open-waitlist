from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class WaitlistData:
    id: int
    slug: str
    title: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    entry_count: int = 0


@dataclass
class EntryData:
    id: int
    waitlist_id: int
    data: dict[str, Any]
    email: str | None
    referrer: str | None
    notified_email: bool
    notified_webhook: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class AdminData:
    id: int
    email: str
    password_hash: str
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class EntryPageData:
    items: list[EntryData]
    total: int
