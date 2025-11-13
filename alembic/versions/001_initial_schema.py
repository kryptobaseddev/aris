"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-12 13:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_name'), 'topics', ['name'], unique=True)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('topic_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_research_at', sa.DateTime(), nullable=True),
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )
    op.create_index(op.f('ix_documents_topic_id'), 'documents', ['topic_id'], unique=False)
    op.create_index('idx_document_topic_status', 'documents', ['topic_id', 'status'], unique=False)
    op.create_index('idx_document_updated', 'documents', ['updated_at'], unique=False)

    # Create sources table
    op.create_table(
        'sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('tier', sa.Integer(), nullable=True),
        sa.Column('credibility_score', sa.Float(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(), nullable=False),
        sa.Column('total_citations', sa.Integer(), nullable=True),
        sa.Column('average_relevance', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index(op.f('ix_sources_url'), 'sources', ['url'], unique=True)
    op.create_index('idx_source_tier_credibility', 'sources', ['tier', 'credibility_score'], unique=False)

    # Create document_sources association table
    op.create_table(
        'document_sources',
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('citation_count', sa.Integer(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'source_id')
    )

    # Create relationships table
    op.create_table(
        'relationships',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_doc_id', sa.String(length=36), nullable=False),
        sa.Column('target_doc_id', sa.String(length=36), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('strength', sa.Float(), nullable=True),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_doc_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_doc_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_doc_id', 'target_doc_id', 'relationship_type', name='uq_relationship')
    )
    op.create_index('idx_relationship_type', 'relationships', ['relationship_type'], unique=False)
    op.create_index('idx_relationship_strength', 'relationships', ['strength'], unique=False)

    # Create research_sessions table
    op.create_table(
        'research_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('topic_id', sa.String(length=36), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_depth', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('current_hop', sa.Integer(), nullable=True),
        sa.Column('max_hops', sa.Integer(), nullable=True),
        sa.Column('documents_found', sa.Text(), nullable=True),
        sa.Column('document_created_id', sa.String(length=36), nullable=True),
        sa.Column('document_updated_id', sa.String(length=36), nullable=True),
        sa.Column('final_confidence', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('budget_target', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_sessions_topic_id'), 'research_sessions', ['topic_id'], unique=False)
    op.create_index('idx_session_status', 'research_sessions', ['status'], unique=False)
    op.create_index('idx_session_started', 'research_sessions', ['started_at'], unique=False)

    # Create research_hops table
    op.create_table(
        'research_hops',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('hop_number', sa.Integer(), nullable=False),
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('search_strategy', sa.String(length=100), nullable=True),
        sa.Column('sources_found_count', sa.Integer(), nullable=True),
        sa.Column('sources_added_count', sa.Integer(), nullable=True),
        sa.Column('confidence_before', sa.Float(), nullable=True),
        sa.Column('confidence_after', sa.Float(), nullable=True),
        sa.Column('llm_calls', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['research_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'hop_number', name='uq_session_hop')
    )
    op.create_index(op.f('ix_research_hops_session_id'), 'research_hops', ['session_id'], unique=False)
    op.create_index('idx_hop_session', 'research_hops', ['session_id', 'hop_number'], unique=False)

    # Create conflicts table
    op.create_table(
        'conflicts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('conflict_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_ids', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conflicts_document_id'), 'conflicts', ['document_id'], unique=False)
    op.create_index('idx_conflict_status', 'conflicts', ['status'], unique=False)
    op.create_index('idx_conflict_severity', 'conflicts', ['severity'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('conflicts')
    op.drop_table('research_hops')
    op.drop_table('research_sessions')
    op.drop_table('relationships')
    op.drop_table('document_sources')
    op.drop_table('sources')
    op.drop_table('documents')
    op.drop_table('topics')
