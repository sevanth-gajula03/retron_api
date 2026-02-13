"""password setup tokens

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_setup_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_password_setup_tokens_user_id", "password_setup_tokens", ["user_id"], unique=False)
    op.create_index("ix_password_setup_tokens_token_hash", "password_setup_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_password_setup_tokens_token_hash", table_name="password_setup_tokens")
    op.drop_index("ix_password_setup_tokens_user_id", table_name="password_setup_tokens")
    op.drop_table("password_setup_tokens")
