from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.contexts.user.domain.identity import Provider


class IdentityProviderError(Exception):
    """The provider could not be reached, refused us, or answered with something unusable.

    One exception for the whole outbound leg on purpose. A caller cannot act differently on
    "Discord timed out" than on "Discord rejected the code" — both mean the sign-in did not
    happen and the way back is to start again — and the difference is exactly the sort of
    thing that gets logged with the code or the secret still attached to it.

    Whatever raises this must keep the client secret, the authorization code and the
    provider's access token out of the message. Nothing in that outbound exchange is safe to
    put in a log line.
    """


@dataclass(frozen=True)
class ProviderProfile:
    """What a provider is willing to say about the person who just signed in.

    Deliberately the smallest set that the sign-in itself needs, rather than everything the
    provider returns. Avatars and usernames are tempting and are a stale copy the moment
    they are written down; `Identity` stores none of it, and this carries `display_name`
    only so a *new* account can derive a username once, at creation.

    `email_verified` is the provider's own claim and is read rather than assumed. It is the
    difference between "Discord knows this address reaches them" and "somebody typed this
    address into Discord", and linking a provider identity to an existing local account is
    only safe on the first of those.
    """

    subject: str
    email: str | None
    email_verified: bool
    display_name: str


class IdentityProvider(ABC):
    """One external place a person can prove who they are.

    The interface is deliberately two calls, because that is all the authorization-code
    flow is from this side: send them somewhere, and turn what comes back into an identity.
    Everything provider-shaped — which URLs, which scopes, whether identity arrives in a
    signed `id_token` or behind a second request, what the claims are called — lives below
    this line, so a second provider is one adapter rather than a second copy of the flow.

    What it does *not* abstract is as important. There is no "find or create the user" here
    and no session issuance: a provider says who somebody is at that provider, and nothing
    else. Deciding which local account that reaches is the application's, and it is the part
    that must not vary per provider.
    """

    @property
    @abstractmethod
    def provider(self) -> Provider:
        """Which half of the `(provider, subject)` key this adapter speaks for."""

    @abstractmethod
    def authorization_url(self, state: str, code_challenge: str) -> str:
        """Where to send the browser to start a sign-in.

        Takes both anti-forgery values rather than minting them, so that the one place they
        are generated is also the place that remembers them. An adapter that produced its
        own `state` would have nowhere to keep it, and PKCE would be decoration: the whole
        point of the challenge is that the verifier stays with whoever will need it back.
        """

    @abstractmethod
    async def profile(self, code: str, code_verifier: str) -> ProviderProfile:
        """Spend the authorization code and come back with an identity.

        Raises `IdentityProviderError` for every way this can fail. The code is single-use
        and short-lived, so there is no retry to offer — a failure here ends the attempt.
        """
