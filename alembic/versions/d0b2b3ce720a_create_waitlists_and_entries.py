"""create waitlists and entries

Revision ID: d0b2b3ce720a
Revises:
Create Date: 2026-07-28 20:46:18.523813
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0b2b3ce720a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "waitlists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_waitlist_slug"),
    )
    op.create_index(op.f("ix_waitlists_slug"), "waitlists", ["slug"], unique=True)
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("waitlist_id", sa.Integer(), nullable=False),
        sa.Column(
            "data", sa.JSON(), nullable=False
        ),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("referrer", sa.String(length=1024), nullable=True),
        sa.Column("notified_email", sa.Boolean(), nullable=False),
        sa.Column("notified_webhook", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["waitlist_id"], ["waitlists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_entries_email"), "entries", ["email"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_entries_email"), table_name="entries")
    op.drop_table("entries")
    op.drop_index(op.f("ix_waitlists_slug"), table_name="waitlists")
    op.drop_table("waitlists")
