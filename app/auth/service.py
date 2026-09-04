from __future__ import annotations

import bcrypt

from app.config import get_settings
from app.repositories.models import AdminData


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def bootstrap_admin(store) -> AdminData:
    """Create the initial admin from .env settings if none exists."""
    settings = get_settings()
    existing = await store.admins.get_by_email(settings.admin_email)
    if existing is not None:
        return existing

    return await store.admins.create(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
    )


async def authenticate_admin(store, email: str, password: str) -> AdminData | None:
    admin = await store.admins.get_by_email(email)
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


async def get_admin_by_id(store, admin_id: int) -> AdminData | None:
    return await store.admins.get_by_id(admin_id)
