from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, PreCheckoutQuery, WebAppInfo
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


class BroadcastState(StatesGroup):
    waiting_for_message = State()


broadcast_drafts: dict[int, dict[str, int | str]] = {}
broadcast_media_group_buffers: dict[str, dict[str, Any]] = {}
broadcast_media_group_tasks: dict[str, asyncio.Task[None]] = {}


def start_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=settings.frontend_base_url.rstrip("/"))))
    return builder


def room_keyboard(url: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Открыть комнату", web_app=WebAppInfo(url=url)))
    return builder


def broadcast_confirmation_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Сделать рассылку", callback_data=f"broadcast:send:{draft_id}"),
        InlineKeyboardButton(text="Отменить", callback_data=f"broadcast:cancel:{draft_id}"),
    )
    return builder.as_markup()


async def send_broadcast_preview(
    *,
    owner_chat_id: int,
    owner_user_id: int,
    source_chat_id: int,
    message_ids: list[int],
) -> None:
    draft_id = min(message_ids)
    broadcast_drafts[draft_id] = {
        "chat_id": source_chat_id,
        "message_ids": message_ids,
        "owner_user_id": owner_user_id,
    }

    if len(message_ids) == 1:
        await bot.copy_message(
            chat_id=owner_chat_id,
            from_chat_id=source_chat_id,
            message_id=message_ids[0],
        )
    else:
        await bot.copy_messages(
            chat_id=owner_chat_id,
            from_chat_id=source_chat_id,
            message_ids=message_ids,
        )

    await bot.send_message(
        chat_id=owner_chat_id,
        text="Это предпросмотр рассылки. Отправить всем пользователям или отменить?",
        reply_markup=broadcast_confirmation_keyboard(draft_id),
    )


async def finalize_broadcast_media_group(group_key: str, state: FSMContext) -> None:
    try:
        await asyncio.sleep(1.0)
        buffer = broadcast_media_group_buffers.get(group_key)
        if buffer is None:
            return

        await send_broadcast_preview(
            owner_chat_id=int(buffer["chat_id"]),
            owner_user_id=int(buffer["owner_user_id"]),
            source_chat_id=int(buffer["chat_id"]),
            message_ids=sorted(int(message_id) for message_id in buffer["message_ids"]),
        )
        await state.clear()
    finally:
        broadcast_media_group_buffers.pop(group_key, None)
        broadcast_media_group_tasks.pop(group_key, None)


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


def parse_custom_payment_payload(payload: str) -> UUID | None:
    prefix = "custom_date:"
    if not payload.startswith(prefix):
        return None
    room_id_text = payload.removeprefix(prefix)
    try:
        return UUID(room_id_text)
    except ValueError:
        return None


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


@dp.message(lambda message: bool(settings.broadcast_codeword) and (message.text or "").strip() == settings.broadcast_codeword)
async def begin_broadcast(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    await state.set_state(BroadcastState.waiting_for_message)
    await message.answer(
        "Отправь сообщение для рассылки. Можно текст, фото, видео, документ или анимацию. "
        "После этого я покажу предпросмотр и спрошу, запускать рассылку или нет."
    )


@dp.message(BroadcastState.waiting_for_message)
async def capture_broadcast_message(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    if message.media_group_id:
        group_key = f"{message.chat.id}:{message.from_user.id}:{message.media_group_id}"
        buffer = broadcast_media_group_buffers.setdefault(
            group_key,
            {
                "chat_id": message.chat.id,
                "owner_user_id": message.from_user.id,
                "message_ids": [],
            },
        )
        if message.message_id not in buffer["message_ids"]:
            buffer["message_ids"].append(message.message_id)

        existing_task = broadcast_media_group_tasks.get(group_key)
        if existing_task is not None:
            existing_task.cancel()

        broadcast_media_group_tasks[group_key] = asyncio.create_task(
            finalize_broadcast_media_group(group_key, state)
        )
        return

    await send_broadcast_preview(
        owner_chat_id=message.chat.id,
        owner_user_id=message.from_user.id,
        source_chat_id=message.chat.id,
        message_ids=[message.message_id],
    )
    await state.clear()


@dp.callback_query(lambda callback: callback.data is not None and callback.data.startswith("broadcast:"))
async def handle_broadcast_callback(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.data is None:
        return

    _, action, draft_id_text = callback.data.split(":", 2)
    if not draft_id_text.isdigit():
        await callback.answer("Не удалось обработать черновик", show_alert=True)
        return

    draft_id = int(draft_id_text)
    draft = broadcast_drafts.get(draft_id)
    if draft is None:
        await callback.answer("Черновик уже недоступен", show_alert=True)
        return
    if int(draft["owner_user_id"]) != callback.from_user.id:
        await callback.answer("Этот черновик принадлежит другому пользователю", show_alert=True)
        return

    if action == "cancel":
        broadcast_drafts.pop(draft_id, None)
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Рассылка отменена.")
        await callback.answer()
        return

    if action != "send":
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    users = await backend.list_users()
    sent = 0
    failed = 0
    message_ids = [int(message_id) for message_id in draft["message_ids"]]
    for user in users:
        user_id = int(user["id"])
        try:
            if len(message_ids) == 1:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=int(draft["chat_id"]),
                    message_id=message_ids[0],
                )
            else:
                await bot.copy_messages(
                    chat_id=user_id,
                    from_chat_id=int(draft["chat_id"]),
                    message_ids=message_ids,
                )
            sent += 1
        except Exception:
            failed += 1

    broadcast_drafts.pop(draft_id, None)
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"Рассылка завершена. Отправлено: {sent}. Не доставлено: {failed}."
        )
    await callback.answer("Рассылка запущена")


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


@dp.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery) -> None:
    room_id = parse_custom_payment_payload(query.invoice_payload)
    if room_id is None:
        await bot.answer_pre_checkout_query(query.id, ok=False, error_message="Не удалось распознать платёж.")
        return

    try:
        await backend.validate_custom_payment(
            room_id=str(room_id),
            user_id=query.from_user.id,
            payload=query.invoice_payload,
            amount=query.total_amount,
            currency=query.currency,
        )
    except Exception:
        await bot.answer_pre_checkout_query(
            query.id,
            ok=False,
            error_message="Проверка платежа не прошла. Попробуйте ещё раз чуть позже.",
        )
        return

    await bot.answer_pre_checkout_query(query.id, ok=True)


@dp.message(lambda message: bool(message.successful_payment))
async def handle_successful_payment(message: Message) -> None:
    if message.from_user is None or message.successful_payment is None:
        return

    payment = message.successful_payment
    room_id = parse_custom_payment_payload(payment.invoice_payload)
    if room_id is None:
        await message.answer("Платёж получен, но связать его с комнатой не удалось.")
        return

    await backend.confirm_custom_payment(
        room_id=str(room_id),
        user_id=message.from_user.id,
        payload=payment.invoice_payload,
        amount=payment.total_amount,
        currency=payment.currency,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
    )
    await message.answer("Оплата прошла. Возвращайся в Mini App, теперь можно генерировать своё свидание.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        await dp.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
