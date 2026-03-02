"""reactions, dialogs, display_name

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add display_name to users
    op.add_column(
        "users",
        sa.Column("display_name", sa.String(64), nullable=True),
    )

    # 2. Create reaction_type enum and dialog_status enum
    op.execute("CREATE TYPE reaction_type_enum AS ENUM ('heart', 'fire', 'heart_eyes', 'dislike')")
    op.execute("CREATE TYPE dialog_status_enum AS ENUM ('active', 'closed')")

    # 3. Modify ratings table: drop score, add reaction
    op.drop_column("ratings", "score")
    op.add_column(
        "ratings",
        sa.Column(
            "reaction",
            sa.Enum("heart", "fire", "heart_eyes", "dislike", name="reaction_type_enum", create_type=False),
            nullable=False,
            server_default="heart",
        ),
    )
    # Remove server_default after adding
    op.alter_column("ratings", "reaction", server_default=None)

    # 4. Create dialogs table
    op.create_table(
        "dialogs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("comments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("initiator_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "closed", name="dialog_status_enum", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_dialogs_initiator", "dialogs", ["initiator_id"])
    op.create_index("ix_dialogs_recipient", "dialogs", ["recipient_id"])

    # 5. Add dialog_id to messages (drop old comment_id approach for dialog context)
    op.add_column(
        "messages",
        sa.Column("dialog_id", sa.Integer(), sa.ForeignKey("dialogs.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_messages_dialog_id", "messages", ["dialog_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_dialog_id", "messages")
    op.drop_column("messages", "dialog_id")
    op.drop_index("ix_dialogs_recipient", "dialogs")
    op.drop_index("ix_dialogs_initiator", "dialogs")
    op.drop_table("dialogs")
    op.drop_column("ratings", "reaction")
    op.add_column("ratings", sa.Column("score", sa.SmallInteger(), nullable=False, server_default="5"))
    op.alter_column("ratings", "score", server_default=None)
    op.execute("DROP TYPE reaction_type_enum")
    op.execute("DROP TYPE dialog_status_enum")
    op.drop_column("users", "display_name")
