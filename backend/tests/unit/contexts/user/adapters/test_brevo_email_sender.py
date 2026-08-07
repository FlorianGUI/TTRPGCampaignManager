import httpx
import pytest

from app.contexts.user.adapters.secondary.email.brevo_email_sender import BREVO_ENDPOINT, BrevoEmailSender
from app.contexts.user.domain.ports.email_sender import EmailDeliveryError


def sender_with(handler: httpx.MockTransport) -> BrevoEmailSender:
    """The adapter pointed at a transport that never leaves the process.

    No test in this suite reaches Brevo. The API key here is a string, not a secret.
    """
    return BrevoEmailSender(
        api_key="test-key",
        sender="noreply@lastdawn.fr",
        sender_name="Campaign Manager",
        client=httpx.AsyncClient(transport=handler),
    )


class TestSend:
    async def test_posts_the_message_in_the_shape_brevo_expects(self):
        seen: dict[str, object] = {}

        def handle(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["api_key"] = request.headers.get("api-key")
            seen["body"] = request.read().decode()
            return httpx.Response(201, json={"messageId": "abc"})

        await sender_with(httpx.MockTransport(handle)).send(
            to="aragorn@gondor.test", subject="Confirm your email address", text="link"
        )

        assert seen["url"] == BREVO_ENDPOINT
        assert seen["api_key"] == "test-key"
        body = str(seen["body"])
        assert '"email": "noreply@lastdawn.fr"' in body or '"email":"noreply@lastdawn.fr"' in body
        assert "aragorn@gondor.test" in body

    async def test_a_refusal_becomes_a_delivery_error(self):
        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "unauthorised"})

        with pytest.raises(EmailDeliveryError) as failed:
            await sender_with(httpx.MockTransport(handle)).send(to="a@b.test", subject="s", text="t")

        assert "401" in str(failed.value)

    async def test_an_unreachable_provider_becomes_a_delivery_error(self):
        def handle(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("too slow")

        with pytest.raises(EmailDeliveryError):
            await sender_with(httpx.MockTransport(handle)).send(to="a@b.test", subject="s", text="t")

    async def test_never_puts_the_recipient_or_the_key_in_the_error(self):
        """A failed send must not be how an address ends up in a log. The message carries
        the shape of the failure and nothing about who it was for."""

        def handle(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"message": "boom"})

        with pytest.raises(EmailDeliveryError) as failed:
            await sender_with(httpx.MockTransport(handle)).send(to="private@address.test", subject="s", text="t")

        assert "private@address.test" not in str(failed.value)
        assert "test-key" not in str(failed.value)

    async def test_sends_html_when_there_is_some(self):
        def handle(request: httpx.Request) -> httpx.Response:
            assert "htmlContent" in request.read().decode()
            return httpx.Response(201, json={})

        await sender_with(httpx.MockTransport(handle)).send(to="a@b.test", subject="s", text="t", html="<p>t</p>")

    async def test_omits_html_when_there_is_none(self):
        def handle(request: httpx.Request) -> httpx.Response:
            assert "htmlContent" not in request.read().decode()
            return httpx.Response(201, json={})

        await sender_with(httpx.MockTransport(handle)).send(to="a@b.test", subject="s", text="t")


class TestItsOwnClient:
    async def test_builds_one_with_a_timeout_when_it_was_not_given_a_client(self, monkeypatch):
        """The path production takes. Every other test here injects a transport, so without
        this the branch that opens a real client — and the timeout on it — is never run.

        A provider that has not answered in ten seconds is not about to, and somebody is
        waiting on this request.
        """
        opened: dict[str, object] = {}

        class RecordingClient:
            def __init__(self, timeout: float) -> None:
                opened["timeout"] = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc: object) -> None:
                return None

            async def post(self, url: str, json: object, headers: dict[str, str]) -> httpx.Response:
                opened["url"] = url
                return httpx.Response(201, json={})

        monkeypatch.setattr(
            "app.contexts.user.adapters.secondary.email.brevo_email_sender.httpx.AsyncClient", RecordingClient
        )

        await BrevoEmailSender(api_key="k", sender="s@t.test", sender_name="n").send(
            to="a@b.test", subject="s", text="t"
        )

        assert opened["url"] == BREVO_ENDPOINT
        assert opened["timeout"] == 10.0
