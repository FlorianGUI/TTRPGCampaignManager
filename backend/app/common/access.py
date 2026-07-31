from abc import ABC, abstractmethod
from typing import ClassVar

from app.common.errors import NotAvailable


class Access[T](ABC):
    """What one viewer may do with one record, and what happens when the answer is no.

    This class holds no rules. All three questions are abstract on purpose: whether
    editing follows from reading is a decision each context has to make for itself, and
    a default here would be that decision made once, in a place no domain can see, for
    domains that have not been written yet. They agree today; #31 is expected to part
    them, and it should part them by changing a domain rather than by discovering an
    inherited answer.

    What is left here is only mechanism, and it is the same everywhere:

    - take `T | None`, because the record comes straight from a repository that may have
      found nothing. Absorbing that here is the point — a record that is absent and a
      record that is forbidden leave by the same door, so the caller cannot tell which
      it was, which is the whole of the 404 decision in #12;
    - hand back the record rather than a yes or no, so a caller cannot take the answer
      and forget to act on it;
    - raise the context's own exception, named by `not_available`, so each keeps its own
      wording and one handler turns any of them into a 404.

    A note on what these are *not*, because the subclasses differ in weight and a shared
    base flattens it. `CharacterAccess` is a capability: only `CampaignAccess.characters_at`
    produces one, so holding it is proof of something. `CampaignAccess` and `SourceAccess`
    are not — anyone can build one around any viewer id. They are rule-holders, and the
    rule is checked against the record, not against the fact that you are holding them.
    Do not read a bare `Access` in a signature as proof.
    """

    not_available: ClassVar[type[NotAvailable]]

    @abstractmethod
    def may_read(self, record: T) -> bool: ...

    @abstractmethod
    def may_edit(self, record: T) -> bool: ...

    @abstractmethod
    def may_delete(self, record: T) -> bool: ...

    def readable(self, record: T | None) -> T:
        if record is None or not self.may_read(record):
            raise self.not_available
        return record

    def editable(self, record: T | None) -> T:
        if record is None or not self.may_edit(record):
            raise self.not_available
        return record

    def deletable(self, record: T | None) -> T:
        if record is None or not self.may_delete(record):
            raise self.not_available
        return record
