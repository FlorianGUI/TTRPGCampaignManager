"""scene status played becomes done

Revision ID: f2489adf7cf7
Revises: 6f268e8ba0a7
Create Date: 2026-08-14

A data migration, not a schema one — `scenes.status` is a `String(16)` precisely so
that changing the set of values it holds costs an UPDATE rather than an ALTER TYPE.
That was the reason given for not using a native enum, and this is the first time it
has been collected on.

Nothing is lost either way, so `downgrade` is exact: `played` and `done` are the same
state under two names, and `skipped` is untouched in both directions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2489adf7cf7"
down_revision: str | Sequence[str] | None = "6f268e8ba0a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE scenes SET status = 'done' WHERE status = 'played'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE scenes SET status = 'played' WHERE status = 'done'"))
