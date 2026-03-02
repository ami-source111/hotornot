"""Refactor: BigInteger audit target_id + relative photo file paths.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-03

Changes:
  1. audit_logs.target_id: INTEGER → BIGINT
     Telegram user IDs can exceed 2^31; BigInteger is required to store them safely.

  2. photos.file_path: strip the '/app/media/' prefix from any existing rows
     so that file_path stores only the filename (e.g. 'abc123.jpg') rather
     than an absolute container path.  New uploads already write only the
     filename; this migration aligns historical rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Widen audit_logs.target_id to BIGINT.
    op.alter_column(
        "audit_logs",
        "target_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    # 2. Strip the '/app/media/' prefix from photos.file_path where present.
    op.execute(
        "UPDATE photos "
        "SET file_path = REPLACE(file_path, '/app/media/', '') "
        "WHERE file_path LIKE '/app/media/%'"
    )


def downgrade() -> None:
    # Re-add the prefix for any rows that look like plain filenames.
    # NOTE: This is a best-effort reversal; rows that never had the prefix
    # will be left unchanged.
    op.execute(
        "UPDATE photos "
        "SET file_path = '/app/media/' || file_path "
        "WHERE file_path NOT LIKE '/app/media/%' AND file_path IS NOT NULL"
    )

    # Narrow target_id back to INTEGER (may fail if stored values exceed 2^31-1).
    op.alter_column(
        "audit_logs",
        "target_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
