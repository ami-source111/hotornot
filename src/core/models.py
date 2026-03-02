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
    SmallInteger,
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


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    """Telegram user_id — используется как PK напрямую."""

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender_enum"), nullable=False, default=Gender.unknown
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


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_file_id: Mapped[str] = mapped_column(String(256), nullable=False)
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
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    """Score 1–10."""
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


class Message(Base):
    """Anonymous proxied message in a dialog initiated from a photo comment."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    """Photo that started this dialog thread (can be NULL if photo deleted)."""
    comment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    """Original comment that started the dialog (first message only)."""
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
