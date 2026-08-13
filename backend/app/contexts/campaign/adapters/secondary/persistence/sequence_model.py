import uuid

from sqlalchemy import Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampedModel


class SequenceModel(Base, TimestampedModel):
    __tablename__ = "sequences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # Nullable because the levels are skippable: a sequence sits under an act or directly
    # under the campaign. NULL is not a missing value here, it is the campaign — which is
    # why nothing treats it as one.
    #
    # Indexed because the common read is "the sequences of this act", and because
    # `last_position_under` filters on it for every sequence created.
    act_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    # Sparse, and scoped to `act_id` rather than to the campaign — see the port. Two
    # sequences under different acts may share a number and nothing is wrong.
    position: Mapped[int] = mapped_column(Integer)
