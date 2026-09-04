from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.repositories.protocols import Store
from app.repositories.redis.keys import RedisKeys
from app.repositories.redis.store import RedisStore
from app.repositories.sql.store import SQLStore

logger = logging.getLogger(__name__)

_store: Store | None = None
_engine = None
_session_factory = None


def _build_sql_engine(url: str):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    global _engine, _session_factory
    _engine = create_async_engine(url, pool_pre_ping=True, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def init_store() -> Store:
    """Create the global Store based on DATABASE_TYPE. Idempotent."""
    global _store
    if _store is not None:
        return _store

    settings = get_settings()

    if settings.database_type == "redis":
        from upstash_redis.asyncio import Redis as UpstashRedis

        client = UpstashRedis(url=settings.redis_url, token=settings.redis_token)
        keys = RedisKeys(settings.redis_namespace_org)
        _store = RedisStore(client, keys)
        logger.info("Store initialized: redis (org=%s)", settings.redis_namespace_org)
    else:
        factory = _build_sql_engine(settings.database_url)
        _store = SQLStore(factory)
        logger.info("Store initialized: %s", settings.database_type)

    return _store


def get_store_engine() -> object | None:
    return _engine


def get_session_factory():
    return _session_factory


async def close_store() -> None:
    global _store, _engine, _session_factory
    if _store is not None:
        await _store.close()
        _store = None
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None


async def wait_for_db(app) -> None:  # noqa: ARG001
    """Retry store connectivity with exponential backoff.

    For SQL backends this lets the app wait for Postgres to become available
    without depending on container ordering. For Redis it verifies the Upstash
    REST endpoint is reachable. Fails after 10 attempts.
    """
    import logging

    from tenacity import (
        after_log,
        before_log,
        retry,
        stop_after_attempt,
        wait_exponential,
    )

    logger = logging.getLogger(__name__)

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        after=after_log(logger, logging.WARNING),
        before=before_log(logger, logging.INFO),
        reraise=True,
    )
    async def _connect() -> None:
        store = await init_store()
        ok = await store.healthcheck()
        if not ok:
            raise ConnectionError("store healthcheck failed")
        logger.info("Database connection established")

    await _connect()


async def get_store() -> AsyncIterator[Store]:
    store = await init_store()
    yield store


StoreDep = Annotated[Store, Depends(get_store)]


def reset_store_for_tests() -> None:
    """Test helper: clear the cached global store."""
    global _store, _engine, _session_factory
    _store = None
    _engine = None
    _session_factory = None


# Re-export for convenience in routers/services
__all__ = [
    "Store",
    "StoreDep",
    "get_store",
    "init_store",
    "close_store",
    "wait_for_db",
    "get_session_factory",
    "get_store_engine",
    "reset_store_for_tests",
]
