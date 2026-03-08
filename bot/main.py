from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import BufferedInputFile, InlineKeyboardButton, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
import httpx

from config import get_settings
from storage import BotObjectStorage, build_memory_keys, create_postcard


settings = get_settings()
bot = Bot(token=settings.bot_token)
dp = Dispatcher()
from api import BackendClient

backend = BackendClient(base_url=settings.backend_base_url, bearer_token=settings.backend_bearer_token)
storage = BotObjectStorage(
    access_key=settings.s3_key,
    secret_key=settings.s3_secret_key,
    bucket_name=settings.s3_bucket_name,
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
)


def start_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=settings.frontend_base_url.rstrip("/"))))
    return builder


def room_keyboard(url: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Открыть комнату", web_app=WebAppInfo(url=url)))
    return builder


def room_webapp_url(room_id: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/?room_id={room_id}"


def invite_link(room_id: str) -> str | None:
    if not settings.telegram_bot_username:
        return None
    bot_username = settings.telegram_bot_username.lstrip("@")
    if settings.telegram_mini_app_short_name:
        short_name = settings.telegram_mini_app_short_name.strip("/").lower()
        return f"https://t.me/{bot_username}/{short_name}?startapp={room_id}"
    return f"https://t.me/{bot_username}?startapp={room_id}"


@dp.message(CommandStart())
async def handle_start(message: Message, command: CommandObject) -> None:
    if message.from_user is None:
        return

    await backend.create_user(
        user_id=message.from_user.id,
        name=message.from_user.full_name,
    )
    room_id = command.args.strip() if command.args else None
    if room_id == "upload_photo":
        await message.answer("Отправь сюда фото свидания, и я соберу открытку автоматически.")
        return
    if room_id and room_id.startswith("download_memory_"):
        memory_id_text = room_id.removeprefix("download_memory_")
        if not memory_id_text.isdigit():
            await message.answer("Не удалось распознать открытку.")
            return

        try:
            target = await backend.get_memory_download_target(memory_id=int(memory_id_text), user_id=message.from_user.id)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                await message.answer("Эта открытка не найдена.")
                return
            if error.response.status_code == 403:
                await message.answer("Эта открытка недоступна для этой комнаты.")
                return
            raise

        created_at = datetime.fromisoformat(target["created_at"].replace("Z", "+00:00")).strftime("%d.%m.%Y")
        await message.answer_document(
            target["postcard_url"],
            caption=f"Открытка от {target['uploaded_by_name']} • {created_at}",
        )
        return

    if room_id:
        await message.answer(
            "Тебя пригласили в комнату для выбора свидания. Открой Mini App ниже, чтобы присоединиться.",
            reply_markup=room_keyboard(room_webapp_url(room_id)).as_markup(),
        )
        return

    await message.answer(
        "Готово. Создай комнату и пригласи второго человека через Telegram.",
        reply_markup=start_keyboard().as_markup(),
    )


@dp.message(lambda message: bool(message.photo))
async def handle_photo(message: Message) -> None:
    if message.from_user is None or not message.photo:
        return

    if not storage.enabled:
        await message.answer("S3 не настроен. Добавь S3_KEY, S3_SECRET_KEY и S3_BUCKET_NAME.")
        return

    try:
        target = await backend.get_latest_photo_target(user_id=message.from_user.id)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            await message.answer("Не нашёл завершённый мэтч без открытки. Сначала открой мэтч в приложении.")
            return
        raise

    largest_photo = message.photo[-1]
    telegram_file = await bot.get_file(largest_photo.file_id)
    buffer = io.BytesIO()
    await bot.download_file(telegram_file.file_path, destination=buffer)
    photo_bytes = buffer.getvalue()

    photo_key, postcard_key = build_memory_keys(target["room_id"], message.from_user.id)
    postcard_bytes = create_postcard(
        photo_bytes,
        footer_date=datetime.now().strftime("%d.%m.%Y"),
    )

    storage.upload_bytes(photo_key, photo_bytes, "image/jpeg")
    storage.upload_bytes(postcard_key, postcard_bytes, "image/jpeg")
    room = await backend.update_room_memory(
        room_id=target["room_id"],
        uploaded_by_user_id=message.from_user.id,
        photo_key=photo_key,
        postcard_key=postcard_key,
    )

    memories_count = len(room.get("memories", []))
    await message.answer(
        f"Готово. Открытка для идеи «{target.get('idea_title') or 'свидание'}» создана. "
        f"Теперь в этой комнате {memories_count} фото-воспоминаний."
    )
    await message.answer_document(
        BufferedInputFile(postcard_bytes, filename=f"postcard-{target['room_id']}.jpg"),
        caption="Вот ваша открытка. Её также можно скачать внутри Mini App.",
    )
async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        await dp.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
