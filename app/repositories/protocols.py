from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from app.repositories.models import AdminData, EntryData, EntryPageData, WaitlistData


@runtime_checkable
class WaitlistRepo(Protocol):
    async def get_by_slug(
        self, slug: str, *, include_inactive: bool = False
    ) -> WaitlistData | None: ...

    async def list(self, *, include_inactive: bool = False) -> list[WaitlistData]: ...

    async def create(self, *, slug: str, title: str, description: str | None) -> WaitlistData: ...

    async def update(
        self, slug: str, *, title: str | None = None, description: str | None = None
    ) -> WaitlistData | None: ...

    async def soft_delete(self, slug: str) -> WaitlistData | None: ...

    async def touch_active(self, slug: str) -> WaitlistData | None: ...


@runtime_checkable
class EntryRepo(Protocol):
    async def get(self, entry_id: int) -> EntryData | None: ...

    async def create(
        self,
        *,
        waitlist_id: int,
        data: dict,
        email: str | None,
        referrer: str | None,
    ) -> EntryData: ...

    async def list_by_waitlist(
        self, waitlist_id: int, *, skip: int = 0, limit: int = 50
    ) -> EntryPageData: ...

    async def data_keys(self, waitlist_id: int, *, batch_size: int = 1000) -> list[str]: ...

    async def iterate_by_waitlist(
        self, waitlist_id: int, *, batch_size: int = 1000
    ) -> AsyncIterator[list[EntryData]]: ...

    async def mark_email_notified(self, entry_id: int) -> None: ...

    async def mark_webhook_notified(self, entry_id: int) -> None: ...


@runtime_checkable
class AdminRepo(Protocol):
    async def get_by_email(self, email: str) -> AdminData | None: ...

    async def get_by_id(self, admin_id: int) -> AdminData | None: ...

    async def count(self) -> int: ...

    async def create(self, *, email: str, password_hash: str) -> AdminData: ...


class Store(Protocol):
    waitlists: WaitlistRepo
    entries: EntryRepo
    admins: AdminRepo

    async def healthcheck(self) -> bool: ...

    async def close(self) -> None: ...


def require(predicate: object, detail: str) -> None:
    if not predicate:
        raise ValueError(detail)
