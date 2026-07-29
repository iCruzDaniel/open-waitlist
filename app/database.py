from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    echo=False,
)

_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionFactory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def dispose_engine() -> None:
    await _engine.dispose()
