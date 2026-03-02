"""Handlers for /browse command — feed browsing and reactions."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from src.core.config import settings
from src.core.database import async_session_factory
from src.core.models import ReactionType
from src.core.services.photo import get_author_photos, get_next_photo, get_photo
from src.core.services.rating import REACTION_EMOJI, set_reaction
from src.core.services.user import get_or_create_user, get_user
from src.bot.keyboards import (
    author_profile_keyboard,
    feed_filter_keyboard,
    post_reaction_keyboard,
    reaction_keyboard,
)

router = Router(name="browse")

FILTER_LABELS = {"all": "Все", "M": "Парни", "F": "Девушки"}


class BrowseStates(StatesGroup):
    browsing = State()


async def _send_photo(
    target: Message,
    viewer_id: int,
    gender_filter: str,
) -> None:
    """Fetch the next unrated photo and send it with reaction buttons."""
    async with async_session_factory() as session:
        photo = await get_next_photo(session, viewer_id, gender_filter)
        if photo is None:
            await target.answer(
                "😔 Новых фото не найдено.\n"
                "Попробуй сменить фильтр или зайди позже."
            )
            return

        author = await get_user(session, photo.author_id)
        author_name = (author.display_name or author.first_name or "Аноним") if author else "Аноним"
        author_gender = author.gender.value if author else "unknown"
        photo_id = photo.id
        allow_comments = photo.allow_comments
        file_id = photo.telegram_file_id
        file_path = photo.file_path

    gender_emoji = "👨" if author_gender == "M" else ("👩" if author_gender == "F" else "👤")
    caption = f"{gender_emoji} <b>{author_name}</b>"

    if file_path and (settings.media_dir / file_path).exists():
        photo_input = FSInputFile(str(settings.media_dir / file_path))
    else:
        photo_input = file_id

    await target.answer_photo(
        photo=photo_input,
        caption=caption,
        reply_markup=reaction_keyboard(photo_id, allow_comments, gender_filter, author_name),
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


@router.callback_query(lambda c: c.data == "menu:browse")
async def cb_menu_browse(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BrowseStates.browsing)
    await state.update_data(gender_filter="all")
    await callback.message.answer(
        "👀 Лента фото. Выбери фильтр:",
        reply_markup=feed_filter_keyboard("all"),
    )
    await _send_photo(callback.message, callback.from_user.id, "all")
    await callback.answer()


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


@router.callback_query(lambda c: c.data and c.data.startswith("react:"))
async def cb_react(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle reaction: react:{photo_id}:{reaction}:{gender_filter}"""
    parts = callback.data.split(":")
    photo_id = int(parts[1])
    reaction_str = parts[2]
    gender_filter = parts[3] if len(parts) > 3 else "all"

    try:
        reaction = ReactionType(reaction_str)
    except ValueError:
        await callback.answer("Неверная реакция.", show_alert=True)
        return

    async with async_session_factory() as session:
        rating, is_new = await set_reaction(session, callback.from_user.id, photo_id, reaction)
        photo = await get_photo(session, photo_id)
        author = await get_user(session, photo.author_id) if photo else None
        allow_comments = photo.allow_comments if photo else False
        author_name = (author.display_name or author.first_name or "Аноним") if author else "Аноним"

    emoji = REACTION_EMOJI.get(reaction, "✅")
    await callback.answer(f"{emoji} Реакция {'поставлена' if is_new else 'изменена'}!")

    try:
        await callback.message.edit_reply_markup(
            reply_markup=post_reaction_keyboard(photo_id, allow_comments, gender_filter, author_name)
        )
    except Exception:
        pass

    await _send_photo(callback.message, callback.from_user.id, gender_filter)


# ---------------------------------------------------------------------------
# Author profile gallery
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("profile:photo:"))
async def cb_author_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Show first photo of the author of the given photo."""
    photo_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        photo = await get_photo(session, photo_id)
        if photo is None:
            await callback.answer("Фото не найдено.", show_alert=True)
            return
        author = await get_user(session, photo.author_id)
        author_name = (author.display_name or author.first_name or "Аноним") if author else "Аноним"
        author_gender = author.gender.value if author else "unknown"
        author_photos = await get_author_photos(session, photo.author_id)

    if not author_photos:
        await callback.answer("У этого автора нет доступных фото.", show_alert=True)
        return

    await state.update_data(profile_author_id=photo.author_id, profile_photo_index=0)
    await _send_author_photo(
        callback.message, author_photos[0], author_name, author_gender, 0, len(author_photos)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("profile:next:"))
async def cb_profile_next(callback: CallbackQuery, state: FSMContext) -> None:
    """Next photo in author profile gallery."""
    data = await state.get_data()
    author_id = data.get("profile_author_id")
    index = data.get("profile_photo_index", 0) + 1

    if not author_id:
        await callback.answer("Сессия устарела.", show_alert=True)
        return

    async with async_session_factory() as session:
        author = await get_user(session, author_id)
        author_name = (author.display_name or author.first_name or "Аноним") if author else "Аноним"
        author_gender = author.gender.value if author else "unknown"
        author_photos = await get_author_photos(session, author_id)

    if index >= len(author_photos):
        await callback.answer("Больше фото нет.", show_alert=True)
        return

    await state.update_data(profile_photo_index=index)
    await _send_author_photo(
        callback.message, author_photos[index], author_name, author_gender, index, len(author_photos)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "profile:back")
async def cb_profile_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main feed from author profile."""
    data = await state.get_data()
    gender_filter = data.get("gender_filter", "all")
    await callback.answer("Возвращаемся в ленту...")
    await _send_photo(callback.message, callback.from_user.id, gender_filter)


async def _send_author_photo(
    target: Message,
    photo,
    author_name: str,
    author_gender: str,
    index: int,
    total: int,
) -> None:
    """Send one photo from the author's gallery with navigation buttons."""
    gender_emoji = "👨" if author_gender == "M" else ("👩" if author_gender == "F" else "👤")
    caption = f"{gender_emoji} <b>{author_name}</b>  •  {index + 1}/{total}"

    if photo.file_path and (settings.media_dir / photo.file_path).exists():
        photo_input = FSInputFile(str(settings.media_dir / photo.file_path))
    else:
        photo_input = photo.telegram_file_id

    await target.answer_photo(
        photo=photo_input,
        caption=caption,
        reply_markup=author_profile_keyboard(has_next=(index + 1 < total)),
    )
