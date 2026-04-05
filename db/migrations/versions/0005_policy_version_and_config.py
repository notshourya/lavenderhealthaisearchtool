"""add policy version and stored config to clinic policy results

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clinic_policy_results",
        sa.Column("policy_version", sa.String(length=16), nullable=False, server_default="v1"),
    )
    op.add_column(
        "clinic_policy_results",
        sa.Column(
            "policy_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("clinic_policy_results", "policy_version", server_default=None)
    op.alter_column("clinic_policy_results", "policy_config", server_default=None)


def downgrade() -> None:
    op.drop_column("clinic_policy_results", "policy_config")
    op.drop_column("clinic_policy_results", "policy_version")
