import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

class UserRegister(UserLogin):
    name: str = Field(min_length=1, max_length=64)

class UserCreate(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str = Field(min_length=1, max_length=64)
    password_hash: str
    role_id: int

class UserInfo(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserDB(UserInfo):
    password_hash: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    name: Optional[str] = None