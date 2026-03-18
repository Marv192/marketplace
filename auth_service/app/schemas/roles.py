from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.permissions import PermissionDB


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: str | None = Field(min_length=1, max_length=64, default=None)
    description: Optional[str] = None

class RoleDB(RoleBase):
    id: int
    permissions: list[PermissionDB] = []
    model_config = ConfigDict(from_attributes=True)

class RolePermissionsUpdate(BaseModel):
    permission_ids: list[int]