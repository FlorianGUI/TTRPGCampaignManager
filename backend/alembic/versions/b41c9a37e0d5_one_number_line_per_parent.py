"""one number line per parent

Revision ID: b41c9a37e0d5
Revises: f2489adf7cf7
Create Date: 2026-08-14

A data migration for #101. The code now treats a sibling group as everything under one
parent, whatever kind it is; the rows written before it did are still on two number
lines, and a sequence and a scene in the same act can both be sitting on 1024.

New placements would sort that out one group at a time, as a game master happened to
reorder things. This does it for every group at once, so a campaign nobody touches again
is still ordered rather than tied.

**Rows that had an order keep it. Rows that were tied get one.**

Each group is renumbered in `(position, id)` order, so anything whose position already
said where it went stays exactly where it was — the story a game master wrote is not
resorted underneath them.

Tied rows are the ones this exists for, and there is nothing to preserve about them: two
records on the same number were never in a recorded order, only in whatever order
something happened to sort their uuids in. That is not stable even between the two halves
of this app — Postgres compares uuids by their bytes, and the client's `localeCompare`
runs ICU collation, which does not treat a hyphen as a character. So a tie may come out of
this on the other side of its neighbour from where one browser last drew it. That is the
defect being fixed rather than a cost of fixing it: before today no one could have moved
it back, and now they can.

`downgrade` is a no-op and says so. The old scheme is not a state to return to: it did not
record which of two tied rows came first, so there is nothing to put back. Nothing about
these values is invalid under the old code either — it read the same column and ignored
the other table — so going back needs no undo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b41c9a37e0d5"
down_revision: str | Sequence[str] | None = "f2489adf7cf7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POSITION_GAP = 1024

# The three groups a parent can be, as the union of what it holds. Each row carries the
# table it came from so the UPDATE below can find it again, and the key it is grouped by.
#
# `ORDER BY position, id` inside the window is the whole promise of this migration: it is
# the order the tree was already being drawn in.
GROUPS = """
WITH members AS (
    SELECT 'act' AS kind, id, campaign_id::text AS parent, position FROM acts
    UNION ALL
    SELECT 'sequence', id, COALESCE(act_id::text, 'campaign:' || campaign_id::text), position FROM sequences
    UNION ALL
    SELECT 'scene', id,
           COALESCE(sequence_id::text, act_id::text, 'campaign:' || campaign_id::text),
           position
    FROM scenes
),
-- An act's parent is its campaign, and a campaign-level sequence or scene names the same
-- thing a different way; both spellings have to land in one bucket or the acts renumber
-- on their own again.
grouped AS (
    SELECT kind, id,
           CASE WHEN kind = 'act' THEN 'campaign:' || parent ELSE parent END AS parent,
           position
    FROM members
),
placed AS (
    SELECT kind, id,
           ROW_NUMBER() OVER (PARTITION BY parent ORDER BY position, id) * :gap AS fresh
    FROM grouped
)
"""


def upgrade() -> None:
    for table, kind in (("acts", "act"), ("sequences", "sequence"), ("scenes", "scene")):
        op.execute(
            sa.text(
                f"{GROUPS}"  # noqa: S608 - `table` and `kind` are the literals above, not input
                f"UPDATE {table} SET position = placed.fresh "
                f"FROM placed WHERE placed.id = {table}.id AND placed.kind = '{kind}'"
            ).bindparams(gap=POSITION_GAP)
        )


def downgrade() -> None:
    """Deliberately nothing — see the note at the top of this file."""
