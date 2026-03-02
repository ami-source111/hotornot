"""Handlers for user reports (complaints)."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from src.core.database import async_session_factory
from src.core.models import ReportTarget
from src.core.services.report import create_report

router = Router(name="report")

TARGET_MAP = {
    "photo": ReportTarget.photo,
    "comment": ReportTarget.comment,
    "message": ReportTarget.message,
}


@router.callback_query(lambda c: c.data and c.data.startswith("report:"))
async def cb_report(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    # report:photo:123  or report:comment:456  or report:message:789
    target_str = parts[1]
    target_id = int(parts[2])

    target_type = TARGET_MAP.get(target_str)
    if target_type is None:
        await callback.answer("Неизвестный тип жалобы.", show_alert=True)
        return

    async with async_session_factory() as session:
        await create_report(
            session,
            reporter_id=callback.from_user.id,
            target_type=target_type,
            target_id=target_id,
        )

    await callback.answer("✅ Жалоба отправлена. Спасибо!", show_alert=True)
