from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramBillingService:
    def __init__(self, *, bot_token: str, bot_username: str | None = None, proxy_url: str | None = None) -> None:
        self.bot_token = bot_token
        self.bot_username = bot_username.lstrip("@") if bot_username else None
        self.proxy_url = proxy_url

    async def create_stars_invoice_link(
        self,
        *,
        title: str,
        description: str,
        payload: str,
        amount_stars: int,
    ) -> str:
        async with httpx.AsyncClient(timeout=20.0, proxy=self.proxy_url) as client:
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
            logger.info("Created Telegram invoice link via proxy=%s", bool(self.proxy_url))

        data = response.json()
        if not data.get("ok") or not data.get("result"):
            raise RuntimeError("Telegram createInvoiceLink failed")
        return str(data["result"])
