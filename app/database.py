import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tenacity import (
    after_log,
    before_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

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


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    after=after_log(logger, logging.WARNING),
    before=before_log(logger, logging.INFO),
    reraise=True,
)
async def wait_for_db() -> None:
    """Retry DB connection with exponential backoff.

    Called during app startup so the container can wait for Postgres
    to become available without depending on container ordering.
    """
    async with _SessionFactory() as session:
        await session.execute(text("SELECT 1"))
        logger.info("Database connection established")
