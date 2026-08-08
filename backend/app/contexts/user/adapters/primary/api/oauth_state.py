import secrets
from typing import Literal, NamedTuple, TypedDict

from fastapi import Response

from app.common.security.pkce import challenge_for, create_verifier

STATE_COOKIE_NAME = "sso"

# Ten minutes: long enough to read a consent screen and find a password manager, short
# enough that an abandoned sign-in does not leave a usable verifier lying in a browser for
# the rest of the day.
_MAX_AGE_SECONDS = 600

# The two halves are one cookie, joined by a character that cannot occur in either — both
# are `token_urlsafe`, whose alphabet is `A-Za-z0-9_-`. A separator that could appear in a
# value would make the split ambiguous, and the ambiguous case is a state comparison against
# the wrong half of the string.
_SEPARATOR = "."


class _Attributes(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["lax"]
    path: str


# Same arrangement as the refresh cookie: written down once, shared by setting and clearing,
# because attributes are the security control and a cookie cleared with attributes that do
# not match the ones it was set with is not cleared at all.
#
#   httponly  — the verifier is the proof that a code belongs to this sign-in. Script must
#               not be able to read it, or an XSS could complete somebody else's flow.
#   secure    — never over plain HTTP. localhost counts as trustworthy, so development works.
#   samesite  — **Lax, and this is the one cookie here that cannot be Strict.** The callback
#               arrives as a top-level navigation from discord.com, which is cross-site, and
#               a Strict cookie is not *sent* on one. The flow would then fail every time,
#               indistinguishably from an attack. Lax is exactly the exemption this needs:
#               sent on a top-level GET navigation, withheld from everything else. That it
#               rides along on a cross-site navigation is not a hole here — the value is
#               compared against `state` from the query, so possessing the cookie alone
#               proves nothing.
#   path      — /auth, so this never travels with an API call. Nothing outside the sign-in
#               dance has any use for it.
_ATTRIBUTES: _Attributes = {"httponly": True, "secure": True, "samesite": "lax", "path": "/auth"}


class SignInAttempt(NamedTuple):
    """The two secrets a sign-in has to remember while the person is away at the provider."""

    state: str
    verifier: str


def begin() -> SignInAttempt:
    """Mint the pair that ties a callback back to the request that started it.

    They answer different questions and neither replaces the other. `state` proves the
    callback belongs to a sign-in *this browser* started, which is what stops an attacker
    feeding their own authorization code to a victim's session and quietly signing them into
    the attacker's account. `verifier` proves the code is being redeemed by whoever asked
    for it, which is what stops an intercepted code being spent by anyone else.
    """
    return SignInAttempt(state=secrets.token_urlsafe(32), verifier=create_verifier())


def challenge(attempt: SignInAttempt) -> str:
    return challenge_for(attempt.verifier)


def remember(response: Response, attempt: SignInAttempt) -> None:
    """Keep the attempt in the browser rather than in a table.

    A row per started sign-in would need a primary key, a migration, an expiry and something
    to sweep it — for state that is worthless ten minutes later and belongs to exactly one
    browser. The cookie is httpOnly, so the browser holds it without being able to read it,
    which is the same property the table would have bought.
    """
    response.set_cookie(
        STATE_COOKIE_NAME,
        f"{attempt.state}{_SEPARATOR}{attempt.verifier}",
        max_age=_MAX_AGE_SECONDS,
        **_ATTRIBUTES,
    )


def recall(cookie: str | None, presented_state: str | None) -> str | None:
    """The verifier, if the callback really belongs to the sign-in this browser began.

    Returns `None` for every way that can fail — no cookie, a malformed one, a missing or
    mismatched `state` — because the caller does the same thing in all of them and telling
    them apart would describe the check to whoever is probing it.

    `compare_digest` rather than `==` on principle rather than because a timing attack on
    this is plausible: `state` is 256 bits of randomness, so nobody is walking it out a byte
    at a time. It costs nothing, and the habit is what matters in the file where the next
    comparison might be against something guessable.
    """
    if cookie is None or presented_state is None:
        return None
    state, separator, verifier = cookie.partition(_SEPARATOR)
    if not separator:
        return None
    if not secrets.compare_digest(state, presented_state):
        return None
    return verifier


def forget(response: Response) -> None:
    """Drop the cookie, whatever the outcome was.

    Unconditional on purpose: a verifier is single-use, and one left behind after a
    completed sign-in is a live secret with nothing left to protect. Clearing it on the
    failure paths too means an abandoned attempt cannot be resumed later with a code
    somebody kept.
    """
    response.delete_cookie(STATE_COOKIE_NAME, **_ATTRIBUTES)
