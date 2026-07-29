from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntryCreate(BaseModel):
    """Free-form entry data. No required fields — everything is optional.

    The ``data`` field stores the raw form payload; ``email`` is extracted at
    the service layer if present inside ``data`` or sent explicitly.
    """

    data: dict = Field(default_factory=dict, max_length=65536)


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    waitlist_id: int
    data: dict
    email: str | None = None
    referrer: str | None = Field(None, max_length=2000)
    created_at: datetime


class PaginatedEntries(BaseModel):
    items: list[EntryRead]
    total: int
    skip: int = 0
    limit: int = 50
