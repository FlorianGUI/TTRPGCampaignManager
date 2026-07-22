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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
