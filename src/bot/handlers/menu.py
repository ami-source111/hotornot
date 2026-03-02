"""User menu — stats, my photos, navigation."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.database import async_session_factory
from src.core.services.user import get_or_create_user
from src.core.services.rating import get_my_photos_reactions, REACTION_EMOJI
from src.core.services.photo import get_author_photos, delete_photo, toggle_comments
from src.core.models import ReactionType
from src.bot.keyboards import main_menu_keyboard

router = Router(name="menu")


# ---------------------------------------------------------------------------
# /menu
# ---------------------------------------------------------------------------

@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    async with async_session_factory() as session:
        user = await get_or_create_user(session, message.from_user)
    name = user.display_name or user.first_name or "пользователь"
    await message.answer(
        f"🏠 Главное меню, {name}!",
        reply_markup=main_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# /stats — reaction stats
# ---------------------------------------------------------------------------

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await _show_stats(message, message.from_user.id)


@router.callback_query(lambda c: c.data == "menu:stats")
async def cb_menu_stats(callback: CallbackQuery) -> None:
    await _show_stats(callback.message, callback.from_user.id)
    await callback.answer()


async def _show_stats(target: Message, user_id: int) -> None:
    async with async_session_factory() as session:
        stats = await get_my_photos_reactions(session, user_id)

    if not stats:
        await target.answer("📊 У тебя пока нет фото в ленте.")
        return

    lines = ["📊 Реакции на твои фото:\n"]
    total_all = 0
    for s in stats:
        counts = s["counts"]
        total = s["total"]
        total_all += total
        parts = []
        for r in ReactionType:
            c = counts.get(r.value, 0)
            if c:
                parts.append(f"{REACTION_EMOJI[r]}{c}")
        reactions_str = "  ".join(parts) if parts else "нет реакций"
        lines.append(f"📸 Фото #{s['photo_id']}: {reactions_str} (всего: {total})")

    lines.append(f"\n💫 Итого реакций: {total_all}")
    await target.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# /myphotos — manage my photos
# ---------------------------------------------------------------------------

@router.message(Command("myphotos"))
async def cmd_myphotos(message: Message) -> None:
    await _show_my_photos(message, message.from_user.id)


@router.callback_query(lambda c: c.data == "menu:photos")
async def cb_menu_photos(callback: CallbackQuery) -> None:
    await _show_my_photos(callback.message, callback.from_user.id)
    await callback.answer()


async def _show_my_photos(target: Message, user_id: int) -> None:
    async with async_session_factory() as session:
        photos = await get_author_photos(session, user_id)

    if not photos:
        builder = InlineKeyboardBuilder()
        builder.button(text="📸 Загрузить фото", callback_data="menu:upload")
        await target.answer(
            "🖼 У тебя нет фото в ленте.\nЗагрузи первое!",
            reply_markup=builder.as_markup(),
        )
        return

    builder = InlineKeyboardBuilder()
    for p in photos:
        comments_icon = "💬" if p.allow_comments else "🔇"
        builder.button(
            text=f"📸 #{p.id} {comments_icon}",
            callback_data=f"myphoto:view:{p.id}"
        )
    builder.button(text="➕ Загрузить ещё", callback_data="menu:upload")
    builder.adjust(3)

    await target.answer(
        f"🖼 Твои фото ({len(photos)} шт.):\n"
        "💬 = комментарии разрешены, 🔇 = отключены\n"
        "Нажми на фото для управления:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("myphoto:view:"))
async def cb_myphoto_view(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    from src.core.services.photo import get_photo
    async with async_session_factory() as session:
        from src.core.services.rating import get_photo_reactions
        photo = await get_photo(session, photo_id)
        if photo is None or photo.author_id != user_id:
            await callback.answer("Фото не найдено.", show_alert=True)
            return
        counts = await get_photo_reactions(session, photo_id)

    parts = []
    for r in ReactionType:
        c = counts.get(r.value, 0)
        if c:
            parts.append(f"{REACTION_EMOJI[r]}{c}")
    reactions_str = "  ".join(parts) if parts else "нет реакций"
    comments_status = "✅ разрешены" if photo.allow_comments else "🚫 отключены"

    builder = InlineKeyboardBuilder()
    toggle_label = "🔇 Отключить комментарии" if photo.allow_comments else "💬 Включить комментарии"
    builder.button(text=toggle_label, callback_data=f"myphoto:toggle_comments:{photo_id}")
    builder.button(text="🗑 Удалить фото", callback_data=f"myphoto:delete:{photo_id}")
    builder.button(text="⬅️ Назад", callback_data="menu:photos")
    builder.adjust(1)

    try:
        await callback.message.answer_photo(
            photo=photo.telegram_file_id,
            caption=(
                f"📸 Фото #{photo_id}\n"
                f"💫 Реакции: {reactions_str}\n"
                f"💬 Комментарии: {comments_status}"
            ),
            reply_markup=builder.as_markup(),
        )
    except Exception:
        await callback.message.answer(
            f"📸 Фото #{photo_id}\n💫 {reactions_str}\n💬 Комментарии: {comments_status}",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("myphoto:toggle_comments:"))
async def cb_myphoto_toggle_comments(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        new_val = await toggle_comments(session, photo_id, callback.from_user.id)
    if new_val is None:
        await callback.answer("Фото не найдено.", show_alert=True)
        return
    status = "разрешены ✅" if new_val else "отключены 🚫"
    await callback.answer(f"Комментарии {status}", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("myphoto:delete:"))
async def cb_myphoto_delete(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])

    # Confirm step
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"myphoto:delete_confirm:{photo_id}")
    builder.button(text="❌ Отмена", callback_data=f"myphoto:view:{photo_id}")
    builder.adjust(2)
    await callback.message.answer(
        f"⚠️ Удалить фото #{photo_id}? Это действие нельзя отменить.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("myphoto:delete_confirm:"))
async def cb_myphoto_delete_confirm(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])
    async with async_session_factory() as session:
        ok = await delete_photo(session, photo_id, callback.from_user.id)
    if ok:
        await callback.message.edit_text(f"✅ Фото #{photo_id} удалено.")
    else:
        await callback.answer("Фото не найдено.", show_alert=True)
    await callback.answer()


# ---------------------------------------------------------------------------
# Upload shortcut from menu
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == "menu:upload")
async def cb_menu_upload(callback: CallbackQuery, state: FSMContext) -> None:
    from src.core.services.user import get_user
    from src.core.models import Gender
    async with async_session_factory() as session:
        user = await get_user(session, callback.from_user.id)
    if user is None or user.gender == Gender.unknown:
        await callback.answer("Сначала заверши регистрацию (/start)", show_alert=True)
        return
    from src.bot.keyboards import cancel_keyboard
    from aiogram.fsm.state import State
    # Trigger upload flow
    from src.bot.handlers.upload import UploadStates
    await state.set_state(UploadStates.waiting_photo)
    await callback.message.answer(
        "📸 Отправь фото, которое хочешь добавить в ленту.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()
