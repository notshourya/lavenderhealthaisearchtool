"""add review signal fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-05

"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column("llm_severity_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reviews",
        sa.Column("explicit_insurance_mention", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reviews", "explicit_insurance_mention")
    op.drop_column("reviews", "llm_severity_score")
