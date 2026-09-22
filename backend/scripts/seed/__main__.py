"""Seed local dev data: a default user, a filled campaign, and a source.

Run with `just seed`. Idempotent — each module finds its own row by username or name
and does nothing further if it's already there, so this is safe to run again any time.

That idempotency is a floor, not a sync: editing `campaign.py`'s content does not
retroactively update a campaign this already created. For a genuinely clean slate —
schema included — use `just reset`, which drops the database volume, recreates it,
migrates, and re-seeds from scratch.
"""

import asyncio

from app.database import AsyncSessionLocal
from scripts.seed.campaign import seed_campaign
from scripts.seed.source import seed_source
from scripts.seed.user import PASSWORD, USERNAME, seed_user


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = await seed_user(db)
        print(f"User: {USERNAME} / {PASSWORD}")

        campaign, created = await seed_campaign(db, user.id)
        if created:
            print(f"Campaign '{campaign.name}' seeded: 2 acts, 1 sequence, 5 scenes, 2 characters.")
        else:
            print(f"Campaign '{campaign.name}' already exists — nothing more to seed.")

        if await seed_source(db, user.id):
            print("Source seeded.")


if __name__ == "__main__":
    asyncio.run(main())
