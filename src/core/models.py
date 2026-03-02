"""
SQLAlchemy models for RateApp.

Status convention
-----------------
User-generated content (photos, comments, messages) shares a single
`ContentStatus` enum with three states:
  active  — visible to users
  hidden  — soft-hidden by moderators (not shown, but recoverable)
  deleted — soft-deleted (not shown, treated as gone)

Using one Python enum keeps the codebase DRY while PostgreSQL still
stores each column in its own typed enum (photo_status_enum, etc.) so
existing DB data is untouched.
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


class ContentStatus(str, enum.Enum):
    """Shared lifecycle status for photos, comments, and messages."""

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
    """Telegram user_id used as primary key directly."""

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Public nickname chosen by the user during registration."""
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
    """
    Filename of the locally stored file (e.g. 'abc123.jpg').
    Reconstruct the full path with: settings.media_dir / photo.file_path
    """
    allow_comments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="photo_status_enum"),
        nullable=False,
        default=ContentStatus.active,
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
    """One reaction per user per photo; can be replaced by a new reaction."""

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
    """Reaction type: heart / fire / heart_eyes / dislike."""
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
    """Comment text; set to '📷' for photo-only comments."""
    media_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    """Telegram file_id for a photo attached to the comment (optional)."""
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="comment_status_enum"),
        nullable=False,
        default=ContentStatus.active,
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
    """Anonymous conversation started when a photo author replies to a comment."""

    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    """The comment that started this dialog (NULL if the comment was deleted)."""
    initiator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    """Photo author who first replied to the comment."""
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    """Author of the original comment."""
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
    """Photo that the dialog is about (for context; may be NULL)."""
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="message_status_enum"),
        nullable=False,
        default=ContentStatus.active,
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
    """A user blocking another user (hides that user's photos from the feed)."""

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
    """Immutable record of every moderation action taken via the web panel."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    moderator: Mapped[str] = mapped_column(String(64), nullable=False)
    """Username of the web moderator who performed the action."""
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    """hide | delete | ban | unban | reject | upload | create_fake_user | hard_delete"""
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    """photo | comment | message | user | report"""
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    """ID of the affected entity. BigInteger to support Telegram user IDs."""
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
