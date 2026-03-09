import uuid
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

class UserRegister(UserCredentials):
    name: str

class UserInfo(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role_id: int
    model_config = ConfigDict(from_attributes=True)

class UserFullInfo(UserInfo):
    created_at: datetime


class RefreshToken(BaseModel):
    refresh_token: str


