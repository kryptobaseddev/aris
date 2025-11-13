"""Add quality validation and metrics tables

Revision ID: 002_add_quality_validation
Revises: 001_initial_schema
Create Date: 2025-11-12 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_quality_validation'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create quality validation tables."""

    # Create source_credibility table
    op.create_table(
        'source_credibility',
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('domain', sa.String(length=500), nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('credibility_score', sa.Float(), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=True),
        sa.Column('verification_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_verified', sa.DateTime(), nullable=True),
        sa.Column('times_cited', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('source_id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index(op.f('ix_source_credibility_domain'), 'source_credibility', ['domain'])
    op.create_index(op.f('ix_source_credibility_tier'), 'source_credibility', ['tier'])

    # Create quality_metrics table
    op.create_table(
        'quality_metrics',
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('query', sa.String(length=2000), nullable=False),
        sa.Column('total_sources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('distinct_sources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hops_executed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),

        # Pre-execution report (JSON)
        sa.Column('pre_execution_report', sa.JSON(), nullable=True),

        # Post-execution report (JSON)
        sa.Column('post_execution_report', sa.JSON(), nullable=True),

        # Confidence breakdown (JSON)
        sa.Column('confidence_breakdown', sa.JSON(), nullable=True),

        # Overall assessment
        sa.Column('overall_quality_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('validation_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('gate_level_used', sa.String(length=20), nullable=False, server_default='standard'),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
    )
    op.create_index(op.f('ix_quality_metrics_validation_passed'), 'quality_metrics', ['validation_passed'])
    op.create_index(op.f('ix_quality_metrics_gate_level'), 'quality_metrics', ['gate_level_used'])
    op.create_index(op.f('ix_quality_metrics_quality_score'), 'quality_metrics', ['overall_quality_score'])

    # Create validation_rule_history table for tracking rule changes
    op.create_table(
        'validation_rule_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('rule_name', sa.String(length=200), nullable=False),
        sa.Column('metric_name', sa.String(length=200), nullable=False),
        sa.Column('operator', sa.String(length=20), nullable=False),
        sa.Column('threshold', sa.String(length=500), nullable=True),
        sa.Column('actual_value', sa.String(length=500), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('gate_level', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['quality_metrics.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_validation_rule_history_session'), 'validation_rule_history', ['session_id'])
    op.create_index(op.f('ix_validation_rule_history_passed'), 'validation_rule_history', ['passed'])

    # Create contradiction_detection table
    op.create_table(
        'contradiction_detection',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('finding_1', sa.Text(), nullable=False),
        sa.Column('finding_2', sa.Text(), nullable=False),
        sa.Column('conflict_score', sa.Float(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('resolution_suggestion', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['quality_metrics.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contradiction_session'), 'contradiction_detection', ['session_id'])
    op.create_index(op.f('ix_contradiction_severity'), 'contradiction_detection', ['severity'])


def downgrade() -> None:
    """Drop quality validation tables."""

    # Drop indexes
    op.drop_index(op.f('ix_contradiction_severity'), table_name='contradiction_detection')
    op.drop_index(op.f('ix_contradiction_session'), table_name='contradiction_detection')

    op.drop_index(op.f('ix_validation_rule_history_passed'), table_name='validation_rule_history')
    op.drop_index(op.f('ix_validation_rule_history_session'), table_name='validation_rule_history')

    op.drop_index(op.f('ix_quality_metrics_quality_score'), table_name='quality_metrics')
    op.drop_index(op.f('ix_quality_metrics_gate_level'), table_name='quality_metrics')
    op.drop_index(op.f('ix_quality_metrics_validation_passed'), table_name='quality_metrics')

    op.drop_index(op.f('ix_source_credibility_tier'), table_name='source_credibility')
    op.drop_index(op.f('ix_source_credibility_domain'), table_name='source_credibility')

    # Drop tables
    op.drop_table('contradiction_detection')
    op.drop_table('validation_rule_history')
    op.drop_table('quality_metrics')
    op.drop_table('source_credibility')
