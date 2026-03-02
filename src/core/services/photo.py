"""Photo service — upload and feed browsing."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Block, Gender, Photo, PhotoStatus, Rating, User


async def upload_photo(
    session: AsyncSession,
    author_id: int,
    telegram_file_id: str,
    allow_comments: bool = True,
) -> Photo:
    photo = Photo(
        author_id=author_id,
        telegram_file_id=telegram_file_id,
        allow_comments=allow_comments,
        status=PhotoStatus.active,
    )
    session.add(photo)
    await session.commit()
    await session.refresh(photo)
    return photo


async def get_next_photo(
    session: AsyncSession,
    viewer_id: int,
    gender_filter: str = "all",
) -> Photo | None:
    """
    Return a random active photo that:
    - is not by the viewer themselves
    - author is not blocked by viewer (or vice versa)
    - viewer has NOT yet rated
    - matches gender filter (M / F / all)
    """
    # subquery: photos already rated by viewer
    rated_sub = select(Rating.photo_id).where(Rating.rater_id == viewer_id).scalar_subquery()

    # subquery: blocked users (both directions)
    blocked_sub = (
        select(Block.blocked_id)
        .where(Block.blocker_id == viewer_id)
        .union(select(Block.blocker_id).where(Block.blocked_id == viewer_id))
        .scalar_subquery()
    )

    stmt = (
        select(Photo)
        .join(User, Photo.author_id == User.id)
        .where(
            Photo.status == PhotoStatus.active,
            Photo.author_id != viewer_id,
            Photo.id.not_in(rated_sub),
            Photo.author_id.not_in(blocked_sub),
            User.is_blocked == False,  # noqa: E712
        )
    )

    if gender_filter == "M":
        stmt = stmt.where(User.gender == Gender.male)
    elif gender_filter == "F":
        stmt = stmt.where(User.gender == Gender.female)

    # Random pick via ORDER BY RANDOM() LIMIT 1
    stmt = stmt.order_by(func.random()).limit(1)

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_photo(session: AsyncSession, photo_id: int) -> Photo | None:
    result = await session.execute(select(Photo).where(Photo.id == photo_id))
    return result.scalar_one_or_none()
