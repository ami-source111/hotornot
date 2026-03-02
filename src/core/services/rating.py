"""Reaction service — one reaction per user per photo, replaceable."""
from __future__ import annotations

from sqlalchemy import func as sqlfunc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import ContentStatus, Photo, Rating, ReactionType

REACTION_EMOJI = {
    ReactionType.heart: "❤️",
    ReactionType.fire: "🔥",
    ReactionType.heart_eyes: "😍",
    ReactionType.dislike: "👎",
}


async def get_user_reaction(
    session: AsyncSession, rater_id: int, photo_id: int
) -> ReactionType | None:
    result = await session.execute(
        select(Rating.reaction).where(
            Rating.rater_id == rater_id,
            Rating.photo_id == photo_id,
        )
    )
    return result.scalar_one_or_none()


async def set_reaction(
    session: AsyncSession,
    rater_id: int,
    photo_id: int,
    reaction: ReactionType,
) -> tuple[Rating, bool]:
    """
    Upsert reaction. Returns (rating, is_new).
    If user already reacted → replace reaction.
    """
    existing = await session.execute(
        select(Rating).where(
            Rating.rater_id == rater_id,
            Rating.photo_id == photo_id,
        )
    )
    rating = existing.scalar_one_or_none()
    if rating is not None:
        rating.reaction = reaction
        await session.commit()
        await session.refresh(rating)
        return rating, False
    else:
        rating = Rating(rater_id=rater_id, photo_id=photo_id, reaction=reaction)
        session.add(rating)
        await session.commit()
        await session.refresh(rating)
        return rating, True


async def get_photo_reactions(session: AsyncSession, photo_id: int) -> dict[str, int]:
    """Return count of each reaction type for a photo."""
    result = await session.execute(
        select(Rating.reaction, sqlfunc.count(Rating.id))
        .where(Rating.photo_id == photo_id)
        .group_by(Rating.reaction)
    )
    counts: dict[str, int] = {r.value: 0 for r in ReactionType}
    for reaction, count in result.all():
        counts[reaction.value] = count
    return counts


async def get_photo_avg(session: AsyncSession, photo_id: int) -> float | None:
    """Legacy compatibility — returns None (reactions replaced scores)."""
    return None


async def get_my_photos_reactions(
    session: AsyncSession, user_id: int
) -> list[dict]:
    """Return reaction stats for each of the user's active photos."""
    photos_result = await session.execute(
        select(Photo).where(
            Photo.author_id == user_id,
            Photo.status == ContentStatus.active,
        )
    )
    photos = list(photos_result.scalars().all())
    out = []
    for photo in photos:
        counts = await get_photo_reactions(session, photo.id)
        total = sum(counts.values())
        out.append({
            "photo_id": photo.id,
            "counts": counts,
            "total": total,
        })
    return out
