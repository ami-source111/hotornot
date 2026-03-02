"""Shared keyboards and callback data helpers."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# --- Age verification ---

def age_verification_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Мне есть 18 лет, я принимаю условия", callback_data="age:confirm")
    builder.button(text="❌ Мне нет 18 лет", callback_data="age:decline")
    builder.adjust(1)
    return builder.as_markup()


# --- Gender selection ---

def gender_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👦 Мужской", callback_data="gender:M")
    builder.button(text="👧 Женский", callback_data="gender:F")
    builder.adjust(2)
    return builder.as_markup()


# --- Feed filter ---

def feed_filter_keyboard(current: str = "all") -> InlineKeyboardMarkup:
    labels = {
        "all": "Все",
        "M": "Парни",
        "F": "Девушки",
    }
    builder = InlineKeyboardBuilder()
    for key, label in labels.items():
        marker = "✅ " if key == current else ""
        builder.button(text=f"{marker}{label}", callback_data=f"filter:{key}")
    builder.adjust(3)
    return builder.as_markup()


# --- Reaction keyboard (under new photo) ---

def reaction_keyboard(photo_id: int, allow_comments: bool, gender_filter: str = "all", author_name: str = "") -> InlineKeyboardMarkup:
    """
    Row 1: ❤️ 🔥 😍 👎 (reactions)
    Row 2: 💬 Комментировать | ➡️ Следующее
    Row 3: 👤 Автор (if name provided)
    """
    builder = InlineKeyboardBuilder()
    # Row 1 — reactions
    builder.button(text="❤️", callback_data=f"react:{photo_id}:heart:{gender_filter}")
    builder.button(text="🔥", callback_data=f"react:{photo_id}:fire:{gender_filter}")
    builder.button(text="😍", callback_data=f"react:{photo_id}:heart_eyes:{gender_filter}")
    builder.button(text="👎", callback_data=f"react:{photo_id}:dislike:{gender_filter}")
    # Row 2 — actions
    if allow_comments:
        builder.button(text="💬 Комментировать", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее", callback_data=f"browse:next:{gender_filter}")
    # Row 3 — author profile
    name_label = author_name or "Профиль автора"
    builder.button(text=f"👤 {name_label}", callback_data=f"profile:photo:{photo_id}")
    # Adjust rows: 4 | 2 (or 1 if no comments) | 1
    if allow_comments:
        builder.adjust(4, 2, 1)
    else:
        builder.adjust(4, 1, 1)
    return builder.as_markup()


# --- Post-reaction keyboard (after user reacted) ---

def post_reaction_keyboard(photo_id: int, allow_comments: bool, gender_filter: str = "all", author_name: str = "") -> InlineKeyboardMarkup:
    """Shown after reacting — no more reaction buttons."""
    builder = InlineKeyboardBuilder()
    if allow_comments:
        builder.button(text="💬 Комментировать", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее", callback_data=f"browse:next:{gender_filter}")
    name_label = author_name or "Профиль автора"
    builder.button(text=f"👤 {name_label}", callback_data=f"profile:photo:{photo_id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:photo:{photo_id}")
    builder.button(text="🔒 Заблокировать автора", callback_data=f"block:author:{photo_id}")
    if allow_comments:
        builder.adjust(2, 1, 2)
    else:
        builder.adjust(1, 1, 2)
    return builder.as_markup()


# --- allow_comments toggle ---

def upload_comments_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Разрешить комментарии", callback_data="upload:comments:yes")
    builder.button(text="🚫 Без комментариев", callback_data="upload:comments:no")
    builder.adjust(1)
    return builder.as_markup()


# --- Cancel / back button ---

def cancel_keyboard(text: str = "⬅️ Отмена") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data="cancel:upload")
    return builder.as_markup()


# --- Next photo button ---

def next_photo_keyboard(filter_val: str = "all") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующее фото", callback_data=f"browse:next:{filter_val}")
    builder.button(text="🔍 Сменить фильтр", callback_data="browse:filter")
    builder.adjust(1)
    return builder.as_markup()


# --- Global navigation bar (appears at bottom of many messages) ---

def nav_keyboard(gender_filter: str = "all") -> InlineKeyboardMarkup:
    """Compact nav row: В ленту | Главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📰 В ленту", callback_data=f"nav:feed:{gender_filter}")
    builder.button(text="🏠 Меню", callback_data="nav:menu")
    builder.adjust(2)
    return builder.as_markup()


# --- Main menu keyboard ---

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Смотреть ленту", callback_data="menu:browse")
    builder.button(text="➕ Загрузить фото", callback_data="menu:upload")
    builder.button(text="📊 Мои реакции", callback_data="menu:stats")
    builder.button(text="💬 Переписки", callback_data="menu:chats")
    builder.button(text="🖼 Мои фото", callback_data="menu:photos")
    builder.adjust(2, 1, 2)
    return builder.as_markup()
