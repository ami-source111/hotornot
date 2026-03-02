"""
Seed script — creates fake users + uploads real photos to Telegram.

Usage:
    docker compose exec web python scripts/seed.py --chat-id YOUR_TELEGRAM_ID

Arguments:
    --chat-id   Your Telegram user ID (the bot will send photos there to get file_ids)
    --users     Number of fake users to create (default: 10)
    --photos    Number of photos per user (default: 1)

Example:
    docker compose exec web python scripts/seed.py --chat-id 26488750 --users 10
"""
from __future__ import annotations

import argparse
import asyncio
import io
import logging
import random
import sys
import urllib.request

from sqlalchemy import select

# Make sure src/ is in path
sys.path.insert(0, "/app")

from src.core.config import settings
from src.core.database import async_session_factory
from src.core.models import Gender, Photo, PhotoStatus, Rating, User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fake user data
# ---------------------------------------------------------------------------

FAKE_MALE_NAMES = [
    ("Алексей", "alex_seed"),
    ("Дмитрий", "dmitry_seed"),
    ("Иван", "ivan_seed"),
    ("Михаил", "misha_seed"),
    ("Сергей", "sergey_seed"),
    ("Андрей", "andrey_seed"),
    ("Никита", "nikita_seed"),
    ("Артём", "artem_seed"),
    ("Кирилл", "kirill_seed"),
    ("Павел", "pavel_seed"),
]

FAKE_FEMALE_NAMES = [
    ("Анна", "anna_seed"),
    ("Мария", "maria_seed"),
    ("Екатерина", "katya_seed"),
    ("Ольга", "olga_seed"),
    ("Наталья", "natasha_seed"),
    ("Юлия", "julia_seed"),
    ("Елена", "elena_seed"),
    ("Виктория", "vika_seed"),
    ("Дарья", "dasha_seed"),
    ("Татьяна", "tanya_seed"),
]

# Picsum photo sets: male portraits = 200-399, female = 400-599
# (just using different ID ranges for visual variety)
MALE_PHOTO_IDS = list(range(10, 110))
FEMALE_PHOTO_IDS = list(range(200, 300))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def upload_photo_to_telegram(bot_token: str, chat_id: int, photo_url: str) -> str | None:
    """Upload a photo URL to Telegram, return file_id."""
    import urllib.request
    import urllib.parse
    import json

    # Download image bytes
    try:
        with urllib.request.urlopen(photo_url, timeout=10) as resp:
            photo_bytes = resp.read()
    except Exception as e:
        log.warning(f"Failed to download {photo_url}: {e}")
        return None

    # Use multipart upload via requests-like approach with urllib
    boundary = "----PythonBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + photo_bytes + f"\r\n--{boundary}--\r\n".encode()

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                # Get largest photo size
                photos = result["result"]["photo"]
                file_id = photos[-1]["file_id"]
                return file_id
    except Exception as e:
        log.warning(f"Failed to send photo to Telegram: {e}")
    return None


async def get_or_create_fake_user(
    session, fake_id: int, first_name: str, username: str, gender: Gender
) -> User:
    result = await session.execute(select(User).where(User.id == fake_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=fake_id,
            username=username,
            first_name=first_name,
            gender=gender,
            is_blocked=False,
        )
        session.add(user)
        await session.flush()
        log.info(f"  Created user {first_name} (id={fake_id}, gender={gender.value})")
    else:
        log.info(f"  User {first_name} (id={fake_id}) already exists, skipping")
    return user


# ---------------------------------------------------------------------------
# Main seed logic
# ---------------------------------------------------------------------------

async def seed(chat_id: int, num_users: int, photos_per_user: int) -> None:
    bot_token = settings.bot_token

    # Split users evenly between genders
    half = num_users // 2
    male_count = half
    female_count = num_users - half

    male_pool = FAKE_MALE_NAMES[:male_count]
    female_pool = FAKE_FEMALE_NAMES[:female_count]

    # Fake user IDs start at 9_000_000_000 to avoid clashing with real users
    base_id = 9_000_000_000

    log.info(f"Seeding {male_count} male + {female_count} female users, "
             f"{photos_per_user} photo(s) each")
    log.info(f"Uploading photos via bot to chat_id={chat_id}")

    async with async_session_factory() as session:
        all_users: list[User] = []

        # --- Create male users ---
        for i, (name, uname) in enumerate(male_pool):
            user = await get_or_create_fake_user(
                session, base_id + i, name, uname, Gender.male
            )
            all_users.append(user)

        # --- Create female users ---
        for i, (name, uname) in enumerate(female_pool):
            user = await get_or_create_fake_user(
                session, base_id + 100 + i, name, uname, Gender.female
            )
            all_users.append(user)

        await session.commit()

        # --- Upload photos ---
        for user in all_users:
            # Check if user already has photos
            result = await session.execute(
                select(Photo).where(Photo.author_id == user.id).limit(1)
            )
            if result.scalar_one_or_none() is not None:
                log.info(f"  User {user.first_name} already has photos, skipping")
                continue

            for _ in range(photos_per_user):
                # Pick a random picsum image
                if user.gender == Gender.male:
                    pic_id = random.choice(MALE_PHOTO_IDS)
                else:
                    pic_id = random.choice(FEMALE_PHOTO_IDS)

                photo_url = f"https://picsum.photos/id/{pic_id}/600/800"
                log.info(f"  Uploading photo for {user.first_name} ({photo_url})")

                file_id = await upload_photo_to_telegram(bot_token, chat_id, photo_url)
                if file_id is None:
                    log.warning(f"  Skipped photo for {user.first_name}")
                    continue

                photo = Photo(
                    author_id=user.id,
                    telegram_file_id=file_id,
                    allow_comments=random.choice([True, True, False]),
                    status=PhotoStatus.active,
                )
                session.add(photo)
                await session.flush()
                log.info(f"  ✓ Photo saved (id={photo.id}, file_id={file_id[:30]}...)")

                # Add a few random ratings from other seed users
                await session.commit()
                await _add_seed_ratings(session, photo.id, user.id, all_users)

        await session.commit()

    log.info("✅ Seed complete!")


async def _add_seed_ratings(session, photo_id: int, author_id: int, all_users: list[User]) -> None:
    """Add 3–6 random ratings from other seed users."""
    raters = [u for u in all_users if u.id != author_id]
    random.shuffle(raters)
    for rater in raters[:random.randint(3, min(6, len(raters)))]:
        score = random.randint(5, 10)
        from src.core.models import Rating
        from sqlalchemy import select
        existing = await session.execute(
            select(Rating).where(Rating.rater_id == rater.id, Rating.photo_id == photo_id)
        )
        if existing.scalar_one_or_none() is None:
            session.add(Rating(rater_id=rater.id, photo_id=photo_id, score=score))
    await session.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed fake users and photos")
    parser.add_argument("--chat-id", type=int, required=True,
                        help="Your Telegram user ID (bot will send photos here)")
    parser.add_argument("--users", type=int, default=10,
                        help="Total number of fake users (default: 10)")
    parser.add_argument("--photos", type=int, default=1,
                        help="Photos per user (default: 1)")
    args = parser.parse_args()

    asyncio.run(seed(
        chat_id=args.chat_id,
        num_users=args.users,
        photos_per_user=args.photos,
    ))
