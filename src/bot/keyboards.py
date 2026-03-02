"""
Shared keyboard factories.

All InlineKeyboardMarkup objects used by bot handlers are defined here
so there is one canonical source to find/change any keyboard layout.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------------------------------------------------------------------
# Registration / onboarding
# ---------------------------------------------------------------------------

def age_verification_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Мне есть 18 лет, я принимаю условия", callback_data="age:confirm")
    builder.button(text="❌ Мне нет 18 лет", callback_data="age:decline")
    builder.adjust(1)
    return builder.as_markup()


def gender_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👦 Мужской", callback_data="gender:M")
    builder.button(text="👧 Женский", callback_data="gender:F")
    builder.adjust(2)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Feed / filter
# ---------------------------------------------------------------------------

def feed_filter_keyboard(current: str = "all") -> InlineKeyboardMarkup:
    labels = {"all": "Все", "M": "Парни", "F": "Девушки"}
    builder = InlineKeyboardBuilder()
    for key, label in labels.items():
        marker = "✅ " if key == current else ""
        builder.button(text=f"{marker}{label}", callback_data=f"filter:{key}")
    builder.adjust(3)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Photo feed — reaction and post-reaction keyboards
# ---------------------------------------------------------------------------

def reaction_keyboard(
    photo_id: int,
    allow_comments: bool,
    gender_filter: str = "all",
    author_name: str = "",
) -> InlineKeyboardMarkup:
    """
    Row 1: ❤️ 🔥 😍 👎 (reactions)
    Row 2: 💬 Комментировать | ➡️ Следующее
    Row 3: 👤 Автор
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❤️", callback_data=f"react:{photo_id}:heart:{gender_filter}")
    builder.button(text="🔥", callback_data=f"react:{photo_id}:fire:{gender_filter}")
    builder.button(text="😍", callback_data=f"react:{photo_id}:heart_eyes:{gender_filter}")
    builder.button(text="👎", callback_data=f"react:{photo_id}:dislike:{gender_filter}")
    if allow_comments:
        builder.button(text="💬 Комментировать", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее", callback_data=f"browse:next:{gender_filter}")
    name_label = author_name or "Профиль автора"
    builder.button(text=f"👤 {name_label}", callback_data=f"profile:photo:{photo_id}")
    builder.adjust(4, 2 if allow_comments else 1, 1)
    return builder.as_markup()


def post_reaction_keyboard(
    photo_id: int,
    allow_comments: bool,
    gender_filter: str = "all",
    author_name: str = "",
) -> InlineKeyboardMarkup:
    """Shown after reacting — no more reaction buttons."""
    builder = InlineKeyboardBuilder()
    if allow_comments:
        builder.button(text="💬 Комментировать", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее", callback_data=f"browse:next:{gender_filter}")
    name_label = author_name or "Профиль автора"
    builder.button(text=f"👤 {name_label}", callback_data=f"profile:photo:{photo_id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:photo:{photo_id}")
    builder.button(text="🔒 Заблокировать автора", callback_data=f"block:author:{photo_id}")
    builder.adjust(2 if allow_comments else 1, 1, 2)
    return builder.as_markup()


def author_profile_keyboard(has_next: bool) -> InlineKeyboardMarkup:
    """Navigation keyboard inside author's photo gallery."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в ленту", callback_data="profile:back")
    if has_next:
        builder.button(text="➡️ Следующее фото автора", callback_data="profile:next:go")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def post_comment_keyboard(photo_id: int) -> InlineKeyboardMarkup:
    """Shown after leaving a comment: write more / next photo / menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Написать ещё", callback_data=f"comments:add:{photo_id}")
    builder.button(text="➡️ Следующее фото", callback_data="browse:next:all")
    builder.button(text="🏠 Главное меню", callback_data="nav:menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def comment_notify_keyboard(
    comment_id: int, commenter_id: int, photo_id: int
) -> InlineKeyboardMarkup:
    """Sent to photo author when a new comment arrives."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="↩️ Ответить",
        callback_data=f"dialog:start:{comment_id}:{commenter_id}:{photo_id}",
    )
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:comment:{comment_id}")
    builder.adjust(2)
    return builder.as_markup()


def cancel_keyboard(
    text: str = "⬅️ Отмена",
    callback_data: str = "cancel:upload",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=callback_data)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Dialogs / messaging
# ---------------------------------------------------------------------------

def dialog_open_keyboard(dialog_id: int, other_id: int) -> InlineKeyboardMarkup:
    """Actions available when viewing a dialog."""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{dialog_id}:{other_id}")
    builder.button(text="🔴 Закрыть диалог", callback_data=f"dialog:close:{dialog_id}")
    builder.button(text="⬅️ К списку чатов", callback_data="menu:chats")
    builder.adjust(2, 1)
    return builder.as_markup()


def dialog_message_keyboard(
    dialog_id: int, sender_id: int, msg_id: int
) -> InlineKeyboardMarkup:
    """Sent as notification when the other party sends a message."""
    builder = InlineKeyboardBuilder()
    builder.button(text="↩️ Ответить", callback_data=f"dialog:reply:{dialog_id}:{sender_id}")
    builder.button(text="🚫 Пожаловаться", callback_data=f"report:message:{msg_id}")
    builder.button(text="🔴 Закрыть диалог", callback_data=f"dialog:close:{dialog_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_comments_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Разрешить комментарии", callback_data="upload:comments:yes")
    builder.button(text="🚫 Без комментариев", callback_data="upload:comments:no")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Global navigation
# ---------------------------------------------------------------------------

def nav_keyboard(gender_filter: str = "all") -> InlineKeyboardMarkup:
    """Compact nav row appended to many messages: В ленту | Главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📰 В ленту", callback_data=f"nav:feed:{gender_filter}")
    builder.button(text="🏠 Меню", callback_data="nav:menu")
    builder.adjust(2)
    return builder.as_markup()


def next_photo_keyboard(filter_val: str = "all") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующее фото", callback_data=f"browse:next:{filter_val}")
    builder.button(text="🔍 Сменить фильтр", callback_data="browse:filter")
    builder.adjust(1)
    return builder.as_markup()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Смотреть ленту", callback_data="menu:browse")
    builder.button(text="➕ Загрузить фото", callback_data="menu:upload")
    builder.button(text="📊 Мои реакции", callback_data="menu:stats")
    builder.button(text="💬 Переписки", callback_data="menu:chats")
    builder.button(text="🖼 Мои фото", callback_data="menu:photos")
    builder.adjust(2, 1, 2)
    return builder.as_markup()
