from __future__ import annotations

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.admin import Admin


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def bootstrap_admin(session: AsyncSession) -> Admin:
    """Create the initial admin from .env settings if none exists."""
    settings = get_settings()
    result = await session.execute(select(Admin).limit(1))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    admin = Admin(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def authenticate_admin(
    session: AsyncSession, email: str, password: str
) -> Admin | None:
    result = await session.execute(
        select(Admin).where(Admin.email == email)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


async def get_admin_by_id(
    session: AsyncSession, admin_id: int
) -> Admin | None:
    result = await session.execute(select(Admin).where(Admin.id == admin_id))
    return result.scalar_one_or_none()
