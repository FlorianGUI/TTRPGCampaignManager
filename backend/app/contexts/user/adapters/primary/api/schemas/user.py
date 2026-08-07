from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str


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
