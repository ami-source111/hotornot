"""Add media_file_id to comments.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("media_file_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("comments", "media_file_id")
