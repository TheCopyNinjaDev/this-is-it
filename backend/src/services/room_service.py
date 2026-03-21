from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from src.repositories.room_repo import RoomRepository
from src.repositories.user_repo import UserRepository
from src.schemas.room import (
    CustomGenerateRequest,
    CustomPaymentConfirmRequest,
    CustomPaymentLinkResponse,
    CustomPaymentValidateRequest,
    CustomPreferenceRequest,
    CustomPreferenceResponse,
    CustomVoteRequest,
    DateIdeaResponse,
    GeneratedIdeaResponse,
    GeneratedIdeaVoteResponse,
    ParticipantResponse,
    RoomCreateRequest,
    RoomLeaveRequest,
    RoomListResponse,
    RoomMemoryDownloadResponse,
    RoomMemoryResponse,
    RoomMemoryUpdateRequest,
    RoomPhotoTargetResponse,
    RoomRevealRequest,
    RoomJoinRequest,
    RoomResponse,
    RoomStartRequest,
    SwipeRequest,
    SwipeResultResponse,
)
from src.services.openrouter_service import OpenRouterDateGenerator
from src.services.telegram_billing_service import TelegramBillingService
from src.storage import ObjectStorage
from src.ws_manager import room_connection_manager

CUSTOM_DATE_SERVICE_CODE = "custom_date_generation"
CUSTOM_DATE_SERVICE_NAME = "Кастомное свидание"
logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    is_service: bool
    user_id: int | None = None


class RoomService:
    def __init__(
        self,
        room_repository: RoomRepository,
        user_repository: UserRepository,
        storage: ObjectStorage,
        frontend_base_url: str,
        telegram_bot_username: str | None = None,
        telegram_mini_app_short_name: str | None = None,
        openrouter_generator: OpenRouterDateGenerator | None = None,
        telegram_billing: TelegramBillingService | None = None,
    ):
        self.room_repository = room_repository
        self.user_repository = user_repository
        self.storage = storage
        self.frontend_base_url = frontend_base_url.rstrip("/")
        self.telegram_bot_username = telegram_bot_username.lstrip("@") if telegram_bot_username else None
        self.telegram_mini_app_short_name = (
            telegram_mini_app_short_name.strip("/").lower() if telegram_mini_app_short_name else None
        )
        self.openrouter_generator = openrouter_generator
        self.telegram_billing = telegram_billing

    def _invite_url(self, room_id: UUID) -> str:
        if self.telegram_bot_username:
            if self.telegram_mini_app_short_name:
                return (
                    f"https://t.me/{self.telegram_bot_username}/"
                    f"{self.telegram_mini_app_short_name}?startapp={room_id}"
                )
            return f"https://t.me/{self.telegram_bot_username}?startapp={room_id}"
        return f"{self.frontend_base_url}/?room_id={room_id}"

    def _photo_upload_url(self) -> str | None:
        if not self.telegram_bot_username:
            return None
        return f"https://t.me/{self.telegram_bot_username}?start=upload_photo"

    def _resolve_user_id(self, auth: AuthContext, requested_user_id: int | None) -> int:
        if auth.is_service:
            if requested_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_id is required for service requests",
                )
            return requested_user_id

        if auth.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user token",
            )

        if requested_user_id is not None and requested_user_id != auth.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not match requested user",
            )
        return auth.user_id

    async def _require_room(self, room_id: UUID):
        room = await self.room_repository.get_room(room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        return room

    async def _require_participant(self, room_id: UUID, user_id: int) -> None:
        is_participant = await self.room_repository.is_participant(room_id, user_id)
        if not is_participant:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a participant of this room")

    def _idea_response(self, idea: Any | None) -> DateIdeaResponse | None:
        if idea is None:
            return None
        return DateIdeaResponse(
            id=idea.id,
            title=idea.title,
            description=idea.description,
            category=idea.category,
            vibe=idea.vibe,
        )

    @staticmethod
    def _custom_payment_required(room: Any, *, has_free_generation: bool = False) -> bool:
        return bool(room.custom_price_stars and room.custom_price_stars > 0 and not has_free_generation)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @staticmethod
    def _payment_payload(room_id: UUID) -> str:
        return f"custom_date:{room_id}"

    async def _room_has_free_custom_generation(self, room_id: UUID) -> bool:
        participants = await self.room_repository.get_room_participants(room_id)
        return await self.user_repository.has_any_service_grant(
            [user_id for user_id, _ in participants],
            CUSTOM_DATE_SERVICE_CODE,
        )

    def _generated_idea_response(self, option: dict[str, Any], votes: list[dict[str, Any]]) -> GeneratedIdeaResponse:
        return GeneratedIdeaResponse(
            id=str(option["id"]),
            title=str(option["title"]),
            description=str(option["description"]),
            category=str(option["category"]),
            vibe=str(option["vibe"]),
            reason=str(option.get("reason", "")),
            votes=[
                GeneratedIdeaVoteResponse(
                    user_id=int(vote["user_id"]),
                    liked=bool(vote["liked"]),
                )
                for vote in votes
            ],
        )

    async def _room_response(self, room_id: UUID) -> RoomResponse:
        room = await self._require_room(room_id)
        return await self._room_response_from_model(room)

    async def _room_response_from_model(self, room) -> RoomResponse:
        participants = await self.room_repository.get_room_participants(room.id)
        memories = await self.room_repository.get_room_memories(room.id)
        participant_name_by_id = {user_id: name for user_id, name in participants}
        matched_idea = None
        if room.matched_idea_id is not None:
            matched_idea = await self.room_repository.get_idea(room.matched_idea_id)

        memory_responses = [
            RoomMemoryResponse(
                id=memory.id,
                uploaded_by_user_id=memory.uploaded_by_user_id,
                uploaded_by_name=uploaded_by_name,
                created_at=memory.created_at,
                matched_at=memory.matched_at,
                photo_url=self.storage.presigned_get_url(memory.photo_key),
                postcard_url=self.storage.presigned_get_url(memory.postcard_key),
            )
            for memory, uploaded_by_name in memories
        ]

        custom_votes_by_option: dict[str, list[dict[str, Any]]] = {}
        for vote in room.custom_votes or []:
            option_id = str(vote["option_id"])
            custom_votes_by_option.setdefault(option_id, []).append(vote)

        custom_preferences = [
            CustomPreferenceResponse(
                user_id=int(item["user_id"]),
                name=participant_name_by_id.get(int(item["user_id"]), "Участник"),
                prompt=str(item["prompt"]),
                submitted_at=self._parse_datetime(str(item.get("submitted_at"))) or room.updated_at,
            )
            for item in room.custom_preferences or []
        ]
        generated_ideas = [
            self._generated_idea_response(option, custom_votes_by_option.get(str(option["id"]), []))
            for option in room.custom_options or []
        ]
        matched_generated_idea = (
            self._generated_idea_response(
                room.custom_matched_option,
                custom_votes_by_option.get(str(room.custom_matched_option["id"]), []),
            )
            if room.custom_matched_option
            else None
        )
        has_free_generation = await self._room_has_free_custom_generation(room.id) if room.flow_type == "custom" else False

        return RoomResponse(
            id=room.id,
            status=room.status,
            created_at=room.created_at,
            updated_at=room.updated_at,
            matched_at=room.matched_at,
            match_revealed_at=room.match_revealed_at,
            photo_uploaded=bool(memory_responses),
            postcard_url=memory_responses[0].postcard_url if memory_responses else None,
            memories=memory_responses,
            participants=[
                ParticipantResponse(
                    user_id=user_id,
                    name=name,
                    is_creator=user_id == room.creator_user_id,
                )
                for user_id, name in participants
            ],
            participants_count=len(participants),
            can_start=len(participants) == 2 and room.status == "waiting",
            invite_url=self._invite_url(room.id),
            photo_upload_url=self._photo_upload_url(),
            matched_idea=self._idea_response(matched_idea),
            matched_generated_idea=matched_generated_idea,
            flow_type=room.flow_type,
            custom_status=room.custom_status,
            custom_price_stars=room.custom_price_stars,
            custom_payment_required=self._custom_payment_required(room, has_free_generation=has_free_generation),
            custom_payment_paid=room.custom_paid_at is not None or not self._custom_payment_required(room, has_free_generation=has_free_generation),
            custom_preferences=custom_preferences,
            generated_ideas=generated_ideas,
        )

    async def list_rooms(self, auth: AuthContext) -> RoomListResponse:
        user_id = self._resolve_user_id(auth, None)
        rooms = await self.room_repository.get_rooms_for_user(user_id)

        active: list[RoomResponse] = []
        completed: list[RoomResponse] = []
        for room in rooms:
            response = await self._room_response_from_model(room)
            if room.status == "matched":
                completed.append(response)
            else:
                active.append(response)

        return RoomListResponse(active=active, completed=completed)

    async def get_latest_matched_room_for_photo(self, auth: AuthContext, requested_user_id: int | None) -> RoomPhotoTargetResponse:
        user_id = self._resolve_user_id(auth, requested_user_id)
        room = await self.room_repository.get_latest_matched_room_for_photo(user_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matched room for photo not found")

        idea = await self.room_repository.get_idea(room.matched_idea_id) if room.matched_idea_id is not None else None
        return RoomPhotoTargetResponse(
            room_id=room.id,
            idea_title=idea.title if idea is not None else None,
            matched_at=room.matched_at,
        )

    async def get_room_memory_download(
        self,
        memory_id: int,
        auth: AuthContext,
        requested_user_id: int | None,
    ) -> RoomMemoryDownloadResponse:
        user_id = self._resolve_user_id(auth, requested_user_id)
        memory_row = await self.room_repository.get_room_memory(memory_id)
        if memory_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

        memory, uploaded_by_name = memory_row
        await self._require_participant(memory.room_id, user_id)
        postcard_url = self.storage.presigned_get_url(memory.postcard_key)
        if postcard_url is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Postcard file not found")

        return RoomMemoryDownloadResponse(
            memory_id=memory.id,
            room_id=memory.room_id,
            uploaded_by_name=uploaded_by_name,
            created_at=memory.created_at,
            postcard_url=postcard_url,
        )

    async def update_room_memory(self, room_id: UUID, request: RoomMemoryUpdateRequest, auth: AuthContext) -> RoomResponse:
        if not auth.is_service:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only service requests can update room memory")

        room = await self._require_room(room_id)
        if room.status != "matched":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not matched yet")

        is_participant = await self.room_repository.is_participant(room_id, request.uploaded_by_user_id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only room participants can upload date photos",
            )

        await self.room_repository.add_room_memory(
            room_id,
            uploaded_by_user_id=request.uploaded_by_user_id,
            photo_key=request.photo_key,
            postcard_key=request.postcard_key,
            matched_at=room.matched_at,
        )
        return await self._room_response(room_id)

    async def reveal_match(self, room_id: UUID, request: RoomRevealRequest, auth: AuthContext) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)
        await self._require_participant(room_id, user_id)

        if room.status != "matched":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not matched yet")

        await self.room_repository.mark_room_revealed(room_id)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def create_room(self, request: RoomCreateRequest, auth: AuthContext) -> RoomResponse:
        creator_user_id = self._resolve_user_id(auth, request.creator_user_id)
        user = await self.user_repository.get(creator_user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator not found")

        room = await self.room_repository.create_room(creator_user_id=creator_user_id)
        return await self._room_response(room.id)

    async def get_room(self, room_id: UUID, auth: AuthContext) -> RoomResponse:
        if not auth.is_service and auth.user_id is not None:
            await self._require_participant(room_id, auth.user_id)
        return await self._room_response(room_id)

    async def join_room(self, room_id: UUID, request: RoomJoinRequest, auth: AuthContext) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        await self._require_room(room_id)

        user = await self.user_repository.get(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        joined = await self.room_repository.add_participant(room_id, user_id)
        if not joined:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already has two participants")

        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def leave_room(self, room_id: UUID, request: RoomLeaveRequest, auth: AuthContext) -> None:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)

        if room.status == "matched":
            return

        await self.room_repository.remove_participant(room_id, user_id)
        participants_count = await self.room_repository.count_room_participants(room_id)

        if participants_count == 0:
            await self.room_repository.delete_room(room_id)
            room_connection_manager.disconnect_all(room_id)
            return

        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})

    async def start_room(self, room_id: UUID, request: RoomStartRequest, auth: AuthContext) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)
        await self._require_participant(room_id, user_id)

        if not auth.is_service and user_id != room.creator_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the room creator can start the room",
            )

        participants_count = await self.room_repository.count_room_participants(room_id)
        if participants_count < 2:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Need two participants to start")
        if room.status != "waiting":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already started")

        if request.flow_type == "catalog":
            room.flow_type = "catalog"
            room.custom_status = None
            room.custom_price_stars = None
            room.custom_paid_at = None
            room.custom_payment_charge_id = None
            room.custom_preferences = []
            room.custom_options = []
            room.custom_votes = []
            room.custom_matched_option = None
            await self.room_repository.save_room(room)
            await self.room_repository.ensure_default_ideas()
            await self.room_repository.set_room_status(room_id, "active")
        else:
            config = await self.room_repository.ensure_service_config(
                service_code=CUSTOM_DATE_SERVICE_CODE,
                name=CUSTOM_DATE_SERVICE_NAME,
            )
            room.status = "active"
            room.flow_type = "custom"
            room.custom_status = "collecting_preferences"
            room.custom_price_stars = config.price_stars
            room.custom_paid_at = None
            room.custom_payment_charge_id = None
            room.custom_generation_round = 0
            room.custom_preferences = []
            room.custom_options = []
            room.custom_votes = []
            room.custom_matched_option = None
            room.matched_idea_id = None
            room.matched_at = None
            room.match_revealed_at = None
            await self.room_repository.save_room(room)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def next_idea(self, room_id: UUID, auth: AuthContext) -> SwipeResultResponse:
        room = await self._require_room(room_id)
        user_id = self._resolve_user_id(auth, None)
        await self._require_participant(room_id, user_id)

        matched_idea = None
        if room.matched_idea_id is not None:
            matched_idea = await self.room_repository.get_idea(room.matched_idea_id)

        next_idea = None
        if room.status == "active":
            if room.flow_type == "catalog":
                await self.room_repository.ensure_default_ideas()
                next_idea = await self.room_repository.get_next_unswiped_idea(room_id, user_id)

        return SwipeResultResponse(
            room_status=room.status,
            matched=room.status == "matched",
            matched_idea=self._idea_response(matched_idea),
            next_idea=self._idea_response(next_idea),
        )

    async def swipe(self, room_id: UUID, request: SwipeRequest, auth: AuthContext) -> SwipeResultResponse:
        room = await self._require_room(room_id)
        user_id = self._resolve_user_id(auth, request.user_id)
        await self._require_participant(room_id, user_id)

        if room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not active")
        if room.flow_type != "catalog":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room uses custom generation flow")

        idea = await self.room_repository.get_idea(request.idea_id)
        if idea is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea not found")

        await self.room_repository.save_swipe(room_id, user_id, request.idea_id, request.liked)

        matched = False
        matched_idea = None
        if request.liked:
            matched = await self.room_repository.get_match_for_idea(room_id, request.idea_id)
            if matched:
                await self.room_repository.set_room_status(room_id, "matched", matched_idea_id=request.idea_id)
                matched_idea = idea

        next_idea = None
        room = await self._require_room(room_id)
        if room.status == "active":
            next_idea = await self.room_repository.get_next_unswiped_idea(room_id, user_id)

        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return SwipeResultResponse(
            room_status=room.status,
            matched=matched,
            matched_idea=self._idea_response(matched_idea),
            next_idea=self._idea_response(next_idea),
        )

    async def submit_custom_preference(
        self,
        room_id: UUID,
        request: CustomPreferenceRequest,
        auth: AuthContext,
    ) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)
        await self._require_participant(room_id, user_id)
        if room.flow_type != "custom" or room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not in custom generation mode")

        preferences = [item for item in (room.custom_preferences or []) if int(item["user_id"]) != user_id]
        preferences.append(
            {
                "user_id": user_id,
                "prompt": request.prompt.strip(),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        preferences.sort(key=lambda item: int(item["user_id"]))
        room.custom_preferences = preferences
        if room.custom_status == "needs_refinement":
            room.custom_status = "collecting_preferences"
        await self.room_repository.save_room(room)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def create_custom_payment_link(self, room_id: UUID, auth: AuthContext) -> CustomPaymentLinkResponse:
        if self.telegram_billing is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram billing is not configured")

        room = await self._require_room(room_id)
        user_id = self._resolve_user_id(auth, None)
        await self._require_participant(room_id, user_id)
        if not auth.is_service and user_id != room.creator_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the room creator can pay for this service",
            )
        has_free_generation = await self._room_has_free_custom_generation(room_id)
        if room.flow_type != "custom" or room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not in custom generation mode")
        if len(room.custom_preferences or []) < 2:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Both participants must submit their prompts first")
        if not self._custom_payment_required(room, has_free_generation=has_free_generation):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom generation is free for this room")
        if room.custom_paid_at is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom generation is already paid")

        invoice_url = await self.telegram_billing.create_stars_invoice_link(
            title="Своё свидание",
            description="10 персональных идей свидания, собранных под вас обоих",
            payload=self._payment_payload(room.id),
            amount_stars=int(room.custom_price_stars or 0),
        )
        logger.info(
            "Created custom payment invoice",
            extra={
                "room_id": str(room.id),
                "creator_user_id": room.creator_user_id,
                "requested_by_user_id": user_id,
                "price_stars": int(room.custom_price_stars or 0),
            },
        )
        return CustomPaymentLinkResponse(
            invoice_url=invoice_url,
            price_stars=int(room.custom_price_stars or 0),
        )

    async def validate_custom_payment(
        self,
        room_id: UUID,
        request: CustomPaymentValidateRequest,
        auth: AuthContext,
    ) -> None:
        if not auth.is_service:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only service requests can validate payments")

        room = await self._require_room(room_id)
        has_free_generation = await self._room_has_free_custom_generation(room_id)
        if request.user_id != room.creator_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the room creator can pay for this service",
            )
        if request.payload != self._payment_payload(room.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment payload")
        if request.currency != "XTR":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported currency")
        if not self._custom_payment_required(room, has_free_generation=has_free_generation):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room does not require payment")
        if request.amount != int(room.custom_price_stars or 0):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment amount")
        await self._require_participant(room_id, request.user_id)

    async def confirm_custom_payment(
        self,
        room_id: UUID,
        request: CustomPaymentConfirmRequest,
        auth: AuthContext,
    ) -> RoomResponse:
        await self.validate_custom_payment(
            room_id,
            CustomPaymentValidateRequest(
                user_id=request.user_id,
                payload=request.payload,
                amount=request.amount,
                currency=request.currency,
            ),
            auth,
        )
        room = await self._require_room(room_id)
        if room.custom_paid_at is None:
            room.custom_paid_at = datetime.now(timezone.utc)
            room.custom_payment_charge_id = request.telegram_payment_charge_id
            await self.room_repository.save_room(room)
            logger.info(
                "Confirmed custom payment",
                extra={
                    "room_id": str(room.id),
                    "creator_user_id": room.creator_user_id,
                    "paid_by_user_id": request.user_id,
                    "amount": request.amount,
                    "currency": request.currency,
                },
            )
            await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def generate_custom_options(
        self,
        room_id: UUID,
        request: CustomGenerateRequest,
        auth: AuthContext,
    ) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)
        await self._require_participant(room_id, user_id)
        if not auth.is_service and user_id != room.creator_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the room creator can generate options",
            )
        if room.flow_type != "custom" or room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not in custom generation mode")
        if self.openrouter_generator is None or not self.openrouter_generator.enabled:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenRouter is not configured")
        if len(room.custom_preferences or []) < 2:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Both participants must submit their prompts first")
        has_free_generation = await self._room_has_free_custom_generation(room_id)
        if self._custom_payment_required(room, has_free_generation=has_free_generation) and room.custom_paid_at is None:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Custom generation requires payment")

        participants = await self.room_repository.get_room_participants(room_id)
        participant_name_by_id = {participant_id: name for participant_id, name in participants}
        prompts = [
            {
                "name": participant_name_by_id.get(int(item["user_id"]), f"Participant {item['user_id']}"),
                "text": str(item["prompt"]),
            }
            for item in room.custom_preferences
        ]

        room.custom_status = "generating"
        await self.room_repository.save_room(room)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})

        try:
            generated = await self.openrouter_generator.generate_options(prompts)
        except Exception as error:
            room = await self._require_room(room_id)
            room.custom_status = "collecting_preferences"
            await self.room_repository.save_room(room)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to generate custom date ideas: {error}",
            ) from error

        room = await self._require_room(room_id)
        room.custom_generation_round += 1
        room.custom_status = "ready"
        room.custom_options = [
            {
                "id": f"r{room.custom_generation_round}-o{index + 1}",
                **option,
            }
            for index, option in enumerate(generated)
        ]
        room.custom_votes = []
        room.custom_matched_option = None
        room.matched_at = None
        room.match_revealed_at = None
        await self.room_repository.save_room(room)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)

    async def vote_custom_option(
        self,
        room_id: UUID,
        request: CustomVoteRequest,
        auth: AuthContext,
    ) -> RoomResponse:
        user_id = self._resolve_user_id(auth, request.user_id)
        room = await self._require_room(room_id)
        await self._require_participant(room_id, user_id)
        if room.flow_type != "custom" or room.status != "active" or room.custom_status != "ready":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom options are not ready for voting")

        option = next((item for item in (room.custom_options or []) if str(item["id"]) == request.option_id), None)
        if option is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated option not found")

        votes = [
            vote
            for vote in (room.custom_votes or [])
            if not (int(vote["user_id"]) == user_id and str(vote["option_id"]) == request.option_id)
        ]
        votes.append(
            {
                "user_id": user_id,
                "option_id": request.option_id,
                "liked": request.liked,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        room.custom_votes = votes

        option_votes = [vote for vote in votes if str(vote["option_id"]) == request.option_id and bool(vote["liked"])]
        liked_by = {int(vote["user_id"]) for vote in option_votes}
        if len(liked_by) >= 2:
            room.status = "matched"
            room.custom_status = "matched"
            room.custom_matched_option = option
            room.matched_idea_id = None
            room.matched_at = datetime.now(timezone.utc)
        else:
            participants_count = await self.room_repository.count_room_participants(room_id)
            all_reviewed = all(
                len({int(vote["user_id"]) for vote in votes if str(vote["option_id"]) == str(option_item["id"])}) >= participants_count
                for option_item in room.custom_options
            )
            if all_reviewed:
                room.custom_status = "needs_refinement"

        await self.room_repository.save_room(room)
        await room_connection_manager.broadcast(room_id, {"type": "room_updated"})
        return await self._room_response(room_id)
