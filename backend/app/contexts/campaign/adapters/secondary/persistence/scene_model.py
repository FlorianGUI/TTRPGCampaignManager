import uuid

from sqlalchemy import Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampedModel


class SceneModel(Base, TimestampedModel):
    __tablename__ = "scenes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    # Text and not null, defaulting to empty: a scene that has been named but not yet
    # written is the normal state of most of a campaign, and `NULL` and `""` would be the
    # same thing said two ways.
    #
    # Nothing here knows this column has a dialect (#53). It is stored and handed back
    # byte for byte — see app/common/markdown.py for why that is a rule and not an
    # oversight.
    body: Mapped[str] = mapped_column(Text, default="")
    # The status as the game master marks it, as text rather than a native enum: adding a
    # value to a PostgreSQL enum is a migration, and this list is not settled enough to
    # pay that. The domain's StrEnum is the authority, and _to_domain is where a value
    # from the table is held to it.
    status: Mapped[str] = mapped_column(String(16))
    # Not a foreign key, matching characters.campaign_id and campaigns.owner_id. Deleting
    # a campaign deletes the scenes in it — an application rule carried out by
    # CampaignService, not an ON DELETE CASCADE.
    campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # The parent, and at most one of these is ever set — see `Scene.__post_init__` for why
    # storing both would be a scene with two answers to where it lives. Both NULL is the
    # campaign itself, which is a parent rather than the absence of one.
    #
    # Only the *direct* parent is stored. A scene under a sequence does not also record
    # that sequence's act: the act is reached by looking, not by a copy kept here that
    # could disagree with the sequence after a move.
    act_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    sequence_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    # Sparse: see domain/position.py. No unique constraint on (campaign_id, position) on
    # purpose — the scheme tolerates a tie and `find_all_in` breaks one by id, whereas a
    # constraint would turn a harmless collision between two scenes created in the same
    # millisecond into a 500.
    position: Mapped[int] = mapped_column(Integer)
