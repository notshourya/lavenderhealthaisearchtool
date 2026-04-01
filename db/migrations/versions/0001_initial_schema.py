"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'city_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='cityrunstatus'), nullable=False),
        sa.Column('triggered_by', sa.Enum('cli', 'dashboard', 'scheduler', name='triggeredby'), nullable=False),
        sa.Column('max_reviews', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_clinics_found', sa.Integer(), nullable=False),
        sa.Column('total_qualified', sa.Integer(), nullable=False),
        sa.Column('total_enriched', sa.Integer(), nullable=False),
        sa.Column('total_drafted', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'clinics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('city_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('zip', sa.String(10), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('google_maps_url', sa.String(1000), nullable=False),
        sa.Column('place_id', sa.String(255), nullable=False),
        sa.Column('overall_rating', sa.Float(), nullable=True),
        sa.Column('total_reviews', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('scraped', 'filtered_out', 'qualified', 'enriched', 'drafted', name='clinicstatus'), nullable=False),
        sa.ForeignKeyConstraint(['city_run_id'], ['city_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('place_id', name='uq_clinic_place_id'),
    )
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('insurance_flag', sa.Boolean(), nullable=False),
        sa.Column('flag_reason', sa.Enum('keyword', 'llm', 'both', name='flagreason'), nullable=True),
        sa.Column('keyword_matches', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llm_reasoning', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('found_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'email_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('subject_variants', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('draft', 'approved', 'sent', name='draftstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('exported_at', sa.DateTime(), nullable=True),
        sa.Column('export_format', sa.Enum('html', 'pdf', name='exportformat'), nullable=True),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('email_drafts')
    op.drop_table('contacts')
    op.drop_table('reviews')
    op.drop_table('clinics')
    op.drop_table('city_runs')
    op.execute("DROP TYPE IF EXISTS exportformat")
    op.execute("DROP TYPE IF EXISTS draftstatus")
    op.execute("DROP TYPE IF EXISTS flagreason")
    op.execute("DROP TYPE IF EXISTS clinicstatus")
    op.execute("DROP TYPE IF EXISTS triggeredby")
    op.execute("DROP TYPE IF EXISTS cityrunstatus")
