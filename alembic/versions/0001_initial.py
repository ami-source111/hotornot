"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    gender_enum = sa.Enum("M", "F", "unknown", name="gender_enum")
    photo_status_enum = sa.Enum("active", "hidden", "deleted", name="photo_status_enum")
    comment_status_enum = sa.Enum("active", "hidden", "deleted", name="comment_status_enum")
    message_status_enum = sa.Enum("active", "hidden", "deleted", name="message_status_enum")
    report_target_enum = sa.Enum("photo", "comment", "message", name="report_target_enum")
    report_status_enum = sa.Enum("pending", "resolved", "rejected", name="report_status_enum")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("gender", gender_enum, nullable=False, server_default="unknown"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- photos ---
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_file_id", sa.String(256), nullable=False),
        sa.Column("allow_comments", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", photo_status_enum, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_photos_author_id", "photos", ["author_id"])
    op.create_index("ix_photos_status", "photos", ["status"])

    # --- ratings ---
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rater_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rater_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rater_id", "photo_id", name="uq_rating_rater_photo"),
    )

    # --- comments ---
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", comment_status_enum, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_photo_id", "comments", ["photo_id"])

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_id", sa.Integer(), nullable=True),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", message_status_enum, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_recipient_id", "messages", ["recipient_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])

    # --- reports ---
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporter_id", sa.BigInteger(), nullable=False),
        sa.Column("target_type", report_target_enum, nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=True),
        sa.Column("status", report_status_enum, nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_target", "reports", ["target_type", "target_id"])

    # --- blocks ---
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("blocker_id", sa.BigInteger(), nullable=False),
        sa.Column("blocked_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("moderator", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("blocks")
    op.drop_table("reports")
    op.drop_table("messages")
    op.drop_table("comments")
    op.drop_table("ratings")
    op.drop_table("photos")
    op.drop_table("users")

    # drop enums
    for enum_name in (
        "gender_enum",
        "photo_status_enum",
        "comment_status_enum",
        "message_status_enum",
        "report_target_enum",
        "report_status_enum",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
