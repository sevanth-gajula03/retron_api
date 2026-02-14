"""module quiz time limit

Revision ID: 0012
Revises: 0011
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("time_limit_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "time_limit_seconds")
