"""audit logs

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("admin_email", sa.String(), nullable=True),
        sa.Column("target_user_email", sa.String(), nullable=True),
        sa.Column("old_role", sa.String(), nullable=True),
        sa.Column("new_role", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
