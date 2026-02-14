"""module quiz data + attempts

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("quiz_data", sa.JSON(), nullable=True))

    op.create_table(
        "module_quiz_attempts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("module_id", sa.String(), sa.ForeignKey("modules.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_module_quiz_attempts_module_user",
        "module_quiz_attempts",
        ["module_id", "user_id"],
        unique=False,
    )
    op.create_index(
        "ix_module_quiz_attempts_user_submitted",
        "module_quiz_attempts",
        ["user_id", "submitted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_module_quiz_attempts_user_submitted", table_name="module_quiz_attempts")
    op.drop_index("ix_module_quiz_attempts_module_user", table_name="module_quiz_attempts")
    op.drop_table("module_quiz_attempts")
    op.drop_column("modules", "quiz_data")
