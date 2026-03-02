"""
SQLAlchemy models for RateApp.
All tables use status: active | hidden | deleted  (no is_deleted).
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PhotoStatus(str, enum.Enum):
    active = "active"
    hidden = "hidden"
    deleted = "deleted"


class CommentStatus(str, enum.Enum):
    active = "active"
    hidden = "hidden"
    deleted = "deleted"


class MessageStatus(str, enum.Enum):
    active = "active"
    hidden = "hidden"
    deleted = "deleted"


class DialogStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class ReportTarget(str, enum.Enum):
    photo = "photo"
    comment = "comment"
    message = "message"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    resolved = "resolved"
    rejected = "rejected"


class Gender(str, enum.Enum):
    male = "M"
    female = "F"
    unknown = "unknown"


class ReactionType(str, enum.Enum):
    heart = "heart"
    fire = "fire"
    heart_eyes = "heart_eyes"
    dislike = "dislike"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    """Telegram user_id — используется как PK напрямую."""

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Публичный ник, выбранный пользователем при регистрации."""
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=Gender.unknown,
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    photos: Mapped[list[Photo]] = relationship(
        "Photo", back_populates="author", foreign_keys="Photo.author_id"
    )
    ratings_given: Mapped[list[Rating]] = relationship(
        "Rating", back_populates="rater", foreign_keys="Rating.rater_id"
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment", back_populates="author", foreign_keys="Comment.author_id"
    )
    messages_sent: Mapped[list[Message]] = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )
    messages_received: Mapped[list[Message]] = relationship(
        "Message", back_populates="recipient", foreign_keys="Message.recipient_id"
    )
    reports_filed: Mapped[list[Report]] = relationship(
        "Report", back_populates="reporter", foreign_keys="Report.reporter_id"
    )
    blocked_users: Mapped[list[Block]] = relationship(
        "Block", back_populates="blocker", foreign_keys="Block.blocker_id"
    )
    dialogs_initiated: Mapped[list[Dialog]] = relationship(
        "Dialog", back_populates="initiator", foreign_keys="Dialog.initiator_id"
    )
    dialogs_received: Mapped[list[Dialog]] = relationship(
        "Dialog", back_populates="recipient", foreign_keys="Dialog.recipient_id"
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    """Telegram file_id (None for web-uploaded photos until first bot send)."""
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    """Local file path for photos uploaded via web panel (e.g. /app/media/uuid.jpg)."""
    allow_comments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[PhotoStatus] = mapped_column(
        Enum(PhotoStatus, name="photo_status_enum"),
        nullable=False,
        default=PhotoStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    author: Mapped[User] = relationship(
        "User", back_populates="photos", foreign_keys=[author_id]
    )
    ratings: Mapped[list[Rating]] = relationship(
        "Rating", back_populates="photo", cascade="all, delete-orphan"
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment", back_populates="photo", cascade="all, delete-orphan"
    )


class Rating(Base):
    """Реакция пользователя на фото (одна реакция на фото, можно заменить)."""

    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("rater_id", "photo_id", name="uq_rating_rater_photo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rater_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    reaction: Mapped[ReactionType] = mapped_column(
        Enum(ReactionType, name="reaction_type_enum"),
        nullable=False,
    )
    """Тип реакции: heart / fire / heart_eyes / dislike."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    rater: Mapped[User] = relationship(
        "User", back_populates="ratings_given", foreign_keys=[rater_id]
    )
    photo: Mapped[Photo] = relationship(
        "Photo", back_populates="ratings", foreign_keys=[photo_id]
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus, name="comment_status_enum"),
        nullable=False,
        default=CommentStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    author: Mapped[User] = relationship(
        "User", back_populates="comments", foreign_keys=[author_id]
    )
    photo: Mapped[Photo] = relationship(
        "Photo", back_populates="comments", foreign_keys=[photo_id]
    )
    dialog: Mapped[Dialog | None] = relationship(
        "Dialog", back_populates="comment", foreign_keys="Dialog.comment_id", uselist=False
    )


class Dialog(Base):
    """Анонимный диалог между двумя пользователями, начатый с ответа на комментарий."""

    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    """Комментарий, с которого начался диалог (может быть NULL если удалён)."""
    initiator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    """Автор фото, который первым ответил на комментарий."""
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    """Автор комментария."""
    status: Mapped[DialogStatus] = mapped_column(
        Enum(DialogStatus, name="dialog_status_enum"),
        nullable=False,
        default=DialogStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    comment: Mapped[Comment | None] = relationship(
        "Comment", back_populates="dialog", foreign_keys=[comment_id]
    )
    initiator: Mapped[User] = relationship(
        "User", back_populates="dialogs_initiated", foreign_keys=[initiator_id]
    )
    recipient: Mapped[User] = relationship(
        "User", back_populates="dialogs_received", foreign_keys=[recipient_id]
    )
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="dialog", cascade="all, delete-orphan"
    )


class Message(Base):
    """Anonymous proxied message inside a Dialog."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dialog_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=True
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    """Photo context (for reference, can be NULL)."""
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status_enum"),
        nullable=False,
        default=MessageStatus.active,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    dialog: Mapped[Dialog | None] = relationship(
        "Dialog", back_populates="messages", foreign_keys=[dialog_id]
    )
    sender: Mapped[User] = relationship(
        "User", back_populates="messages_sent", foreign_keys=[sender_id]
    )
    recipient: Mapped[User] = relationship(
        "User", back_populates="messages_received", foreign_keys=[recipient_id]
    )


class Report(Base):
    """User complaint against a photo, comment, or message."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[ReportTarget] = mapped_column(
        Enum(ReportTarget, name="report_target_enum"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    """ID of the reported photo / comment / message."""
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status_enum"),
        nullable=False,
        default=ReportStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    reporter: Mapped[User] = relationship(
        "User", back_populates="reports_filed", foreign_keys=[reporter_id]
    )


class Block(Base):
    """A user blocking another user (photo author)."""

    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blocker_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    blocked_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    blocker: Mapped[User] = relationship(
        "User", back_populates="blocked_users", foreign_keys=[blocker_id]
    )


class AuditLog(Base):
    """Immutable log of moderation actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    moderator: Mapped[str] = mapped_column(String(64), nullable=False)
    """Username of the web moderator who took the action."""
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    """hide | delete | ban | reject"""
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """photo | comment | message | user | report"""
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
