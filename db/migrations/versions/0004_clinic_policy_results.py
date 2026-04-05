"""add clinic policy results table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinic_policy_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qualification_profile", sa.String(length=32), nullable=False),
        sa.Column("qualification_threshold", sa.Float(), nullable=False),
        sa.Column("is_qualified", sa.Boolean(), nullable=False),
        sa.Column("decision_reason", sa.String(length=100), nullable=False),
        sa.Column("insurer_fault_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clinic_fault_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shared_fault_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_insurer_reviewers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dominant_issue_category", sa.String(length=64), nullable=True),
        sa.Column("dominant_issue_category_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recent_insurer_fault_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recent_month_cluster_peak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_reviews_known", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("complaint_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("effective_insurer_signal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("base_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("insurer_signal_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("complaint_rate_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recency_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reviewer_uniqueness_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["city_run_id"], ["city_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_clinic_policy_results_run_profile_created",
        "clinic_policy_results",
        ["city_run_id", "qualification_profile", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_clinic_policy_results_run_profile_created", table_name="clinic_policy_results")
    op.drop_table("clinic_policy_results")
