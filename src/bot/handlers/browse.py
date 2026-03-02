"""Handlers for /browse command — feed browsing and rating."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.database import async_session_factory
from src.core.services.photo import get_next_photo
from src.core.services.rating import create_rating, get_photo_avg
from src.core.services.user import get_or_create_user
from src.bot.keyboards import feed_filter_keyboard, rating_keyboard

router = Router(name="browse")

FILTER_LABELS = {"all": "Все", "M": "Парни", "F": "Девушки"}


class BrowseStates(StatesGroup):
    browsing = State()


def _photo_action_keyboard(photo_id: int, allow_comments: bool, gender_filter: str):
    builder = InlineKeyboardBuilder()
    if allow_comments:
        builder.button(text="💬 Комментарии", callback_data=f"comments:view:{photo_id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:photo:{photo_id}")
    builder.button(text="🔒 Заблокировать автора", callback_data=f"block:author:{photo_id}")
    builder.button(text="➡️ Следующее фото", callback_data=f"browse:next:{gender_filter}")
    builder.button(text="🔍 Сменить фильтр", callback_data="browse:filter")
    builder.adjust(1)
    return builder.as_markup()


async def _send_photo(
    target: Message,
    viewer_id: int,
    gender_filter: str,
) -> None:
    async with async_session_factory() as session:
        photo = await get_next_photo(session, viewer_id, gender_filter)
        if photo is None:
            await target.answer(
                "😔 Новых фото не найдено.\n"
                "Попробуй сменить фильтр или зайди позже."
            )
            return

        avg = await get_photo_avg(session, photo.id)
        avg_str = f"{avg:.1f}" if avg is not None else "—"
        caption = (
            f"📸 Фото #{photo.id}\n"
            f"⭐ Средняя оценка: {avg_str}\n"
            f"💬 Комментарии: {'разрешены' if photo.allow_comments else 'отключены'}\n\n"
            f"Поставь оценку от 1 до 10:"
        )
        photo_file_id = photo.telegram_file_id
        allow_comments = photo.allow_comments
        photo_id = photo.id

    await target.answer_photo(
        photo=photo_file_id,
        caption=caption,
        reply_markup=rating_keyboard(photo_id),
    )


@router.message(Command("browse"))
async def cmd_browse(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        await get_or_create_user(session, message.from_user)

    await state.set_state(BrowseStates.browsing)
    await state.update_data(gender_filter="all")

    await message.answer(
        "👀 Лента фото. Выбери фильтр:",
        reply_markup=feed_filter_keyboard("all"),
    )
    await _send_photo(message, message.from_user.id, "all")


@router.callback_query(lambda c: c.data and c.data.startswith("filter:"))
async def cb_filter(callback: CallbackQuery, state: FSMContext) -> None:
    gender_filter = callback.data.split(":")[1]
    await state.update_data(gender_filter=gender_filter)
    await callback.message.edit_reply_markup(reply_markup=feed_filter_keyboard(gender_filter))
    await callback.answer(f"Фильтр: {FILTER_LABELS.get(gender_filter, gender_filter)}")
    await _send_photo(callback.message, callback.from_user.id, gender_filter)


@router.callback_query(lambda c: c.data and c.data.startswith("browse:next:"))
async def cb_next_photo(callback: CallbackQuery, state: FSMContext) -> None:
    gender_filter = callback.data.split(":")[2]
    await callback.answer()
    await _send_photo(callback.message, callback.from_user.id, gender_filter)


@router.callback_query(lambda c: c.data == "browse:filter")
async def cb_show_filter(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = data.get("gender_filter", "all")
    await callback.message.answer(
        "🔍 Выбери фильтр ленты:",
        reply_markup=feed_filter_keyboard(current),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("rate:"))
async def cb_rate(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    photo_id = int(parts[1])
    score = int(parts[2])

    async with async_session_factory() as session:
        rating = await create_rating(session, callback.from_user.id, photo_id, score)

    if rating is None:
        await callback.answer("⚠️ Ты уже оценил это фото.", show_alert=True)
        return

    data = await state.get_data()
    gender_filter = data.get("gender_filter", "all")

    await callback.answer(f"✅ Оценка {score}/10 принята!")

    # Fetch photo details to show action buttons
    async with async_session_factory() as session:
        from src.core.services.photo import get_photo
        photo = await get_photo(session, photo_id)
        allow_comments = photo.allow_comments if photo else False

    await callback.message.edit_reply_markup(
        reply_markup=_photo_action_keyboard(photo_id, allow_comments, gender_filter)
    )
