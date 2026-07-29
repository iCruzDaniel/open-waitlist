from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.waitlist import Waitlist


class Entry(TimestampMixin, Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    waitlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("waitlists.id", ondelete="CASCADE"), nullable=False
    )

    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    referrer: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    notified_email: Mapped[bool] = mapped_column(default=False, nullable=False)
    notified_webhook: Mapped[bool] = mapped_column(default=False, nullable=False)

    waitlist: Mapped[Waitlist] = relationship("Waitlist", back_populates="entries")
