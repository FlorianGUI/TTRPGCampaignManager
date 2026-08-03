from typing import NewType
from uuid import UUID

# Every id its own type, because the bug they prevent is real and silent.
#
# This codebase passes adjacent same-typed UUIDs everywhere — `get_for(id, owner_id)`,
# `Character(owner_id=..., campaign_id=...)`, `CharacterAccess(campaign_id=..., viewer_id=...)`.
# Swapping any pair typechecks perfectly and produces a plausible, wrong answer that only
# a test would catch. Distinct types make each of those a mypy error, at no runtime cost:
# a NewType is its underlying UUID once the program runs.
#
# They live in common rather than in each context because they are referenced across
# contexts — a campaign's owner is a user — and the alternative is the campaign domain
# importing the user domain, which would be the first dependency between two contexts
# that have so far been kept apart down to the absence of foreign keys. Value types with
# no behaviour are exactly what `common` is for.
#
# Note these say nothing about authorisation. A `CampaignId` is any campaign's id, held
# by anyone; ids arrive from path parameters and database rows all day without anyone
# having been checked. Proving a viewer may *have* something is `Access` and `Unsafe`,
# and is a separate concern from naming what kind of thing it is.

UserId = NewType("UserId", UUID)
CampaignId = NewType("CampaignId", UUID)
CharacterId = NewType("CharacterId", UUID)
SourceId = NewType("SourceId", UUID)
RefreshTokenId = NewType("RefreshTokenId", UUID)
SessionId = NewType("SessionId", UUID)
