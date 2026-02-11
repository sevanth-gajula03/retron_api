"""subsections

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_sections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("section_id", sa.String(), sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objectives", sa.JSON(), nullable=True),
        sa.Column("duration", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.add_column("modules", sa.Column("sub_section_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "modules_sub_section_id_fkey",
        "modules",
        "sub_sections",
        ["sub_section_id"],
        ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("modules_sub_section_id_fkey", "modules", type_="foreignkey")
    op.drop_column("modules", "sub_section_id")
    op.drop_table("sub_sections")
