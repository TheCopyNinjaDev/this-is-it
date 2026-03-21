from __future__ import annotations

from typing import Any

import httpx


class BackendClient:
    def __init__(self, *, base_url: str, bearer_token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_user(self, *, user_id: int, name: str) -> dict[str, Any]:
        response = await self._client.post("/user", json={"id": user_id, "name": name})
        response.raise_for_status()
        return response.json()

    async def list_users(self) -> list[dict[str, Any]]:
        response = await self._client.get("/user")
        response.raise_for_status()
        return response.json()

    async def create_room(self, *, creator_user_id: int) -> dict[str, Any]:
        response = await self._client.post("/rooms", json={"creator_user_id": creator_user_id})
        response.raise_for_status()
        return response.json()

    async def get_latest_photo_target(self, *, user_id: int) -> dict[str, Any]:
        response = await self._client.get("/rooms/matched/latest-photo-target", params={"user_id": user_id})
        response.raise_for_status()
        return response.json()

    async def get_memory_download_target(self, *, memory_id: int, user_id: int) -> dict[str, Any]:
        response = await self._client.get(
            f"/rooms/memories/{memory_id}/download-target",
            params={"user_id": user_id},
        )
        response.raise_for_status()
        return response.json()

    async def update_room_memory(
        self,
        *,
        room_id: str,
        uploaded_by_user_id: int,
        photo_key: str,
        postcard_key: str,
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"/rooms/{room_id}/memory",
            json={
                "uploaded_by_user_id": uploaded_by_user_id,
                "photo_key": photo_key,
                "postcard_key": postcard_key,
            },
        )
        response.raise_for_status()
        return response.json()

    async def validate_custom_payment(
        self,
        *,
        room_id: str,
        user_id: int,
        payload: str,
        amount: int,
        currency: str,
    ) -> None:
        response = await self._client.post(
            f"/rooms/{room_id}/custom/payment/validate",
            json={
                "user_id": user_id,
                "payload": payload,
                "amount": amount,
                "currency": currency,
            },
        )
        response.raise_for_status()

    async def confirm_custom_payment(
        self,
        *,
        room_id: str,
        user_id: int,
        payload: str,
        amount: int,
        currency: str,
        telegram_payment_charge_id: str,
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"/rooms/{room_id}/custom/payment/confirm",
            json={
                "user_id": user_id,
                "payload": payload,
                "amount": amount,
                "currency": currency,
                "telegram_payment_charge_id": telegram_payment_charge_id,
            },
        )
        response.raise_for_status()
        return response.json()
