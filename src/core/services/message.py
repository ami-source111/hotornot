"""Message service — legacy compatibility wrapper (use dialog service for new code)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Message


async def create_message(
    session: AsyncSession,
    sender_id: int,
    recipient_id: int,
    text: str,
    photo_id: int | None = None,
    comment_id: int | None = None,  # legacy param, ignored (dialog_id used instead)
    dialog_id: int | None = None,
) -> Message:
    msg = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        text=text,
        photo_id=photo_id,
        dialog_id=dialog_id,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def get_message(session: AsyncSession, message_id: int) -> Message | None:
    result = await session.execute(select(Message).where(Message.id == message_id))
    return result.scalar_one_or_none()
