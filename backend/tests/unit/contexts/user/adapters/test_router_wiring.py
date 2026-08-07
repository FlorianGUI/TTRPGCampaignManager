from app.contexts.user.adapters.primary.api.routers.users import (
    get_password_reset_service,
    get_verification_service,
)
from app.contexts.user.application.email_verification_service import EmailVerificationService
from app.contexts.user.application.password_reset_service import PasswordResetService


class TestGetVerificationService:
    def test_composes_the_real_thing_from_the_environment(self, monkeypatch):
        """The composition root, which nothing else runs.

        The whole suite replaces this dependency so that no test can send mail, which
        leaves the wiring itself unexercised — and wiring that nothing runs is wiring that
        breaks on deploy. This calls it the way FastAPI would, with the environment a
        deployment provides.
        """
        monkeypatch.setenv("BREVO_API_KEY", "not-a-real-key")
        monkeypatch.setenv("MAIL_FROM", "noreply@lastdawn.fr")

        service = get_verification_service(db=None)  # type: ignore[arg-type]

        assert isinstance(service, EmailVerificationService)

    def test_refuses_to_build_without_a_key(self, monkeypatch):
        """A deployment that forgot the key should fail where it is obvious, not send
        anonymously or silently do nothing."""
        monkeypatch.delenv("BREVO_API_KEY", raising=False)
        monkeypatch.setenv("MAIL_FROM", "noreply@lastdawn.fr")

        try:
            get_verification_service(db=None)  # type: ignore[arg-type]
        except KeyError as missing:
            assert "BREVO_API_KEY" in str(missing)
        else:
            raise AssertionError("expected a missing key to be refused")


class TestGetPasswordResetService:
    def test_composes_the_real_thing_from_the_environment(self, monkeypatch):
        """Same reasoning as the verification service above: the suite replaces this so no
        test can send mail, which leaves the wiring itself unrun. Wiring nothing exercises
        is wiring that breaks on deploy."""
        monkeypatch.setenv("BREVO_API_KEY", "not-a-real-key")
        monkeypatch.setenv("MAIL_FROM", "noreply@lastdawn.fr")

        service = get_password_reset_service(db=None)  # type: ignore[arg-type]

        assert isinstance(service, PasswordResetService)
