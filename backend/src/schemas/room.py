from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RoomCreateRequest(BaseModel):
    creator_user_id: int | None = None


class RoomJoinRequest(BaseModel):
    user_id: int | None = None


class RoomLeaveRequest(BaseModel):
    user_id: int | None = None


class RoomStartRequest(BaseModel):
    user_id: int | None = None


class SwipeRequest(BaseModel):
    idea_id: int
    liked: bool
    user_id: int | None = None


class ParticipantResponse(BaseModel):
    user_id: int
    name: str
    is_creator: bool


class DateIdeaResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    vibe: str


class RoomMemoryResponse(BaseModel):
    id: int
    uploaded_by_user_id: int
    uploaded_by_name: str
    created_at: datetime
    matched_at: datetime | None = None
    photo_url: str | None = None
    postcard_url: str | None = None


class RoomResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    matched_at: datetime | None = None
    match_revealed_at: datetime | None = None
    photo_uploaded: bool = False
    postcard_url: str | None = None
    memories: list[RoomMemoryResponse] = []
    participants: list[ParticipantResponse]
    participants_count: int
    max_participants: int = 2
    can_start: bool
    invite_url: str
    photo_upload_url: str | None = None
    matched_idea: DateIdeaResponse | None = None


class RoomListResponse(BaseModel):
    active: list[RoomResponse]
    completed: list[RoomResponse]


class RoomMemoryUpdateRequest(BaseModel):
    uploaded_by_user_id: int
    photo_key: str
    postcard_key: str


class RoomPhotoTargetResponse(BaseModel):
    room_id: UUID
    idea_title: str | None = None
    matched_at: datetime | None = None


class RoomRevealRequest(BaseModel):
    user_id: int | None = None


class RoomMemoryDownloadResponse(BaseModel):
    memory_id: int
    room_id: UUID
    uploaded_by_name: str
    created_at: datetime
    postcard_url: str


class SwipeResultResponse(BaseModel):
    room_status: str
    matched: bool
    matched_idea: DateIdeaResponse | None = None
    next_idea: DateIdeaResponse | None = None
