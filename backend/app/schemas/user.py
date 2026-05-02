"""User schemas for request/response validation."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str | None = Field(None, max_length=100)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str | None = Field(None, max_length=100)
    role: str = Field("user", pattern="^(admin|user)$")
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr
    nickname: str | None = Field(None, max_length=100)
    role: str = Field(..., pattern="^(admin|user)$")
    is_active: bool


class UserPasswordUpdate(BaseModel):
    password: str = Field(..., min_length=6, max_length=100)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    nickname: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
