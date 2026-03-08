from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_deleted: bool


class UserCreate(BaseModel):
    id: int
    name: str


class UserUpdate(BaseModel):
    name: str


class UserPatch(BaseModel):
    name: str | None = None
