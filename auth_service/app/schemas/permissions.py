from pydantic import BaseModel, Field, ConfigDict


class PermissionBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    description: str

class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(BaseModel):
    code: str | None = Field(min_length=1, max_length=64, default=None)
    description: str | None = None

class PermissionDB(PermissionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)