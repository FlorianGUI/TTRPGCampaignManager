import os
from collections.abc import AsyncGenerator
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TimestampedModel:
    """When a record was made, and when it was last written.

    Opted into rather than folded into `Base`, and the distinction is the point. The
    four tables in the user context already carry timestamps built for a purpose —
    `expires_at`, `used_at`, `revoked_at` — and a generic pair means something different
    beside those. Putting this on `Base` would give them columns nobody asked for and
    quietly change what inheriting from `Base` says. Here, the class line of a model
    states whether it keeps a record of itself.

    No `server_default` and no `onupdate`: **the domain writes both values** (#78). The
    entity sets them on construction and moves `updated_at` when it is revised, so an
    entity is complete the moment it exists rather than after a round trip, and the
    value is testable without a database. The consequence to know is that a row written
    by hand or by a migration gets no timestamp for free — the backfill in the migration
    that added these columns is the one place that had to say `now()` itself.

    `timezone=True` throughout: naive timestamps in a table read by people in different
    rooms is a bug waiting for the first person on a different offset.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
