import uuid
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool
    companies: list[dict]

    model_config = ConfigDict(from_attributes=True)


class RegisterUserOnlyRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


class UserOnlyResponse(BaseModel):
    id: uuid.UUID
    email: str
    message: str

    model_config = ConfigDict(from_attributes=True)