"""Handlers for viewing and adding comments to photos."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.core.database import async_session_factory
from src.core.services.comment import add_comment, get_active_comments, get_comment
from src.core.services.message import create_message
from src.core.services.photo import get_photo
from src.bot.keyboards import next_photo_keyboard

router = Router(name="comments")


class CommentStates(StatesGroup):
    waiting_comment_text = State()
    waiting_reply_text = State()


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

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Написать комментарий", callback_data=f"comments:add:{photo_id}")
    builder.button(text="↩️ Назад", callback_data=f"comments:back:{photo_id}")
    builder.adjust(1)

    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("comments:add:"))
async def cb_add_comment_start(callback: CallbackQuery, state: FSMContext) -> None:
    photo_id = int(callback.data.split(":")[2])
    await state.set_state(CommentStates.waiting_comment_text)
    await state.update_data(photo_id=photo_id)
    await callback.message.answer(
        f"✏️ Напиши комментарий к фото #{photo_id}:\n(или отправь /cancel для отмены)"
    )
    await callback.answer()


@router.message(CommentStates.waiting_comment_text, F.text)
async def handle_comment_text(message: Message, state: FSMContext) -> None:
    if message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.")
        return

    data = await state.get_data()
    photo_id: int = data["photo_id"]
    text = message.text.strip()

    async with async_session_factory() as session:
        comment = await add_comment(session, message.from_user.id, photo_id, text)

    await state.clear()
    if comment is None:
        await message.answer("❌ Не удалось добавить комментарий. Возможно, комментарии к этому фото отключены.")
    else:
        await message.answer(f"✅ Комментарий #{comment.id} добавлен!")


@router.callback_query(lambda c: c.data and c.data.startswith("comments:reply:"))
async def cb_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Initiate anonymous reply to a comment author."""
    parts = callback.data.split(":")
    comment_id = int(parts[2])

    async with async_session_factory() as session:
        comment = await get_comment(session, comment_id)
        if comment is None:
            await callback.answer("Комментарий не найден.", show_alert=True)
            return

    if comment.author_id == callback.from_user.id:
        await callback.answer("Нельзя ответить самому себе.", show_alert=True)
        return

    await state.set_state(CommentStates.waiting_reply_text)
    await state.update_data(
        comment_id=comment_id,
        recipient_id=comment.author_id,
        photo_id=comment.photo_id,
    )
    await callback.message.answer(
        "📨 Напиши анонимное сообщение автору комментария:\n(или /cancel для отмены)"
    )
    await callback.answer()


@router.message(CommentStates.waiting_reply_text, F.text)
async def handle_reply_text(message: Message, state: FSMContext) -> None:
    if message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.")
        return

    data = await state.get_data()
    text = message.text.strip()

    async with async_session_factory() as session:
        msg = await create_message(
            session,
            sender_id=message.from_user.id,
            recipient_id=data["recipient_id"],
            text=text,
            photo_id=data.get("photo_id"),
            comment_id=data.get("comment_id"),
        )

    await state.clear()
    await message.answer(f"✅ Анонимное сообщение отправлено!")

    # Notify recipient via bot
    from aiogram import Bot
    bot: Bot = message.bot
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{msg.id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:message:{msg.id}")
    builder.adjust(2)

    try:
        await bot.send_message(
            chat_id=data["recipient_id"],
            text=f"📨 Тебе анонимное сообщение:\n\n{text}",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        pass  # User may have blocked the bot
