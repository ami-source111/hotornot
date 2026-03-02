"""Dialog service — anonymous proxied conversations."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models import Dialog, DialogStatus, Message, MessageStatus


async def get_or_create_dialog(
    session: AsyncSession,
    comment_id: int | None,
    initiator_id: int,
    recipient_id: int,
) -> tuple[Dialog, bool]:
    """
    Find existing dialog for this comment (if any) or create a new one.
    Returns (dialog, is_new).
    initiator = photo author who replies, recipient = commenter.
    """
    if comment_id:
        result = await session.execute(
            select(Dialog).where(Dialog.comment_id == comment_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

    dialog = Dialog(
        comment_id=comment_id,
        initiator_id=initiator_id,
        recipient_id=recipient_id,
        status=DialogStatus.active,
    )
    session.add(dialog)
    await session.commit()
    await session.refresh(dialog)
    return dialog, True


async def add_message(
    session: AsyncSession,
    dialog_id: int,
    sender_id: int,
    recipient_id: int,
    text: str,
    photo_id: int | None = None,
) -> Message:
    msg = Message(
        dialog_id=dialog_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        text=text,
        photo_id=photo_id,
        status=MessageStatus.active,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


async def get_dialog(session: AsyncSession, dialog_id: int) -> Dialog | None:
    result = await session.execute(
        select(Dialog).where(Dialog.id == dialog_id)
    )
    return result.scalar_one_or_none()


async def get_user_dialogs(session: AsyncSession, user_id: int) -> list[Dialog]:
    """All active dialogs where user is initiator or recipient."""
    result = await session.execute(
        select(Dialog)
        .where(
            Dialog.status == DialogStatus.active,
            or_(Dialog.initiator_id == user_id, Dialog.recipient_id == user_id),
        )
        .order_by(Dialog.created_at.desc())
    )
    return list(result.scalars().all())


async def get_dialog_messages(session: AsyncSession, dialog_id: int) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.dialog_id == dialog_id, Message.status == MessageStatus.active)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def close_dialog(session: AsyncSession, dialog_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(Dialog).where(
            Dialog.id == dialog_id,
            or_(Dialog.initiator_id == user_id, Dialog.recipient_id == user_id),
        )
    )
    dialog = result.scalar_one_or_none()
    if dialog is None:
        return False
    dialog.status = DialogStatus.closed
    await session.commit()
    return True


async def get_message(session: AsyncSession, message_id: int) -> Message | None:
    result = await session.execute(select(Message).where(Message.id == message_id))
    return result.scalar_one_or_none()
