"""Shared keyboards and callback data helpers."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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


# --- Rating 1–10 ---

def rating_keyboard(photo_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for score in range(1, 11):
        builder.button(text=str(score), callback_data=f"rate:{photo_id}:{score}")
    builder.adjust(5)
    return builder.as_markup()


# --- allow_comments toggle ---

def upload_comments_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Разрешить комментарии", callback_data="upload:comments:yes")
    builder.button(text="🚫 Без комментариев", callback_data="upload:comments:no")
    builder.adjust(1)
    return builder.as_markup()


# --- Next photo button ---

def next_photo_keyboard(filter_val: str = "all") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующее фото", callback_data=f"browse:next:{filter_val}")
    builder.button(text="🔍 Сменить фильтр", callback_data="browse:filter")
    builder.adjust(1)
    return builder.as_markup()
