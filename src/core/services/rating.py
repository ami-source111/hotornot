"""Rating service — one rating per user per photo (no updates)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Rating


async def has_rated(session: AsyncSession, rater_id: int, photo_id: int) -> bool:
    result = await session.execute(
        select(Rating.id).where(
            Rating.rater_id == rater_id,
            Rating.photo_id == photo_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def create_rating(
    session: AsyncSession, rater_id: int, photo_id: int, score: int
) -> Rating | None:
    """Create a new rating. Returns None if rating already exists."""
    if await has_rated(session, rater_id, photo_id):
        return None
    if not (1 <= score <= 10):
        raise ValueError(f"Score must be 1–10, got {score}")
    rating = Rating(rater_id=rater_id, photo_id=photo_id, score=score)
    session.add(rating)
    await session.commit()
    await session.refresh(rating)
    return rating


async def get_photo_avg(session: AsyncSession, photo_id: int) -> float | None:
    from sqlalchemy import func as sqlfunc
    result = await session.execute(
        select(sqlfunc.avg(Rating.score)).where(Rating.photo_id == photo_id)
    )
    val = result.scalar_one_or_none()
    return float(val) if val is not None else None
