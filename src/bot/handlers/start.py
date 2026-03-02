"""Handlers for /start command and gender selection."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from src.core.database import async_session_factory
from src.core.models import Gender
from src.core.services.user import get_or_create_user, set_gender
from src.bot.keyboards import gender_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user)

    if user.gender == Gender.unknown:
        await message.answer(
            "👋 Привет! Добро пожаловать в RateApp.\n\n"
            "Сначала укажи свой пол — это нужно для фильтрации ленты:",
            reply_markup=gender_keyboard(),
        )
    else:
        await message.answer(
            f"👋 С возвращением!\n\n"
            f"Команды:\n"
            f"📸 /upload — загрузить фото\n"
            f"👀 /browse — смотреть ленту"
        )


@router.callback_query(lambda c: c.data and c.data.startswith("gender:"))
async def cb_gender(callback: CallbackQuery) -> None:
    gender_str = callback.data.split(":")[1]  # M or F
    gender = Gender.male if gender_str == "M" else Gender.female

    async with async_session_factory() as session:
        await get_or_create_user(session, callback.from_user)
        await set_gender(session, callback.from_user.id, gender)

    label = "Мужской" if gender == Gender.male else "Женский"
    await callback.message.edit_text(
        f"✅ Пол сохранён: {label}\n\n"
        f"Теперь ты можешь:\n"
        f"📸 /upload — загрузить фото\n"
        f"👀 /browse — смотреть ленту"
    )
    await callback.answer()
