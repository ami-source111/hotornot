"""Anonymous dialog — continuing conversation and chat list."""
from __future__ import annotations

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.database import async_session_factory
from src.core.services.dialog import (
    get_dialog,
    get_user_dialogs,
    add_message as add_dialog_message,
    close_dialog,
)
from src.core.services.user import get_user

router = Router(name="dialog")


class DialogStates(StatesGroup):
    waiting_reply = State()


# ---------------------------------------------------------------------------
# /chats — list of active dialogs
# ---------------------------------------------------------------------------

@router.message(Command("chats"))
async def cmd_chats(message: Message) -> None:
    await _show_chats(message, message.from_user.id)


@router.callback_query(lambda c: c.data == "menu:chats")
async def cb_menu_chats(callback: CallbackQuery) -> None:
    await _show_chats(callback.message, callback.from_user.id)
    await callback.answer()


async def _show_chats(target: Message, user_id: int) -> None:
    async with async_session_factory() as session:
        dialogs = await get_user_dialogs(session, user_id)

    if not dialogs:
        await target.answer(
            "💬 У тебя нет активных переписок.\n\n"
            "Оставь комментарий под фото или дождись ответа автора."
        )
        return

    builder = InlineKeyboardBuilder()
    for d in dialogs:
        label = f"💬 Диалог #{d.id} (фото #{d.comment_id or '—'})"
        builder.button(text=label, callback_data=f"dialog:open:{d.id}")
    builder.adjust(1)

    await target.answer(
        f"💬 Твои переписки ({len(dialogs)} активных):",
        reply_markup=builder.as_markup(),
    )


# ---------------------------------------------------------------------------
# Open a dialog
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("dialog:open:"))
async def cb_dialog_open(callback: CallbackQuery, state: FSMContext) -> None:
    dialog_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        dialog = await get_dialog(session, dialog_id)
        if dialog is None:
            await callback.answer("Диалог не найден.", show_alert=True)
            return
        if dialog.initiator_id != user_id and dialog.recipient_id != user_id:
            await callback.answer("Нет доступа.", show_alert=True)
            return

        from src.core.services.dialog import get_dialog_messages
        messages = await get_dialog_messages(session, dialog_id)
        # Determine other party
        other_id = dialog.recipient_id if dialog.initiator_id == user_id else dialog.initiator_id

    if not messages:
        text = f"💬 Диалог #{dialog_id}\nСообщений пока нет."
    else:
        lines = [f"💬 Диалог #{dialog_id}:\n"]
        for m in messages[-10:]:  # last 10 messages
            role = "Ты" if m.sender_id == user_id else "Собеседник"
            lines.append(f"[{role}]: {m.text[:150]}")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{dialog_id}:{other_id}")
    builder.button(text="🔴 Закрыть диалог", callback_data=f"dialog:close:{dialog_id}")
    builder.button(text="⬅️ К списку чатов", callback_data="menu:chats")
    builder.adjust(2, 1)

    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ---------------------------------------------------------------------------
# Reply in existing dialog
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("dialog:reply:"))
async def cb_dialog_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    """callback_data: dialog:reply:{dialog_id}:{recipient_id}"""
    parts = callback.data.split(":")
    dialog_id = int(parts[2])
    recipient_id = int(parts[3])
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        dialog = await get_dialog(session, dialog_id)
        if dialog is None:
            await callback.answer("Диалог не найден.", show_alert=True)
            return
        if dialog.initiator_id != user_id and dialog.recipient_id != user_id:
            await callback.answer("Нет доступа.", show_alert=True)
            return

    await state.set_state(DialogStates.waiting_reply)
    await state.update_data(dialog_id=dialog_id, recipient_id=recipient_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data=f"dialog:open:{dialog_id}")
    await callback.message.answer(
        "↩️ Напиши ответ (анонимно):",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(DialogStates.waiting_reply, F.text)
async def handle_dialog_reply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    dialog_id: int = data["dialog_id"]
    recipient_id: int = data["recipient_id"]
    text = message.text.strip()

    async with async_session_factory() as session:
        dialog = await get_dialog(session, dialog_id)
        if dialog is None:
            await state.clear()
            await message.answer("❌ Диалог не найден.")
            return
        msg = await add_dialog_message(
            session,
            dialog_id=dialog_id,
            sender_id=message.from_user.id,
            recipient_id=recipient_id,
            text=text,
        )

    await state.clear()
    from src.bot.keyboards import nav_keyboard
    await message.answer("✅ Сообщение отправлено!", reply_markup=nav_keyboard())

    # Notify recipient
    bot: Bot = message.bot
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{dialog_id}:{message.from_user.id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:message:{msg.id}")
    builder.button(text="🔴 Закрыть диалог", callback_data=f"dialog:close:{dialog_id}")
    builder.adjust(2, 1)

    try:
        await bot.send_message(
            chat_id=recipient_id,
            text=f"📨 Новое сообщение в диалоге #{dialog_id}:\n\n«{text}»",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Close dialog
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("dialog:close:"))
async def cb_dialog_close(callback: CallbackQuery, state: FSMContext) -> None:
    dialog_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        ok = await close_dialog(session, dialog_id, user_id)

    if ok:
        from src.bot.keyboards import nav_keyboard
        await callback.message.answer(f"🔴 Диалог #{dialog_id} закрыт.", reply_markup=nav_keyboard())
    else:
        await callback.answer("Не удалось закрыть диалог.", show_alert=True)
    await callback.answer()
