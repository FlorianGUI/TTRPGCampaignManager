from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    # Read straight off the domain entity, so endpoints hand back a `User` and this decides
    # what leaves the building — notably not `hashed_password`.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    # Without this the frontend cannot tell whether to ask someone to confirm their
    # address — /users/me was the only thing it had, and it did not say (#72).
    email_verified: bool


class VerifyEmail(BaseModel):
    """The token, in a body rather than a query string.

    Query strings end up in access logs, in `Referer` headers and in browser history. This
    one is a credential — it verifies an address by itself — so it travels where those do
    not reach.
    """

    token: str


class ForgotPassword(BaseModel):
    """An email address or a username — whichever the person remembers (#71)."""

    identifier: str


class ResetPassword(BaseModel):
    token: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
