"""Add file_path to photos, make telegram_file_id nullable

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file_path for locally-stored photos
    op.add_column(
        "photos",
        sa.Column("file_path", sa.String(512), nullable=True),
    )
    # Make telegram_file_id nullable (web-uploaded photos don't have it initially)
    op.alter_column("photos", "telegram_file_id", nullable=True)


def downgrade() -> None:
    op.alter_column("photos", "telegram_file_id", nullable=False)
    op.drop_column("photos", "file_path")
