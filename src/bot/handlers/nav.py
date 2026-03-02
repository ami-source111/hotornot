"""Global navigation callbacks: nav:feed and nav:menu."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.bot.keyboards import main_menu_keyboard

router = Router(name="nav")


@router.callback_query(lambda c: c.data == "nav:menu")
async def cb_nav_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear any FSM state and show main menu."""
    await state.clear()
    await callback.message.answer("🏠 Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("nav:feed"))
async def cb_nav_feed(callback: CallbackQuery, state: FSMContext) -> None:
    """Clear FSM state and jump to the feed."""
    parts = callback.data.split(":")
    gender_filter = parts[2] if len(parts) > 2 else "all"

    await state.clear()
    from src.bot.handlers.browse import BrowseStates, _send_photo
    await state.set_state(BrowseStates.browsing)
    await state.update_data(gender_filter=gender_filter)
    await callback.answer("📰 Переходим в ленту...")
    await _send_photo(callback.message, callback.from_user.id, gender_filter)
