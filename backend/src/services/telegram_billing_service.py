from __future__ import annotations

import httpx


class TelegramBillingService:
    def __init__(self, *, bot_token: str, bot_username: str | None = None) -> None:
        self.bot_token = bot_token
        self.bot_username = bot_username.lstrip("@") if bot_username else None

    async def create_stars_invoice_link(
        self,
        *,
        title: str,
        description: str,
        payload: str,
        amount_stars: int,
    ) -> str:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/createInvoiceLink",
                json={
                    "title": title,
                    "description": description,
                    "payload": payload,
                    "currency": "XTR",
                    "prices": [{"label": title, "amount": amount_stars}],
                },
            )
            response.raise_for_status()

        data = response.json()
        if not data.get("ok") or not data.get("result"):
            raise RuntimeError("Telegram createInvoiceLink failed")
        return str(data["result"])
