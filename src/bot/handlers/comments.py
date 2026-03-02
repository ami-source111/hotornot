"""Handlers for comments and comment-initiated dialogs."""
from __future__ import annotations

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.database import async_session_factory
from src.core.services.comment import add_comment, get_active_comments, get_comment
from src.core.services.photo import get_photo
from src.core.services.user import get_user
from src.bot.keyboards import next_photo_keyboard

router = Router(name="comments")


class CommentStates(StatesGroup):
    waiting_comment_text = State()
    waiting_reply_text = State()    # photo author replying to commenter


# ---------------------------------------------------------------------------
# View comments
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("comments:view:"))
async def cb_view_comments(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        photo = await get_photo(session, photo_id)
        if photo is None:
            await callback.answer("Фото не найдено.", show_alert=True)
            return
        if not photo.allow_comments:
            await callback.answer("Комментарии к этому фото отключены.", show_alert=True)
            return
        comments = await get_active_comments(session, photo_id)

    if not comments:
        text = f"💬 Комментарии к фото #{photo_id}:\n\nПока нет комментариев."
    else:
        lines = [f"💬 Комментарии к фото #{photo_id}:\n"]
        for i, c in enumerate(comments, 1):
            lines.append(f"{i}. {c.text[:200]}")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Написать комментарий", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее фото", callback_data="browse:next:all")
    builder.button(text="🏠 Главное меню", callback_data="nav:menu")
    builder.adjust(1)

    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ---------------------------------------------------------------------------
# Add comment (viewer -> photo)
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("comments:add:"))
async def cb_add_comment_start(callback: CallbackQuery, state: FSMContext) -> None:
    photo_id = int(callback.data.split(":")[2])
    await state.set_state(CommentStates.waiting_comment_text)
    await state.update_data(photo_id=photo_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="cancel:comment")
    await callback.message.answer(
        f"✏️ Напиши комментарий к фото #{photo_id}:",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel:comment")
async def cb_cancel_comment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


async def _process_comment(
    message: Message,
    state: FSMContext,
    text: str,
    media_file_id: str | None = None,
) -> None:
    """Save comment and notify photo author. Handles both text and photo comments."""
    data = await state.get_data()
    photo_id: int = data["photo_id"]

    async with async_session_factory() as session:
        comment = await add_comment(session, message.from_user.id, photo_id, text, media_file_id=media_file_id)
        if comment is None:
            await state.clear()
            await message.answer("❌ Комментарии к этому фото отключены.")
            return
        photo = await get_photo(session, photo_id)
        author = await get_user(session, photo.author_id) if photo else None
        commenter = await get_user(session, message.from_user.id)
        comment_id = comment.id

    await state.clear()

    # Post-comment keyboard (feature C)
    post_builder = InlineKeyboardBuilder()
    post_builder.button(text="✏️ Написать ещё", callback_data=f"comments:add:{photo_id}")
    post_builder.button(text="➡️ Следующее фото", callback_data="browse:next:all")
    post_builder.button(text="🏠 Главное меню", callback_data="nav:menu")
    post_builder.adjust(2, 1)
    await message.answer("✅ Комментарий добавлен!", reply_markup=post_builder.as_markup())

    # Notify photo author (if they're not the commenter)
    if author and author.id != message.from_user.id:
        commenter_name = (commenter.display_name or commenter.first_name or "Кто-то") if commenter else "Кто-то"
        preview = text[:100] + ("…" if len(text) > 100 else "")

        notify_builder = InlineKeyboardBuilder()
        notify_builder.button(
            text="↩️ Ответить",
            callback_data=f"dialog:start:{comment_id}:{message.from_user.id}:{photo_id}"
        )
        notify_builder.button(
            text="🚫 Пожаловаться",
            callback_data=f"report:comment:{comment_id}"
        )
        notify_builder.adjust(2)

        try:
            bot: Bot = message.bot
            notify_text = (
                f"💬 К вашему фото #{photo_id} новый комментарий:\n\n"
                f"«{preview}»"
            )
            if media_file_id:
                await bot.send_photo(
                    chat_id=author.id,
                    photo=media_file_id,
                    caption=notify_text,
                    reply_markup=notify_builder.as_markup(),
                )
            else:
                await bot.send_message(
                    chat_id=author.id,
                    text=notify_text,
                    reply_markup=notify_builder.as_markup(),
                )
        except Exception:
            pass


@router.message(CommentStates.waiting_comment_text, F.text)
async def handle_comment_text(message: Message, state: FSMContext) -> None:
    await _process_comment(message, state, text=message.text.strip())


@router.message(CommentStates.waiting_comment_text, F.photo)
async def handle_comment_photo(message: Message, state: FSMContext) -> None:
    """User sends a photo as a comment (with optional caption)."""
    file_id = message.photo[-1].file_id
    caption_text = (message.caption or "").strip() or "📷"
    await _process_comment(message, state, text=caption_text, media_file_id=file_id)


# ---------------------------------------------------------------------------
# Photo author replies to a comment → starts / continues a dialog
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("dialog:start:"))
async def cb_dialog_start(callback: CallbackQuery, state: FSMContext) -> None:
    """
    callback_data: dialog:start:{comment_id}:{commenter_id}:{photo_id}
    Triggered when photo author taps "Ответить" on comment notification.
    """
    parts = callback.data.split(":")
    comment_id = int(parts[2])
    commenter_id = int(parts[3])
    photo_id = int(parts[4])

    # Verify caller is the photo author
    async with async_session_factory() as session:
        photo = await get_photo(session, photo_id)
        if photo is None or photo.author_id != callback.from_user.id:
            await callback.answer("Это не ваше фото.", show_alert=True)
            return

    await state.set_state(CommentStates.waiting_reply_text)
    await state.update_data(
        comment_id=comment_id,
        recipient_id=commenter_id,
        photo_id=photo_id,
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="cancel:dialog_reply")
    await callback.message.answer(
        "📨 Напиши анонимный ответ автору комментария:",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel:dialog_reply")
async def cb_cancel_dialog_reply(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


@router.message(CommentStates.waiting_reply_text, F.text)
async def handle_reply_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = message.text.strip()
    comment_id = data.get("comment_id")
    recipient_id = data["recipient_id"]
    photo_id = data.get("photo_id")

    from src.core.services.dialog import get_or_create_dialog, add_message as add_dialog_message
    async with async_session_factory() as session:
        dialog, is_new = await get_or_create_dialog(
            session,
            comment_id=comment_id,
            initiator_id=message.from_user.id,
            recipient_id=recipient_id,
        )
        msg = await add_dialog_message(
            session,
            dialog_id=dialog.id,
            sender_id=message.from_user.id,
            recipient_id=recipient_id,
            text=text,
            photo_id=photo_id,
        )
        dialog_id = dialog.id

    await state.clear()
    await message.answer("✅ Ответ отправлен анонимно!")

    # Notify commenter
    bot: Bot = message.bot
    reply_builder = InlineKeyboardBuilder()
    reply_builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{dialog_id}:{message.from_user.id}")
    reply_builder.button(text="🚫 Пожаловаться", callback_data=f"report:message:{msg.id}")
    reply_builder.button(text="🔴 Закрыть диалог", callback_data=f"dialog:close:{dialog_id}")
    reply_builder.adjust(2, 1)

    try:
        await bot.send_message(
            chat_id=recipient_id,
            text=f"📨 Автор фото #{photo_id} ответил на твой комментарий:\n\n«{text}»",
            reply_markup=reply_builder.as_markup(),
        )
    except Exception:
        pass
