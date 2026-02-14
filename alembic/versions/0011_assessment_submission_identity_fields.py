"""add assessment submission identity fields

Revision ID: 0011
Revises: 0010
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessment_submissions", sa.Column("student_email", sa.String(), nullable=True))
    op.add_column("assessment_submissions", sa.Column("student_name", sa.String(), nullable=True))
    op.add_column("assessment_submissions", sa.Column("submitted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_submissions", "submitted_at")
    op.drop_column("assessment_submissions", "student_name")
    op.drop_column("assessment_submissions", "student_email")
