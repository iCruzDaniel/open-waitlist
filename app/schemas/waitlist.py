from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WaitlistCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class WaitlistUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class WaitlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None
    entry_count: int = 0
