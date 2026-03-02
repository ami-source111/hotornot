"""Block service — user blocking other users."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Block


async def block_user(
    session: AsyncSession, blocker_id: int, blocked_id: int
) -> Block | None:
    """Block a user. Returns None if already blocked."""
    existing = await session.execute(
        select(Block).where(
            Block.blocker_id == blocker_id, Block.blocked_id == blocked_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None
    block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
    session.add(block)
    await session.commit()
    await session.refresh(block)
    return block


async def is_blocked(
    session: AsyncSession, blocker_id: int, blocked_id: int
) -> bool:
    result = await session.execute(
        select(Block.id).where(
            Block.blocker_id == blocker_id, Block.blocked_id == blocked_id
        )
    )
    return result.scalar_one_or_none() is not None
