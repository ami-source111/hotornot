"""User service — get or create users from Telegram data."""
from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Gender, User


async def get_or_create_user(session: AsyncSession, tg_user: TgUser) -> User:
    """Return existing user or create a new one. Does NOT set gender."""
    result = await session.execute(select(User).where(User.id == tg_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            gender=Gender.unknown,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def set_gender(session: AsyncSession, user_id: int, gender: Gender) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.gender = gender
    await session.commit()
    await session.refresh(user)
    return user


async def set_display_name(session: AsyncSession, user_id: int, display_name: str) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.display_name = display_name.strip()[:64]
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
