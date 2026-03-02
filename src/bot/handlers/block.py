"""Handlers for blocking photo authors."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from src.core.database import async_session_factory
from src.core.services.block import block_user
from src.core.services.photo import get_photo

router = Router(name="block")


@router.callback_query(lambda c: c.data and c.data.startswith("block:author:"))
async def cb_block_author(callback: CallbackQuery) -> None:
    photo_id = int(callback.data.split(":")[2])

    async with async_session_factory() as session:
        photo = await get_photo(session, photo_id)
        if photo is None:
            await callback.answer("Фото не найдено.", show_alert=True)
            return
        if photo.author_id == callback.from_user.id:
            await callback.answer("Нельзя заблокировать себя.", show_alert=True)
            return
        result = await block_user(session, callback.from_user.id, photo.author_id)

    if result is None:
        await callback.answer("Этот пользователь уже заблокирован.", show_alert=True)
    else:
        await callback.answer("🚫 Автор заблокирован. Его фото больше не будут показаны.", show_alert=True)
