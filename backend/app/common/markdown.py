from typing import Annotated

from pydantic import Field

# The syntax primer, kept apart from the annotation only so it stays readable.
#
# This is most of the alias's value and is written for a *reader that is not a
# person*. A generator handed `body: str` writes plain prose, and none of the
# design-system components ever appear; handed this, it knows the field has a
# dialect and what the dialect is. Every directive below is one the renderer
# actually implements — inventing syntax here would be worse than saying nothing,
# because the failure is silent: an unknown directive degrades to visible text.
#
# `scene` is deliberately absent from the entity list. #80 leaves adding it to
# `ENTITY_KINDS` open, and this primer follows that list rather than leading it.
_PRIMER = """\
Campaign Manager markdown: CommonMark, plus a small directive dialect.

Stored and returned byte for byte. Nothing here is parsed or validated by the
API — this description tells a writer what the renderer understands, and an
unrecognised directive simply shows as the text it was typed as.

Inline:
  :npc[Maerin Holt]                          a reference to a person
  :location[Greyfen Marsh]                   ...to a place
  :item[the rubbing]                         ...to a thing
  :monster[Owlbear]                          ...to a creature
  :faction[The Fen Wardens]                  ...to a group
  :session[Session 14]                       ...to a sitting at the table
  :dice[2d8 + 5]                             a roll
  :dice[1d20]{result=19 outcome=crit}        a roll that happened; outcome is
                                             `crit` or `fumble`, both optional
  :ref[Cities of the Vale]{page=88}          a source-book citation

Block:
  :::read-aloud
  Text the game master reads to the table.
  :::

  :::read-aloud{label="Boxed text"}          the heading can be renamed
  ...
  :::
"""

CampaignMarkdown = Annotated[
    str,
    Field(
        # The JSON Schema keyword that means exactly this. A bespoke `x-` extension
        # would carry the same string and mean nothing to any tool that read it.
        json_schema_extra={"contentMediaType": "text/x-campaign-markdown"},
        description=_PRIMER,
    ),
]
"""A field carrying the game master's markdown dialect (#53), opaque to the backend.

**A hint, never a validator**, and this has to be said out loud because a type that
looks like a format is an invitation to enforce it. Nothing in this module inspects a
value. `CampaignMarkdown` is `str` at runtime — the annotation adds a media type and a
primer to the generated schema and changes no behaviour at all.

Why it must stay that way, from #80: a scene body is *stored and handed back byte for
byte, no parsing, no validating of directives, no rendering*. The dialect in #53 is the
frontend's business and is expected to grow; a backend that validated it would turn every
new directive into a migration and a deploy, and a body written against a newer client
into a 422.

Two consequences worth keeping:

- **It carries nothing about rendering.** Whether a value is displayed as a block or
  inline belongs to the call site, not to the type.
- **It is not a place for a length cap.** A field that wants one says so itself; putting
  it here would make the dialect and the size limit the same decision, and they are not.

Carried by `Scene.body` and, from PR 2 of #80, by act and sequence descriptions.
"""
