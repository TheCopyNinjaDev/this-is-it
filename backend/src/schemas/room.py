from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RoomCreateRequest(BaseModel):
    creator_user_id: int | None = None


class RoomJoinRequest(BaseModel):
    user_id: int | None = None


class RoomLeaveRequest(BaseModel):
    user_id: int | None = None


class RoomStartRequest(BaseModel):
    user_id: int | None = None
    flow_type: Literal["catalog", "custom"] = "catalog"


class SwipeRequest(BaseModel):
    idea_id: int
    liked: bool
    user_id: int | None = None


class CustomPreferenceRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=1000)
    user_id: int | None = None


class CustomGenerateRequest(BaseModel):
    user_id: int | None = None


class CustomVoteRequest(BaseModel):
    option_id: str
    liked: bool
    user_id: int | None = None


class CustomPaymentValidateRequest(BaseModel):
    user_id: int
    payload: str
    amount: int
    currency: str


class CustomPaymentConfirmRequest(BaseModel):
    user_id: int
    payload: str
    amount: int
    currency: str
    telegram_payment_charge_id: str


class CustomPaymentLinkResponse(BaseModel):
    invoice_url: str
    price_stars: int


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


class GeneratedIdeaVoteResponse(BaseModel):
    user_id: int
    liked: bool


class CustomPreferenceResponse(BaseModel):
    user_id: int
    name: str
    prompt: str
    submitted_at: datetime


class GeneratedIdeaResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    vibe: str
    reason: str
    votes: list[GeneratedIdeaVoteResponse] = []


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
    matched_generated_idea: GeneratedIdeaResponse | None = None
    flow_type: str | None = None
    custom_status: str | None = None
    custom_price_stars: int | None = None
    custom_payment_required: bool = False
    custom_payment_paid: bool = False
    custom_preferences: list[CustomPreferenceResponse] = []
    generated_ideas: list[GeneratedIdeaResponse] = []


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
