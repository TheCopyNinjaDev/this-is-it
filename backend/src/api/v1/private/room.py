from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from src.auth import decode_access_token
from src.api.deps import AuthContext, get_auth_context, get_room_service
from src.schemas.room import (
    RoomCreateRequest,
    RoomLeaveRequest,
    RoomJoinRequest,
    RoomListResponse,
    RoomMemoryDownloadResponse,
    RoomMemoryUpdateRequest,
    RoomPhotoTargetResponse,
    RoomRevealRequest,
    RoomResponse,
    RoomStartRequest,
    SwipeRequest,
    SwipeResultResponse,
)
from src.services.room_service import RoomService
from src.ws_manager import room_connection_manager

router = APIRouter(
    tags=["Room"],
    prefix="/rooms",
)


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreateRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.create_room(request, auth)


@router.get("/mine", response_model=RoomListResponse)
async def list_my_rooms(
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomListResponse:
    return await service.list_rooms(auth)


@router.get("/matched/latest-photo-target", response_model=RoomPhotoTargetResponse)
async def get_latest_photo_target(
    user_id: int | None = Query(default=None),
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomPhotoTargetResponse:
    return await service.get_latest_matched_room_for_photo(auth, user_id)


@router.get("/memories/{memory_id}/download-target", response_model=RoomMemoryDownloadResponse)
async def get_memory_download_target(
    memory_id: int,
    user_id: int | None = Query(default=None),
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomMemoryDownloadResponse:
    return await service.get_room_memory_download(memory_id, auth, user_id)


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: UUID,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.get_room(room_id, auth)


@router.post("/{room_id}/join", response_model=RoomResponse)
async def join_room(
    room_id: UUID,
    request: RoomJoinRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.join_room(room_id, request, auth)


@router.post("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room(
    room_id: UUID,
    request: RoomLeaveRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> None:
    await service.leave_room(room_id, request, auth)


@router.post("/{room_id}/memory", response_model=RoomResponse)
async def update_room_memory(
    room_id: UUID,
    request: RoomMemoryUpdateRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.update_room_memory(room_id, request, auth)


@router.post("/{room_id}/reveal", response_model=RoomResponse)
async def reveal_room_match(
    room_id: UUID,
    request: RoomRevealRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.reveal_match(room_id, request, auth)


@router.post("/{room_id}/start", response_model=RoomResponse)
async def start_room(
    room_id: UUID,
    request: RoomStartRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RoomResponse:
    return await service.start_room(room_id, request, auth)


@router.get("/{room_id}/ideas/next", response_model=SwipeResultResponse)
async def get_next_idea(
    room_id: UUID,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> SwipeResultResponse:
    return await service.next_idea(room_id, auth)


@router.post("/{room_id}/swipes", response_model=SwipeResultResponse)
async def swipe_idea(
    room_id: UUID,
    request: SwipeRequest,
    service: RoomService = Depends(get_room_service),
    auth: AuthContext = Depends(get_auth_context),
) -> SwipeResultResponse:
    return await service.swipe(room_id, request, auth)


@router.websocket("/ws/{room_id}")
async def room_updates_websocket(
    websocket: WebSocket,
    room_id: UUID,
    service: RoomService = Depends(get_room_service),
    token: str = Query(...),
) -> None:
    try:
        payload = decode_access_token(token)
        auth = AuthContext(is_service=False, user_id=int(payload["sub"]))
        await service.get_room(room_id, auth)
    except Exception:
        await websocket.close(code=4401)
        return

    await room_connection_manager.connect(room_id, websocket)
    await room_connection_manager.send_json(websocket, {"type": "room_updated"})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        room_connection_manager.disconnect(room_id, websocket)
