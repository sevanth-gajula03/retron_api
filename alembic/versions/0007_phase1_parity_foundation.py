"""phase1 parity foundation

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("users", sa.Column("college", sa.String(), nullable=True))
    op.add_column("users", sa.Column("roll_number", sa.String(), nullable=True))
    op.add_column("users", sa.Column("institution_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("mentor_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("banned_from", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("permissions", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("guest_access_expiry", sa.DateTime(), nullable=True))
    op.create_foreign_key("users_institution_id_fkey", "users", "institutions", ["institution_id"], ["id"])
    op.create_foreign_key("users_mentor_id_fkey", "users", "users", ["mentor_id"], ["id"])

    op.add_column("courses", sa.Column("institution_id", sa.String(), nullable=True))
    op.add_column("courses", sa.Column("instructor_name", sa.String(), nullable=True))
    op.create_foreign_key("courses_institution_id_fkey", "courses", "institutions", ["institution_id"], ["id"])

    op.create_table(
        "course_co_instructors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("added_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_co_instructor_course_user"),
    )

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("inviter_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("invitee_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("invitee_email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "mentor_assignments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("college", sa.String(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("student_id", "mentor_id", name="uq_mentor_assignment_student_mentor"),
    )

    op.create_table(
        "mentor_course_assignments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("mentor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("assigned_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("institution_match", sa.Boolean(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("mentor_id", "course_id", name="uq_mentor_course_assignment_mentor_course"),
    )

    op.create_table(
        "course_progress",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("completed_modules", sa.JSON(), nullable=True),
        sa.Column("completed_sections", sa.JSON(), nullable=True),
        sa.Column("module_progress_percentage", sa.Integer(), nullable=False),
        sa.Column("section_progress_percentage", sa.Integer(), nullable=False),
        sa.Column("completed_module_count", sa.Integer(), nullable=False),
        sa.Column("completed_section_count", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(), nullable=True),
        sa.Column("last_accessed", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),
    )

    op.create_table(
        "assessment_access",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assessment_id", sa.String(), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("mentor_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("granted_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("granted_by_name", sa.String(), nullable=True),
        sa.Column("assessment_title", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("student_id", "assessment_id", name="uq_assessment_access_student_assessment"),
    )

    op.create_index("ix_invitations_course_status", "invitations", ["course_id", "status"], unique=False)
    op.create_index("ix_invitations_invitee_email", "invitations", ["invitee_email"], unique=False)
    op.create_index("ix_mentor_assignments_mentor_status", "mentor_assignments", ["mentor_id", "status"], unique=False)
    op.create_index("ix_mentor_assignments_student_status", "mentor_assignments", ["student_id", "status"], unique=False)
    op.create_index(
        "ix_mentor_course_assignments_mentor_status",
        "mentor_course_assignments",
        ["mentor_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_mentor_course_assignments_course_status",
        "mentor_course_assignments",
        ["course_id", "status"],
        unique=False,
    )
    op.create_index("ix_course_progress_user_course", "course_progress", ["user_id", "course_id"], unique=False)
    op.create_index(
        "ix_assessment_access_student_status",
        "assessment_access",
        ["student_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_access_assessment_status",
        "assessment_access",
        ["assessment_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_access_assessment_status", table_name="assessment_access")
    op.drop_index("ix_assessment_access_student_status", table_name="assessment_access")
    op.drop_index("ix_course_progress_user_course", table_name="course_progress")
    op.drop_index("ix_mentor_course_assignments_course_status", table_name="mentor_course_assignments")
    op.drop_index("ix_mentor_course_assignments_mentor_status", table_name="mentor_course_assignments")
    op.drop_index("ix_mentor_assignments_student_status", table_name="mentor_assignments")
    op.drop_index("ix_mentor_assignments_mentor_status", table_name="mentor_assignments")
    op.drop_index("ix_invitations_invitee_email", table_name="invitations")
    op.drop_index("ix_invitations_course_status", table_name="invitations")

    op.drop_table("assessment_access")
    op.drop_table("course_progress")
    op.drop_table("mentor_course_assignments")
    op.drop_table("mentor_assignments")
    op.drop_table("invitations")
    op.drop_table("course_co_instructors")

    op.drop_constraint("courses_institution_id_fkey", "courses", type_="foreignkey")
    op.drop_column("courses", "instructor_name")
    op.drop_column("courses", "institution_id")

    op.drop_constraint("users_mentor_id_fkey", "users", type_="foreignkey")
    op.drop_constraint("users_institution_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "guest_access_expiry")
    op.drop_column("users", "permissions")
    op.drop_column("users", "banned_from")
    op.drop_column("users", "mentor_id")
    op.drop_column("users", "institution_id")
    op.drop_column("users", "roll_number")
    op.drop_column("users", "college")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
