from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EntryCreate(BaseModel):
    """Free-form entry data. Accepts any JSON fields — all are captured into ``data``.

    The ``email`` and ``referrer`` fields are extracted from the body at the
    service layer if present. No schema validation beyond size limits.
    """

    model_config = ConfigDict(extra="allow")

    data: dict = Field(default_factory=dict, max_length=65536)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="before")
    @classmethod
    def capture_all_fields_as_data(cls, values: dict) -> dict:
        """Wrap the entire payload into ``data`` so no fields are lost."""
        if isinstance(values, dict):
            # If `data` is explicitly provided at the top level, use it as-is
            # but still merge in any sibling fields so nothing is dropped.
            if "data" in values and isinstance(values["data"], dict):
                merged = dict(values["data"])
                for k, v in values.items():
                    if k != "data":
                        merged[k] = v
                values["data"] = merged
            else:
                values["data"] = {k: v for k, v in values.items()}
            # The Turnstile token is a verification concern, not lead data.
            values["data"].pop("turnstile_token", None)
        return values


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
