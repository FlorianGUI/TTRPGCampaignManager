import re

MAX_LENGTH = 50  # matches users.username
_FALLBACK = "adventurer"
_ALLOWED = re.compile(r"[^a-z0-9._-]+")


def derive(display_name: str) -> str:
    """Turn whatever a provider calls someone into something this app can store.

    A provider's display name is not a username: Google returns "Aragorn Elessar", Discord
    allows emoji and spaces, and neither promises uniqueness or a length. This narrows it to
    the shape `users.username` can hold, and never fails — a name made entirely of
    characters we drop still has to produce an account.

    Not reversible and not meant to be. Two different display names can derive the same
    base, which is exactly why callers must be prepared to take the next free variant
    rather than assuming this answer is available.
    """
    lowered = display_name.strip().lower()
    cleaned = _ALLOWED.sub("-", lowered).strip("-._")
    # Collapse the runs the substitution leaves behind, so "Aragorn   Elessar" is
    # "aragorn-elessar" rather than "aragorn---elessar".
    collapsed = re.sub(r"([._-])\1+", r"\1", cleaned)

    return (collapsed or _FALLBACK)[:MAX_LENGTH]


def variant(base: str, attempt: int) -> str:
    """The nth alternative to a base that is already taken: `aragorn`, `aragorn-2`, …

    The suffix is counted, not random, because a person reads their own username. Truncated
    from the base rather than the suffix when the two together would overflow the column —
    dropping digits would produce a name that collides again, which is the one thing this
    must not do.
    """
    if attempt == 0:
        return base[:MAX_LENGTH]

    suffix = f"-{attempt + 1}"

    return f"{base[: MAX_LENGTH - len(suffix)]}{suffix}"
