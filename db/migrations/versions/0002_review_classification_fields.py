"""add review classification fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-03

"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    faultparty = sa.Enum("insurer", "clinic", "shared", "unclear", "none", name="faultparty")
    issuecategory = sa.Enum(
        "claim_denial",
        "coverage_confusion",
        "reimbursement_delay",
        "authorization_issue",
        "billing_error",
        "other",
        name="issuecategory",
    )
    faultparty.create(op.get_bind(), checkfirst=True)
    issuecategory.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "reviews",
        sa.Column(
            "fault_party",
            faultparty,
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "issue_category",
            issuecategory,
            nullable=True,
        ),
    )
    op.add_column(
        "reviews",
        sa.Column("classification_confidence", sa.Float(), nullable=True),
    )

    op.alter_column("reviews", "fault_party", server_default=None)


def downgrade() -> None:
    op.drop_column("reviews", "classification_confidence")
    op.drop_column("reviews", "issue_category")
    op.drop_column("reviews", "fault_party")
    op.execute("DROP TYPE IF EXISTS issuecategory")
    op.execute("DROP TYPE IF EXISTS faultparty")
