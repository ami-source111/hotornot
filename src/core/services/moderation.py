"""Moderation service — used by web panel."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    AuditLog,
    Block,
    Comment,
    CommentStatus,
    Message,
    MessageStatus,
    Photo,
    PhotoStatus,
    Report,
    ReportStatus,
    User,
)


async def get_all_photos(
    session: AsyncSession, limit: int = 100, offset: int = 0
) -> list[Photo]:
    result = await session.execute(
        select(Photo)
        .order_by(Photo.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def hide_photo(session: AsyncSession, photo_id: int, moderator: str) -> bool:
    await session.execute(
        update(Photo).where(Photo.id == photo_id).values(status=PhotoStatus.hidden)
    )
    session.add(AuditLog(moderator=moderator, action="hide", target_type="photo", target_id=photo_id))
    await session.commit()
    return True


async def delete_photo(session: AsyncSession, photo_id: int, moderator: str) -> bool:
    await session.execute(
        update(Photo).where(Photo.id == photo_id).values(status=PhotoStatus.deleted)
    )
    session.add(AuditLog(moderator=moderator, action="delete", target_type="photo", target_id=photo_id))
    await session.commit()
    return True


async def get_all_users(
    session: AsyncSession, limit: int = 200, offset: int = 0
) -> list[User]:
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_all_comments(
    session: AsyncSession, limit: int = 200, offset: int = 0
) -> list[Comment]:
    result = await session.execute(
        select(Comment)
        .order_by(Comment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def ban_user(session: AsyncSession, user_id: int, moderator: str) -> bool:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_blocked = True
    audit = AuditLog(
        moderator=moderator,
        action="ban",
        target_type="user",
        target_id=user_id,
    )
    session.add(audit)
    await session.commit()
    return True


async def unban_user(session: AsyncSession, user_id: int, moderator: str) -> bool:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_blocked = False
    audit = AuditLog(
        moderator=moderator,
        action="unban",
        target_type="user",
        target_id=user_id,
    )
    session.add(audit)
    await session.commit()
    return True


async def hide_comment(session: AsyncSession, comment_id: int, moderator: str) -> bool:
    await session.execute(
        update(Comment)
        .where(Comment.id == comment_id)
        .values(status=CommentStatus.hidden)
    )
    audit = AuditLog(
        moderator=moderator,
        action="hide",
        target_type="comment",
        target_id=comment_id,
    )
    session.add(audit)
    await session.commit()
    return True


async def get_pending_reports(session: AsyncSession, limit: int = 50) -> list[Report]:
    result = await session.execute(
        select(Report)
        .where(Report.status == ReportStatus.pending)
        .order_by(Report.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_report(session: AsyncSession, report_id: int) -> Report | None:
    result = await session.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


async def get_report_target_preview(session: AsyncSession, report: Report) -> dict:
    """Return a dict with target info for display in the moderation card."""
    info: dict = {
        "type": report.target_type.value,
        "id": report.target_id,
        "content": None,
        "author_id": None,
        "photo_id": None,
    }
    if report.target_type.value == "photo":
        r = await session.execute(select(Photo).where(Photo.id == report.target_id))
        obj = r.scalar_one_or_none()
        if obj:
            info["content"] = obj.telegram_file_id
            info["author_id"] = obj.author_id
            info["status"] = obj.status.value
            info["photo_id"] = obj.id
    elif report.target_type.value == "comment":
        r = await session.execute(select(Comment).where(Comment.id == report.target_id))
        obj = r.scalar_one_or_none()
        if obj:
            info["content"] = obj.text
            info["author_id"] = obj.author_id
            info["status"] = obj.status.value
            info["photo_id"] = obj.photo_id
    elif report.target_type.value == "message":
        r = await session.execute(select(Message).where(Message.id == report.target_id))
        obj = r.scalar_one_or_none()
        if obj:
            info["content"] = obj.text
            info["author_id"] = obj.sender_id
            info["status"] = obj.status.value
    return info


async def apply_moderation_action(
    session: AsyncSession,
    report_id: int,
    action: str,
    moderator: str,
    note: str | None = None,
) -> bool:
    """
    action: hide | delete | ban | reject
    Returns True on success.
    """
    report = await get_report(session, report_id)
    if report is None:
        return False

    target_type = report.target_type.value
    target_id = report.target_id

    if action == "reject":
        # Just close the report, no content change
        pass

    elif action in ("hide", "delete"):
        new_status = PhotoStatus.hidden if action == "hide" else PhotoStatus.deleted

        if target_type == "photo":
            await session.execute(
                update(Photo)
                .where(Photo.id == target_id)
                .values(status=new_status)
            )
        elif target_type == "comment":
            cs = CommentStatus.hidden if action == "hide" else CommentStatus.deleted
            await session.execute(
                update(Comment)
                .where(Comment.id == target_id)
                .values(status=cs)
            )
        elif target_type == "message":
            ms = MessageStatus.hidden if action == "hide" else MessageStatus.deleted
            await session.execute(
                update(Message)
                .where(Message.id == target_id)
                .values(status=ms)
            )

    elif action == "ban":
        # Ban the author of the target
        author_id: int | None = None
        if target_type == "photo":
            r = await session.execute(select(Photo.author_id).where(Photo.id == target_id))
            author_id = r.scalar_one_or_none()
        elif target_type == "comment":
            r = await session.execute(select(Comment.author_id).where(Comment.id == target_id))
            author_id = r.scalar_one_or_none()
        elif target_type == "message":
            r = await session.execute(select(Message.sender_id).where(Message.id == target_id))
            author_id = r.scalar_one_or_none()

        if author_id:
            await session.execute(
                update(User).where(User.id == author_id).values(is_blocked=True)
            )

    # Mark report resolved / rejected
    new_report_status = ReportStatus.rejected if action == "reject" else ReportStatus.resolved
    await session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(status=new_report_status, resolved_at=datetime.now(timezone.utc))
    )

    # Write audit log
    audit = AuditLog(
        moderator=moderator,
        action=action,
        target_type=target_type,
        target_id=target_id,
        note=note,
    )
    session.add(audit)
    await session.commit()
    return True


async def upload_photo_for_user(
    session: AsyncSession,
    author_id: int,
    file_path: str,
    allow_comments: bool,
    moderator: str,
) -> Photo:
    """Upload a photo on behalf of a user from a local file (web panel)."""
    photo = Photo(
        author_id=author_id,
        telegram_file_id=None,
        file_path=file_path,
        allow_comments=allow_comments,
        status=PhotoStatus.active,
    )
    session.add(photo)
    await session.flush()
    audit = AuditLog(
        moderator=moderator,
        action="upload",
        target_type="photo",
        target_id=photo.id,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(photo)
    return photo


async def get_audit_log(session: AsyncSession, limit: int = 100) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
