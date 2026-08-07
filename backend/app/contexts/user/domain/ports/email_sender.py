from abc import ABC, abstractmethod


class EmailDeliveryError(Exception):
    """The message could not be handed to the provider.

    Deliberately says nothing about whether it will arrive — nobody can know that at the
    moment of sending. This is "the provider did not accept it", which is the only failure
    the application can see and the only one it can react to.
    """


class EmailSender(ABC):
    """Somewhere to hand a message. Domain-owned, so nothing above it knows about HTTP.

    One method, and no template or provider concepts in the signature. Which provider is
    behind this is an adapter's business, and keeping it out of here is what makes moving
    from Brevo to anything else — or to a self-hosted relay — a change in one file.
    """

    @abstractmethod
    async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        """Deliver one message, or raise `EmailDeliveryError`."""
