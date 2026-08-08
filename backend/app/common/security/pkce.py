import base64
import hashlib
import secrets

# RFC 7636 allows 43–128 characters. `token_urlsafe(64)` produces 86, comfortably inside the
# range and already in the unreserved alphabet the spec requires, so nothing has to be
# trimmed or re-encoded on the way into a URL.
_VERIFIER_BYTES = 64


def create_verifier() -> str:
    """The secret half of a PKCE pair: 512 bits from the OS CSPRNG.

    Never leaves this server. It is minted when a sign-in starts, kept where only this
    server can read it, and handed to the provider's token endpoint at the end as proof
    that the code being redeemed belongs to the sign-in that started here.
    """
    return secrets.token_urlsafe(_VERIFIER_BYTES)


def challenge_for(verifier: str) -> str:
    """The public half: S256, which is the only method worth offering.

    The alternative the spec permits is `plain`, where the challenge *is* the verifier —
    which secures nothing, since anyone who intercepts the authorization request then holds
    everything needed to redeem the code. Hashing means the value that travels through the
    browser and sits in the provider's logs cannot be turned back into the verifier.

    Base64url without padding, because the spec says so and because `=` in a query string is
    a needless escaping question.
    """
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")
