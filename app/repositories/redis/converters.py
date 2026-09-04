from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.repositories.models import AdminData, EntryData, WaitlistData

_ISO_PREFIX = "iso:"
_JSON_PREFIX = "json:"


def _encode_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return _ISO_PREFIX + value.isoformat()
    if isinstance(value, (dict, list)):
        return _JSON_PREFIX + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _decode_value(raw: str | None, *, field_type: str = "str") -> Any:
    if raw is None or raw == "":
        return None
    if raw.startswith(_ISO_PREFIX):
        return datetime.fromisoformat(raw[len(_ISO_PREFIX) :])
    if raw.startswith(_JSON_PREFIX):
        return json.loads(raw[len(_JSON_PREFIX) :])
    if field_type == "int":
        return int(raw)
    if field_type == "bool":
        return raw == "true"
    return raw


def waitlist_to_hash(wl: WaitlistData) -> dict[str, str]:
    return {
        "id": str(wl.id),
        "slug": wl.slug,
        "title": wl.title,
        "description": wl.description or "",
        "is_active": "true" if wl.is_active else "false",
        "created_at": _encode_value(wl.created_at),
        "updated_at": _encode_value(wl.updated_at),
        "deleted_at": _encode_value(wl.deleted_at),
    }


def hash_to_waitlist(raw: dict[str, Any], *, entry_count: int = 0) -> WaitlistData:
    return WaitlistData(
        id=int(raw["id"]),
        slug=raw["slug"],
        title=raw["title"],
        description=raw.get("description") or None,
        is_active=raw.get("is_active", "true") == "true",
        created_at=_decode_value(raw.get("created_at")),
        updated_at=_decode_value(raw.get("updated_at")),
        deleted_at=_decode_value(raw.get("deleted_at")),
        entry_count=entry_count,
    )


def entry_to_hash(entry: EntryData) -> dict[str, str]:
    return {
        "id": str(entry.id),
        "waitlist_id": str(entry.waitlist_id),
        "data": _encode_value(entry.data),
        "email": entry.email or "",
        "referrer": entry.referrer or "",
        "notified_email": "true" if entry.notified_email else "false",
        "notified_webhook": "true" if entry.notified_webhook else "false",
        "created_at": _encode_value(entry.created_at),
        "updated_at": _encode_value(entry.updated_at),
    }


def hash_to_entry(raw: dict[str, Any]) -> EntryData:
    return EntryData(
        id=int(raw["id"]),
        waitlist_id=int(raw["waitlist_id"]),
        data=_decode_value(raw.get("data")),
        email=raw.get("email") or None,
        referrer=raw.get("referrer") or None,
        notified_email=raw.get("notified_email", "false") == "true",
        notified_webhook=raw.get("notified_webhook", "false") == "true",
        created_at=_decode_value(raw.get("created_at")),
        updated_at=_decode_value(raw.get("updated_at")),
    )


def admin_to_hash(admin: AdminData) -> dict[str, str]:
    return {
        "id": str(admin.id),
        "email": admin.email,
        "password_hash": admin.password_hash,
        "last_login_at": _encode_value(admin.last_login_at),
        "created_at": _encode_value(admin.created_at),
        "updated_at": _encode_value(admin.updated_at),
    }


def hash_to_admin(raw: dict[str, Any]) -> AdminData:
    return AdminData(
        id=int(raw["id"]),
        email=raw["email"],
        password_hash=raw["password_hash"],
        last_login_at=_decode_value(raw.get("last_login_at")),
        created_at=_decode_value(raw.get("created_at")),
        updated_at=_decode_value(raw.get("updated_at")),
    )


def utcnow() -> datetime:
    return datetime.now(UTC)
