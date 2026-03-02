"""Anonymous dialog — reply proxying."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.core.database import async_session_factory
from src.core.services.message import create_message, get_message

router = Router(name="dialog")


class DialogStates(StatesGroup):
    waiting_reply = State()


@router.callback_query(lambda c: c.data and c.data.startswith("dialog:reply:"))
async def cb_dialog_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    original_msg_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        original = await get_message(session, original_msg_id)
        if original is None:
            await callback.answer("Сообщение не найдено.", show_alert=True)
            return

    # The replier is the current user; the recipient is the original sender
    if original.recipient_id != callback.from_user.id:
        await callback.answer("Это не твоё сообщение.", show_alert=True)
        return

    await state.set_state(DialogStates.waiting_reply)
    await state.update_data(
        original_msg_id=original_msg_id,
        recipient_id=original.sender_id,
        photo_id=original.photo_id,
    )
    await callback.message.answer(
        "↩️ Напиши ответ (анонимно):\n(или /cancel для отмены)"
    )
    await callback.answer()


@router.message(DialogStates.waiting_reply, F.text)
async def handle_dialog_reply(message: Message, state: FSMContext) -> None:
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
        )

    await state.clear()
    await message.answer("✅ Ответ отправлен анонимно!")

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
        pass
