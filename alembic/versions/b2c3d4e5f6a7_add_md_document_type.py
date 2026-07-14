"""add md to document_type enum

Revision ID: b2c3d4e5f6a7
Revises: 12afebdd90a9
Create Date: 2026-03-26

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "12afebdd90a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL: extend enum used by documents.file_type
    op.execute(sa.text("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'md'"))


def downgrade() -> None:
    # Enum values cannot be dropped safely in PostgreSQL without recreating the type.
    pass
