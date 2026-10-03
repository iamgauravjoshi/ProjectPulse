"""Canonical project schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_canonical"
down_revision: str | None = "0001_vector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_projects_name_not_blank")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email = lower(email) AND length(trim(email)) > 0",
            name=op.f("ck_users_normalized_email"),
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0", name=op.f("ck_users_display_name_not_blank")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "milestones",
        sa.Column("status", sa.String(length=20), server_default="PLANNED", nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_milestones_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('PLANNED', 'AT_RISK', 'COMPLETED', 'CANCELLED')",
            name=op.f("ck_milestones_status_values"),
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_milestones_title_not_blank")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_milestones_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_milestones_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_milestones")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_milestones_project_id_id")),
    )
    op.create_index(op.f("ix_milestones_project_id"), "milestones", ["project_id"], unique=False)
    op.create_table(
        "project_members",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('PRODUCT_OWNER', 'TECH_LEAD', 'ARCHITECT', 'DEVELOPER', "
            "'QA', 'SECURITY', 'CLIENT', 'PROJECT_MANAGER')",
            name=op.f("ck_project_members_role_values"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_members_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_project_members_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_members")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_project_members_project_id_id")),
        sa.UniqueConstraint(
            "project_id", "user_id", name=op.f("uq_project_members_project_id_user_id")
        ),
    )
    op.create_index(
        op.f("ix_project_members_project_id"), "project_members", ["project_id"], unique=False
    )
    op.create_table(
        "requirements",
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("phase", sa.Integer(), server_default="1", nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_requirements_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name=op.f("ck_requirements_status_values"),
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_requirements_title_not_blank")),
        sa.CheckConstraint("phase > 0", name=op.f("ck_requirements_phase_positive")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_requirements_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_requirements_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirements")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_requirements_project_id_id")),
    )
    op.create_index(
        op.f("ix_requirements_project_id"), "requirements", ["project_id"], unique=False
    )
    op.create_table(
        "risks",
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="MEDIUM", nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name=op.f("ck_risks_severity_values"),
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_risks_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'MITIGATED', 'CLOSED')", name=op.f("ck_risks_status_values")
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_risks_title_not_blank")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_risks_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_risks_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risks")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_risks_project_id_id")),
    )
    op.create_index(op.f("ix_risks_project_id"), "risks", ["project_id"], unique=False)
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(action)) > 0", name=op.f("ck_audit_events_action_not_blank")
        ),
        sa.CheckConstraint(
            "length(trim(entity_type)) > 0", name=op.f("ck_audit_events_entity_type_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "actor_id"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_audit_events_project_id_actor_id_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_audit_events_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_audit_events_project_id_id")),
    )
    op.create_index(
        op.f("ix_audit_events_project_id"), "audit_events", ["project_id"], unique=False
    )
    op.create_table(
        "decisions",
        sa.Column(
            "decision_status", sa.String(length=30), server_default="DISCUSSION", nullable=False
        ),
        sa.Column("impact_area", sa.String(length=120), server_default="", nullable=False),
        sa.Column("made_by", sa.Uuid(), nullable=True),
        sa.Column("supersedes_decision_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision_status IN ('DISCUSSION', 'PROPOSAL', 'PROVISIONAL', 'REVIEW_REQUIRED', "
            "'CONFIRMED', 'SUPERSEDED', 'REJECTED')",
            name=op.f("ck_decisions_decision_status_values"),
        ),
        sa.CheckConstraint(
            "decision_status NOT IN ('CONFIRMED', 'SUPERSEDED') OR confirmed_at IS NOT NULL",
            name=op.f("ck_decisions_confirmed_timestamp"),
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_decisions_source_kind_values")
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_decisions_title_not_blank")),
        sa.CheckConstraint(
            "supersedes_decision_id IS NULL OR supersedes_decision_id <> id",
            name=op.f("ck_decisions_not_self"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_decisions_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id", "made_by"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_decisions_project_id_made_by_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "supersedes_decision_id"],
            ["decisions.project_id", "decisions.id"],
            name=op.f("fk_decisions_project_id_supersedes_decision_id_decisions"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_decisions_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decisions")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_decisions_project_id_id")),
    )
    op.create_index(op.f("ix_decisions_project_id"), "decisions", ["project_id"], unique=False)
    op.create_table(
        "dependencies",
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("blocked_milestone_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_dependencies_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'READY', 'BLOCKED')", name=op.f("ck_dependencies_status_values")
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_dependencies_title_not_blank")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_dependencies_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id", "blocked_milestone_id"],
            ["milestones.project_id", "milestones.id"],
            name=op.f("fk_dependencies_project_id_blocked_milestone_id_milestones"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "owner_id"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_dependencies_project_id_owner_id_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_dependencies_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dependencies")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_dependencies_project_id_id")),
    )
    op.create_index(
        op.f("ix_dependencies_project_id"), "dependencies", ["project_id"], unique=False
    )
    op.create_table(
        "open_questions",
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_open_questions_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'CLOSED')", name=op.f("ck_open_questions_status_values")
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0", name=op.f("ck_open_questions_title_not_blank")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_open_questions_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id", "owner_id"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_open_questions_project_id_owner_id_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_open_questions_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_open_questions")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_open_questions_project_id_id")),
    )
    op.create_index(
        op.f("ix_open_questions_project_id"), "open_questions", ["project_id"], unique=False
    )
    op.create_table(
        "commitments",
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("said_by", sa.Uuid(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("dependency_id", sa.Uuid(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("source_kind", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column("source_label", sa.String(), server_default="", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_kind IN ('MANUAL', 'SEED')", name=op.f("ck_commitments_source_kind_values")
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED')",
            name=op.f("ck_commitments_status_values"),
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_commitments_confidence_range"),
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_commitments_title_not_blank")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_commitments_version_positive")),
        sa.ForeignKeyConstraint(
            ["project_id", "dependency_id"],
            ["dependencies.project_id", "dependencies.id"],
            name=op.f("fk_commitments_project_id_dependency_id_dependencies"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "owner_id"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_commitments_project_id_owner_id_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "said_by"],
            ["project_members.project_id", "project_members.user_id"],
            name=op.f("fk_commitments_project_id_said_by_project_members"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_commitments_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_commitments")),
        sa.UniqueConstraint("project_id", "id", name=op.f("uq_commitments_project_id_id")),
    )
    op.create_index(op.f("ix_commitments_project_id"), "commitments", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commitments_project_id"), table_name="commitments")
    op.drop_table("commitments")
    op.drop_index(op.f("ix_open_questions_project_id"), table_name="open_questions")
    op.drop_table("open_questions")
    op.drop_index(op.f("ix_dependencies_project_id"), table_name="dependencies")
    op.drop_table("dependencies")
    op.drop_index(op.f("ix_decisions_project_id"), table_name="decisions")
    op.drop_table("decisions")
    op.drop_index(op.f("ix_audit_events_project_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_risks_project_id"), table_name="risks")
    op.drop_table("risks")
    op.drop_index(op.f("ix_requirements_project_id"), table_name="requirements")
    op.drop_table("requirements")
    op.drop_index(op.f("ix_project_members_project_id"), table_name="project_members")
    op.drop_table("project_members")
    op.drop_index(op.f("ix_milestones_project_id"), table_name="milestones")
    op.drop_table("milestones")
    op.drop_table("users")
    op.drop_table("projects")
