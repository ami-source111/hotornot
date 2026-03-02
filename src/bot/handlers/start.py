"""Handlers for /start command — registration flow and main menu."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.core.database import async_session_factory
from src.core.models import Gender
from src.core.services.user import get_or_create_user, set_gender, set_display_name
from src.bot.keyboards import gender_keyboard, main_menu_keyboard

router = Router(name="start")

HELP_TEXT = (
    "📸 /upload — загрузить фото\n"
    "👀 /browse — смотреть ленту\n"
    "💬 /chats — мои переписки\n"
    "📊 /stats — реакции на мои фото\n"
    "🖼 /myphotos — управление моими фото\n"
    "🏠 /menu — главное меню"
)


class RegistrationStates(StatesGroup):
    waiting_name = State()


async def _show_menu(target: Message, name: str) -> None:
    await target.answer(
        f"🏠 Главное меню, {name}!\n\n{HELP_TEXT}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user)

    # Step 1: needs gender
    if user.gender == Gender.unknown:
        await message.answer(
            "👋 Привет! Добро пожаловать в RateApp.\n\n"
            "Сначала укажи свой пол — это нужно для фильтрации ленты:",
            reply_markup=gender_keyboard(),
        )
        return

    # Step 2: needs display_name
    if not user.display_name:
        await state.set_state(RegistrationStates.waiting_name)
        await message.answer(
            "✏️ Придумай себе ник (1–64 символа).\n"
            "Он будет виден другим пользователям вместо твоего Telegram-имени:"
        )
        return

    # Fully registered
    await _show_menu(message, user.display_name)


@router.callback_query(lambda c: c.data and c.data.startswith("gender:"))
async def cb_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender_str = callback.data.split(":")[1]  # M or F
    gender = Gender.male if gender_str == "M" else Gender.female

    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user)
        user = await set_gender(session, callback.from_user.id, gender)

    label = "Мужской" if gender == Gender.male else "Женский"
    await callback.message.edit_text(f"✅ Пол сохранён: {label}")

    # Check if display_name needed
    if not user.display_name:
        await state.set_state(RegistrationStates.waiting_name)
        await callback.message.answer(
            "✏️ Теперь придумай себе ник (1–64 символа).\n"
            "Он будет виден другим пользователям:"
        )
    else:
        await _show_menu(callback.message, user.display_name)

    await callback.answer()


@router.message(RegistrationStates.waiting_name, F.text)
async def handle_display_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 1 or len(name) > 64:
        await message.answer("❌ Ник должен быть от 1 до 64 символов. Попробуй ещё раз:")
        return

    async with async_session_factory() as session:
        user = await set_display_name(session, message.from_user.id, name)

    await state.clear()
    await message.answer(f"✅ Ник сохранён: <b>{user.display_name}</b>")
    await _show_menu(message, user.display_name)
