"""module title

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("title", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "title")
