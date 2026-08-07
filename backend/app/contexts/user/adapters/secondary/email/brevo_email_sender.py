import os

import httpx

from app.contexts.user.domain.ports.email_sender import EmailDeliveryError, EmailSender

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"

# Short. A caller is waiting on this — registering, or pressing "send it again" — and a
# provider that has not answered in ten seconds is not about to.
_TIMEOUT_SECONDS = 10.0


class BrevoEmailSender(EmailSender):
    """Hands a message to Brevo's transactional API.

    Everything provider-shaped lives here and nowhere else: the endpoint, the header name,
    the JSON body. The port above it knows only that mail can be sent, which is what makes
    a move to another provider a change to this one file.

    The API key is read from the environment, like `JWT_SECRET_KEY`, and never travels
    anywhere near the frontend. It is not logged, and neither is the recipient: this class
    raises without either in the message, because the one thing that must not happen is an
    address ending up in a log because a send failed.
    """

    def __init__(
        self,
        api_key: str | None = None,
        sender: str | None = None,
        sender_name: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ["BREVO_API_KEY"]
        self._sender = sender if sender is not None else os.environ["MAIL_FROM"]
        self._sender_name = sender_name if sender_name is not None else os.environ.get("MAIL_FROM_NAME", "")
        self._client = client

    async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        sender: dict[str, str] = {"email": self._sender}
        if self._sender_name:
            sender["name"] = self._sender_name

        payload: dict[str, object] = {
            "sender": sender,
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
        }
        if html is not None:
            payload["htmlContent"] = html

        try:
            response = await self._post(payload)
        except httpx.HTTPError as error:
            # The provider was unreachable, or took too long. Deliberately does not carry
            # the recipient or the original error's body into the message.
            raise EmailDeliveryError(f"Could not reach the email provider: {type(error).__name__}") from None

        if response.status_code >= 400:
            raise EmailDeliveryError(f"The email provider refused the message: {response.status_code}")

    async def _post(self, payload: dict[str, object]) -> httpx.Response:
        headers = {"api-key": self._api_key, "content-type": "application/json"}
        if self._client is not None:
            return await self._client.post(BREVO_ENDPOINT, json=payload, headers=headers)
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            return await client.post(BREVO_ENDPOINT, json=payload, headers=headers)
