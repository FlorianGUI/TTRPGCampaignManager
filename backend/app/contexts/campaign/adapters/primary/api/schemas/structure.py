from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.common.markdown import CampaignMarkdown
from app.contexts.campaign.domain.placement import NarrativeItem, NarrativeKind, Placement
from app.contexts.campaign.domain.scene import SceneStatus


class StructureAct(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    position: int
    created_at: datetime
    updated_at: datetime


class StructureSequence(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    act_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime


class StructureScene(BaseModel):
    """A scene as the tree sees it. **No `body`, and that is the point of the endpoint.**

    Not an omission a caller should work around by fetching each scene: a body is read one
    at a time, on the page that shows it. An outline that wanted a preview of each would
    have to compute it on the client from bodies it already holds — see #80 for why
    deriving one here would mean the API learning the #53 dialect.
    """

    id: UUID
    title: str
    status: SceneStatus
    act_id: UUID | None
    sequence_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime


class StructureResponse(BaseModel):
    """The campaign's tree as three ordered lists. See `Structure` for why it is flat.

    `campaign_id` is not repeated on every row. One request is one campaign — it is in the
    path, every row in the answer belongs to it, and saying so a few hundred times would
    only invite a client to trust a copy instead of the request it made.
    """

    acts: list[StructureAct]
    sequences: list[StructureSequence]
    scenes: list[StructureScene]


# Which parents each level may hang off. The campaign is `None` everywhere and so is not
# listed: #80's levels are skippable, and a scene on the campaign is as legitimate as one
# three levels down.
_PARENTS: dict[NarrativeKind, set[NarrativeKind]] = {
    NarrativeKind.ACT: set(),
    NarrativeKind.SEQUENCE: {NarrativeKind.ACT},
    NarrativeKind.SCENE: {NarrativeKind.ACT, NarrativeKind.SEQUENCE},
}


class StructureItem(BaseModel):
    """One row of the outline: which it is, and which kind of row it is.

    The kind is not decoration. `ActId` and friends are `NewType`s over `UUID`, so they
    are indistinguishable once the program runs — without this field the service would
    have to guess a row's level by querying all three repositories for it.
    """

    id: UUID
    kind: NarrativeKind

    def to_domain(self) -> NarrativeItem:
        return NarrativeItem(id=self.id, kind=self.kind)


class StructurePlacement(BaseModel):
    """A drop: the row that moved, the parent it landed in, and the sibling above it.

    `parent` null is the campaign itself; `after` null is the head of the list. Neither is
    a missing value — dropping a scene first in an empty act is an ordinary gesture and
    needs both nulls to say so.

    The combinations refused below are the ones #110 is about: the outline should not be
    able to ask for a move the tree has no meaning for, and finding that out here is a 422
    naming the field rather than a 404 that says only "not found".
    """

    item: StructureItem
    parent: StructureItem | None = None
    after: StructureItem | None = None

    @model_validator(mode="after")
    def _reject_impossible_moves(self) -> "StructurePlacement":
        if self.parent is not None and self.parent.kind not in _PARENTS[self.item.kind]:
            allowed = ", ".join(sorted(k.value for k in _PARENTS[self.item.kind])) or "nothing"
            raise ValueError(f"a {self.item.kind.value} hangs off {allowed} or the campaign")

        # Siblings are per level: an act is ordered among acts, a scene among scenes. That
        # sequences and scenes under one act are *not* ordered against each other is #101,
        # still open — this endpoint does not quietly decide it.
        if self.after is not None and self.after.kind is not self.item.kind:
            raise ValueError(f"a {self.item.kind.value} is placed after another {self.item.kind.value}")

        if self.after is not None and self.after.id == self.item.id:
            raise ValueError("a row cannot be placed after itself")

        return self

    def to_domain(self) -> Placement:
        return Placement(
            item=self.item.to_domain(),
            parent=self.parent.to_domain() if self.parent else None,
            after=self.after.to_domain() if self.after else None,
        )
