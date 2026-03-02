"""Comment service."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Comment, CommentStatus, Photo, PhotoStatus


async def add_comment(
    session: AsyncSession,
    author_id: int,
    photo_id: int,
    text: str,
    media_file_id: str | None = None,
) -> Comment | None:
    """Add a comment. Returns None if photo doesn't allow comments or not active."""
    result = await session.execute(
        select(Photo).where(Photo.id == photo_id, Photo.status == PhotoStatus.active)
    )
    photo = result.scalar_one_or_none()
    if photo is None or not photo.allow_comments:
        return None

    comment = Comment(
        author_id=author_id,
        photo_id=photo_id,
        text=text,
        media_file_id=media_file_id,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


async def get_active_comments(session: AsyncSession, photo_id: int) -> list[Comment]:
    result = await session.execute(
        select(Comment)
        .where(Comment.photo_id == photo_id, Comment.status == CommentStatus.active)
        .order_by(Comment.created_at.asc())
    )
    return list(result.scalars().all())


async def get_comment(session: AsyncSession, comment_id: int) -> Comment | None:
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    return result.scalar_one_or_none()
