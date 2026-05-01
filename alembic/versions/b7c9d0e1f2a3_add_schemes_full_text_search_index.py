"""add schemes full text search index

Revision ID: b7c9d0e1f2a3
Revises: a3f8b2c1d4e5
Create Date: 2026-05-01 20:55:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c9d0e1f2a3"
down_revision: Union[str, None] = "a3f8b2c1d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_schemes_search_vector
        ON schemes
        USING gin (
            to_tsvector(
                'english',
                coalesce(name, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(ministry, '') || ' ' ||
                coalesce(category, '')
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_schemes_search_vector")
