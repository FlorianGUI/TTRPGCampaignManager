from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from app.common.errors import NotAvailable


@dataclass(frozen=True)
class Unsafe[T]:
    """A record straight out of a repository, or nothing. Nobody has checked it yet.

    The marking is on the dangerous side on purpose. A repository cannot hand back a bare
    record, so the only way to obtain one is to pass this through an `Access` method —
    which makes forgetting the check a type error at the point of use rather than
    something review has to notice.

    Marking the *safe* side instead does not work, and it is worth saying why, because it
    is the more obvious design. If repositories returned `T | None` and `Access` returned
    some `Safe[T]`, the raw type would stay freely available and wrapping it would be
    opt-in — a service could declare `-> T` and return the repository's answer directly,
    and nothing would complain. The guarantee comes from the default being restrictive,
    which is the same reason taint analysis marks the tainted value at the source rather
    than blessing it at the sink.

    `unchecked` is the way out, and it is named to read badly. Repository integration
    tests use it, since asserting on what the repository returned is exactly their job.
    Anywhere else it should look wrong, which is the whole of its design.
    """

    unchecked: T | None


class Access[T](ABC):
    """What one viewer may do with one record, and what happens when the answer is no.

    This class holds no rules. All three questions are abstract on purpose: whether
    editing follows from reading is a decision each context has to make for itself, and
    a default here would be that decision made once, in a place no domain can see, for
    domains that have not been written yet. They agree today; #31 is expected to part
    them, and it should part them by changing a domain rather than by discovering an
    inherited answer.

    What is left here is only mechanism, and it is the same everywhere:

    - take an `Unsafe[T]`, which is the only thing a repository can return, so nothing can
      reach a record without coming through here. It may hold nothing, and absorbing that
      is the point — a record that is absent and a record that is forbidden leave by the
      same door, so the caller cannot tell which it was, which is the whole of the 404
      decision in #12;
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

    def readable(self, found: Unsafe[T]) -> T:
        record = found.unchecked
        if record is None or not self.may_read(record):
            raise self.not_available
        return record

    def editable(self, found: Unsafe[T]) -> T:
        record = found.unchecked
        if record is None or not self.may_edit(record):
            raise self.not_available
        return record

    def deletable(self, found: Unsafe[T]) -> T:
        record = found.unchecked
        if record is None or not self.may_delete(record):
            raise self.not_available
        return record
