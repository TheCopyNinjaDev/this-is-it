from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from src.repositories.room_repo import RoomRepository
from src.repositories.user_repo import UserRepository
from src.schemas.room import (
    DateIdeaResponse,
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
from src.storage import ObjectStorage
from src.ws_manager import room_connection_manager


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
    ):
        self.room_repository = room_repository
        self.user_repository = user_repository
        self.storage = storage
        self.frontend_base_url = frontend_base_url.rstrip("/")
        self.telegram_bot_username = telegram_bot_username.lstrip("@") if telegram_bot_username else None
        self.telegram_mini_app_short_name = (
            telegram_mini_app_short_name.strip("/").lower() if telegram_mini_app_short_name else None
        )

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

    async def _room_response(self, room_id: UUID) -> RoomResponse:
        room = await self._require_room(room_id)
        return await self._room_response_from_model(room)

    async def _room_response_from_model(self, room) -> RoomResponse:
        participants = await self.room_repository.get_room_participants(room.id)
        memories = await self.room_repository.get_room_memories(room.id)
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

        await self.room_repository.ensure_default_ideas()
        await self.room_repository.set_room_status(room_id, "active")
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
