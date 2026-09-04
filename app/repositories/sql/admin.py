from __future__ import annotations

from sqlalchemy import func, select

from app.models.admin import Admin
from app.repositories.models import AdminData
from app.repositories.sql.converters import admin_to_data


class SQLAdminRepo:
    def __init__(self, session_factory) -> None:
        self._factory = session_factory

    async def get_by_email(self, email: str) -> AdminData | None:
        async with self._factory() as session:
            result = await session.execute(select(Admin).where(Admin.email == email))
            admin = result.scalar_one_or_none()
            return admin_to_data(admin) if admin is not None else None

    async def get_by_id(self, admin_id: int) -> AdminData | None:
        async with self._factory() as session:
            admin = await session.get(Admin, admin_id)
            return admin_to_data(admin) if admin is not None else None

    async def count(self) -> int:
        async with self._factory() as session:
            result = await session.execute(select(func.count(Admin.id)))
            return result.scalar_one()

    async def create(self, *, email: str, password_hash: str) -> AdminData:
        async with self._factory() as session:
            admin = Admin(email=email, password_hash=password_hash)
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            return admin_to_data(admin)
