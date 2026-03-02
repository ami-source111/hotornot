"""Handlers for /upload command — photo upload flow."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, PhotoSize

from src.core.database import async_session_factory
from src.core.models import Gender
from src.core.services.photo import upload_photo
from src.core.services.user import get_or_create_user
from src.bot.keyboards import upload_comments_keyboard

router = Router(name="upload")


class UploadStates(StatesGroup):
    waiting_photo = State()
    waiting_comments_choice = State()


@router.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user)

    if user.gender == Gender.unknown:
        await message.answer(
            "⚠️ Сначала укажи свой пол через /start"
        )
        return

    await state.set_state(UploadStates.waiting_photo)
    await message.answer("📸 Отправь фото, которое хочешь добавить в ленту.")


@router.message(UploadStates.waiting_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    # Take highest resolution
    best: PhotoSize = message.photo[-1]
    await state.update_data(file_id=best.file_id)
    await state.set_state(UploadStates.waiting_comments_choice)
    await message.answer(
        "💬 Разрешить другим пользователям оставлять комментарии к этому фото?",
        reply_markup=upload_comments_keyboard(),
    )


@router.message(UploadStates.waiting_photo)
async def handle_not_photo(message: Message) -> None:
    await message.answer("❌ Пожалуйста, отправь именно фото (не файл).")


@router.callback_query(
    UploadStates.waiting_comments_choice,
    lambda c: c.data and c.data.startswith("upload:comments:"),
)
async def cb_comments_choice(callback: CallbackQuery, state: FSMContext) -> None:
    allow = callback.data.endswith(":yes")
    data = await state.get_data()
    file_id: str = data["file_id"]

    async with async_session_factory() as session:
        await get_or_create_user(session, callback.from_user)
        photo = await upload_photo(
            session,
            author_id=callback.from_user.id,
            telegram_file_id=file_id,
            allow_comments=allow,
        )

    await state.clear()
    comments_note = "✅ Комментарии разрешены" if allow else "🚫 Комментарии отключены"
    await callback.message.edit_text(
        f"🎉 Фото #{photo.id} загружено!\n{comments_note}\n\n"
        f"👀 Используй /browse чтобы смотреть ленту."
    )
    await callback.answer()
