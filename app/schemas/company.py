import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.company import RoleEnum


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)


class MemberInviteRequest(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.member

    model_config = ConfigDict(str_strip_whitespace=True)


class MemberRoleUpdateRequest(BaseModel):
    role: RoleEnum


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    company_id: uuid.UUID
    email: str
    role: RoleEnum

    model_config = ConfigDict(from_attributes=True)