import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    # No foreign key to users: the contexts stay independent at the schema level too.
    #
    # Deleting a game master must delete their sources, but that cascade is a rule of
    # the application, not a constraint of the database — there is deliberately no
    # ON DELETE CASCADE here. Whichever use case deletes a user owns the job of
    # clearing the sources they own, and it does not exist yet: nothing anywhere can
    # delete a user today. Tracked in #12, along with the DELETE endpoints themselves.
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
