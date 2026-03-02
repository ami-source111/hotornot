"""Moderation service — used by the web panel only."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    AuditLog,
    Block,
    Comment,
    ContentStatus,
    Gender,
    Message,
    Photo,
    Report,
    ReportStatus,
    ReportTarget,
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
        update(Photo).where(Photo.id == photo_id).values(status=ContentStatus.hidden)
    )
    session.add(AuditLog(moderator=moderator, action="hide", target_type="photo", target_id=photo_id))
    await session.commit()
    return True


async def delete_photo(session: AsyncSession, photo_id: int, moderator: str) -> bool:
    await session.execute(
        update(Photo).where(Photo.id == photo_id).values(status=ContentStatus.deleted)
    )
    session.add(AuditLog(moderator=moderator, action="delete", target_type="photo", target_id=photo_id))
    await session.commit()
    return True


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_photos(
    session: AsyncSession, user_id: int, limit: int = 100
) -> list[Photo]:
    result = await session.execute(
        select(Photo)
        .where(Photo.author_id == user_id)
        .order_by(Photo.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


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
    session.add(AuditLog(moderator=moderator, action="ban", target_type="user", target_id=user_id))
    await session.commit()
    return True


async def unban_user(session: AsyncSession, user_id: int, moderator: str) -> bool:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_blocked = False
    session.add(AuditLog(moderator=moderator, action="unban", target_type="user", target_id=user_id))
    await session.commit()
    return True


async def hide_comment(session: AsyncSession, comment_id: int, moderator: str) -> bool:
    await session.execute(
        update(Comment)
        .where(Comment.id == comment_id)
        .values(status=ContentStatus.hidden)
    )
    session.add(AuditLog(moderator=moderator, action="hide", target_type="comment", target_id=comment_id))
    await session.commit()
    return True


async def get_pending_reports(session: AsyncSession, limit: int = 100) -> list[Report]:
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
    if report.target_type == ReportTarget.photo:
        r = await session.execute(select(Photo).where(Photo.id == report.target_id))
        obj = r.scalar_one_or_none()
        if obj:
            info["content"] = obj.telegram_file_id
            info["author_id"] = obj.author_id
            info["status"] = obj.status.value
            info["photo_id"] = obj.id
    elif report.target_type == ReportTarget.comment:
        r = await session.execute(select(Comment).where(Comment.id == report.target_id))
        obj = r.scalar_one_or_none()
        if obj:
            info["content"] = obj.text
            info["author_id"] = obj.author_id
            info["status"] = obj.status.value
            info["photo_id"] = obj.photo_id
    elif report.target_type == ReportTarget.message:
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
    Apply a moderation decision to a report.

    action: hide | delete | ban | reject
    Returns True on success.
    """
    report = await get_report(session, report_id)
    if report is None:
        return False

    target_type = report.target_type.value
    target_id = report.target_id

    if action in ("hide", "delete"):
        new_status = ContentStatus.hidden if action == "hide" else ContentStatus.deleted

        if report.target_type == ReportTarget.photo:
            await session.execute(
                update(Photo).where(Photo.id == target_id).values(status=new_status)
            )
        elif report.target_type == ReportTarget.comment:
            await session.execute(
                update(Comment).where(Comment.id == target_id).values(status=new_status)
            )
        elif report.target_type == ReportTarget.message:
            await session.execute(
                update(Message).where(Message.id == target_id).values(status=new_status)
            )

    elif action == "ban":
        # Ban the author of the reported content
        author_id: int | None = None
        if report.target_type == ReportTarget.photo:
            r = await session.execute(select(Photo.author_id).where(Photo.id == target_id))
            author_id = r.scalar_one_or_none()
        elif report.target_type == ReportTarget.comment:
            r = await session.execute(select(Comment.author_id).where(Comment.id == target_id))
            author_id = r.scalar_one_or_none()
        elif report.target_type == ReportTarget.message:
            r = await session.execute(select(Message.sender_id).where(Message.id == target_id))
            author_id = r.scalar_one_or_none()

        if author_id:
            await session.execute(
                update(User).where(User.id == author_id).values(is_blocked=True)
            )

    # action == "reject" → just close the report without touching content

    new_report_status = ReportStatus.rejected if action == "reject" else ReportStatus.resolved
    await session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(status=new_report_status, resolved_at=datetime.now(timezone.utc))
    )

    session.add(AuditLog(
        moderator=moderator,
        action=action,
        target_type=target_type,
        target_id=target_id,
        note=note,
    ))
    await session.commit()
    return True


async def upload_photo_for_user(
    session: AsyncSession,
    author_id: int,
    file_path: str,
    allow_comments: bool,
    moderator: str,
) -> Photo:
    """Create a Photo record for a web-uploaded file. file_path is the filename only."""
    photo = Photo(
        author_id=author_id,
        telegram_file_id=None,
        file_path=file_path,
        allow_comments=allow_comments,
        status=ContentStatus.active,
    )
    session.add(photo)
    await session.flush()
    session.add(AuditLog(moderator=moderator, action="upload", target_type="photo", target_id=photo.id))
    await session.commit()
    await session.refresh(photo)
    return photo


async def hard_delete_user(session: AsyncSession, user_id: int, moderator: str) -> bool:
    """Permanently delete a user and all their data (CASCADE). Use for fake/seed accounts."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return False
    await session.delete(user)
    session.add(AuditLog(
        moderator=moderator,
        action="hard_delete",
        target_type="user",
        target_id=user_id,
    ))
    await session.commit()
    return True


def generate_fake_user_id() -> int:
    """Return a random ID clearly outside the real Telegram range (< 9 billion)."""
    return random.randint(9_000_000_000, 9_999_999_999)


async def create_fake_user(
    session: AsyncSession,
    user_id: int,
    display_name: str,
    first_name: str,
    gender: str,
    moderator: str,
) -> User:
    """Create a synthetic user for testing/seeding via the web panel."""
    gender_enum = (
        Gender.male if gender == "M"
        else (Gender.female if gender == "F" else Gender.unknown)
    )
    user = User(
        id=user_id,
        first_name=first_name or display_name,
        display_name=display_name,
        gender=gender_enum,
        is_blocked=False,
    )
    session.add(user)
    await session.flush()
    session.add(AuditLog(
        moderator=moderator,
        action="create_fake_user",
        target_type="user",
        target_id=user_id,
    ))
    await session.commit()
    await session.refresh(user)
    return user


async def get_audit_log(session: AsyncSession, limit: int = 200) -> list[AuditLog]:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
