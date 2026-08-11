"""records gain created and updated times

Revision ID: b41f7c9d2e05
Revises: 86ebc562d0b0
Create Date: 2026-08-11 14:05:11.902314

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b41f7c9d2e05"
down_revision: Union[str, Sequence[str], None] = "86ebc562d0b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The three tables that gain a record of themselves (#78). The user context's four are
# deliberately not here: they already carry timestamps built for a purpose — expires_at,
# used_at, revoked_at — and a generic pair means something different beside those.
TABLES = ("campaigns", "sources", "characters")


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        for column in ("created_at", "updated_at"):
            # Added with a server default and then stripped of it, in that order and for
            # two different reasons.
            #
            # The default is how existing rows come out of this migration non-null. It
            # backfills every one of them to the moment the migration ran, which is
            # untrue — those campaigns were made earlier — but it is untrue in a way
            # that keeps the column NOT NULL and every consumer free of an Optional.
            # The alternative, a nullable column, pushes that None all the way into the
            # API schemas for the sake of rows nobody has looked at.
            #
            # Then it goes, because the application is the only thing that should be
            # writing these. #78 put the clock in the domain: an entity knows its own
            # timestamps the moment it is constructed. A column default left in place
            # would be a second, silent writer for any INSERT that omits the value, and
            # the two would disagree by a round trip.
            op.add_column(
                table,
                sa.Column(column, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            )
            op.alter_column(table, column, server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        for column in ("updated_at", "created_at"):
            op.drop_column(table, column)
