from uuid import UUID

from pydantic import BaseModel, Field

# The name's ceiling is the column's. `campaigns.name` is a `String(200)`, so a longer
# name travelled all the way to a database that cannot hold it and came back as a driver
# error — a 500 for the offence of typing too much. Stated here it is a 422 naming the
# field, which is the shape `CampaignForm` already knows how to place.
NAME_MAX_LENGTH = 200

# The description's ceiling is not the column's: that one is `Text` and would take a
# novel. This is a product limit — "a line introducing the table", in the form's own words
# — and it is sized for the reader it is waiting on. Nothing renders it today; #31 is what
# will, to introduce a campaign to someone deciding whether to join it, and a paragraph is
# the most that is worth reading in that moment.
DESCRIPTION_MAX_LENGTH = 1000


class CampaignCreate(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)


class CampaignUpdate(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)


class CampaignResponse(BaseModel):
    # No limits on the way out. They belong on what is accepted, not on what is read
    # back: a row already longer than a limit is a row that must still be readable, or
    # tightening one would strand the campaigns that were saved under the old one.
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
