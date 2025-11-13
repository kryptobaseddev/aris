"""Integration tests for repository pattern."""

import pytest
from pathlib import Path
import tempfile
import shutil

from aris.storage.database import DatabaseManager
from aris.storage.repositories import (
    TopicRepository,
    DocumentRepository,
    SourceRepository,
    RelationshipRepository,
    ResearchSessionRepository,
    ResearchHopRepository,
    ConflictRepository,
)


class TestRepositories:
    """Integration tests for all repositories."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create and initialize DatabaseManager."""
        db = DatabaseManager(temp_db_path)
        db.initialize_database()
        return db

    @pytest.fixture
    def session(self, db_manager):
        """Create database session."""
        session = db_manager.get_session()
        yield session
        session.close()

    def test_topic_repository(self, session):
        """Test TopicRepository CRUD operations."""
        repo = TopicRepository(session)

        # Create
        topic = repo.create(name="AI Research", description="Artificial Intelligence")
        session.commit()
        assert topic.id is not None
        assert topic.name == "AI Research"

        # Get by ID
        retrieved = repo.get_by_id(topic.id)
        assert retrieved.name == "AI Research"

        # Get by name
        by_name = repo.get_by_name("AI Research")
        assert by_name.id == topic.id

        # Get or create (existing)
        existing = repo.get_or_create("AI Research")
        assert existing.id == topic.id

        # Get or create (new)
        new_topic = repo.get_or_create("Machine Learning", "ML research")
        session.commit()
        assert new_topic.id != topic.id

        # Get all
        all_topics = repo.get_all()
        assert len(all_topics) == 2

        # Update status
        repo.update_status(topic.id, "completed")
        session.commit()
        updated = repo.get_by_id(topic.id)
        assert updated.status == "completed"

    def test_document_repository(self, session):
        """Test DocumentRepository CRUD operations."""
        topic_repo = TopicRepository(session)
        doc_repo = DocumentRepository(session)

        # Create topic first
        topic = topic_repo.create(name="Test Topic")
        session.commit()

        # Create document
        doc = doc_repo.create(
            topic_id=topic.id,
            title="Test Document",
            file_path="/path/to/doc.md",
            word_count=100,
            confidence=0.8
        )
        session.commit()
        assert doc.id is not None

        # Get by ID
        retrieved = doc_repo.get_by_id(doc.id)
        assert retrieved.title == "Test Document"
        assert retrieved.topic.name == "Test Topic"

        # Find by topic
        topic_docs = doc_repo.find_by_topic(topic.id)
        assert len(topic_docs) == 1

        # Search by title
        search_results = doc_repo.search_by_title("Test")
        assert len(search_results) == 1

        # Update metadata
        doc_repo.update_metadata(doc.id, title="Updated Document", confidence=0.9)
        session.commit()
        updated = doc_repo.get_by_id(doc.id)
        assert updated.title == "Updated Document"
        assert updated.confidence == 0.9

    def test_source_repository(self, session):
        """Test SourceRepository CRUD operations."""
        repo = SourceRepository(session)

        # Create source
        source = repo.create(
            url="https://example.com/article",
            title="Example Article",
            source_type="academic",
            tier=1,
            credibility_score=0.9
        )
        session.commit()
        assert source.id is not None

        # Get by URL
        by_url = repo.get_by_url("https://example.com/article")
        assert by_url.id == source.id

        # Get or create
        existing = repo.get_or_create(
            url="https://example.com/article",
            title="Example Article"
        )
        assert existing.id == source.id

        # Find by tier
        tier1_sources = repo.find_by_tier(min_tier=1, max_tier=1)
        assert len(tier1_sources) == 1

        # Update credibility
        repo.update_credibility(source.id, 0.95, "verified")
        session.commit()
        updated = repo.get_by_id(source.id)
        assert updated.credibility_score == 0.95
        assert updated.verification_status == "verified"

    def test_relationship_repository(self, session):
        """Test RelationshipRepository CRUD operations."""
        topic_repo = TopicRepository(session)
        doc_repo = DocumentRepository(session)
        rel_repo = RelationshipRepository(session)

        # Create documents
        topic = topic_repo.create(name="Test Topic")
        session.commit()

        doc1 = doc_repo.create(topic_id=topic.id, title="Doc 1", file_path="/doc1.md")
        doc2 = doc_repo.create(topic_id=topic.id, title="Doc 2", file_path="/doc2.md")
        session.commit()

        # Create relationship
        rel = rel_repo.create(
            source_doc_id=doc1.id,
            target_doc_id=doc2.id,
            relationship_type="supports",
            strength=0.8,
            evidence="Doc 1 supports Doc 2"
        )
        session.commit()
        assert rel.id is not None

        # Find by document
        doc1_rels = rel_repo.find_by_document(doc1.id, direction="outgoing")
        assert len(doc1_rels) == 1

        doc2_rels = rel_repo.find_by_document(doc2.id, direction="incoming")
        assert len(doc2_rels) == 1

        # Find by type
        support_rels = rel_repo.find_by_type("supports", min_strength=0.7)
        assert len(support_rels) == 1

    def test_research_session_repository(self, session):
        """Test ResearchSessionRepository CRUD operations."""
        topic_repo = TopicRepository(session)
        session_repo = ResearchSessionRepository(session)

        # Create topic
        topic = topic_repo.create(name="Research Topic")
        session.commit()

        # Create research session
        research_session = session_repo.create(
            topic_id=topic.id,
            query_text="What is AI?",
            query_depth="standard",
            max_hops=3,
            budget_target=0.50
        )
        session.commit()
        assert research_session.id is not None

        # Get by ID
        retrieved = session_repo.get_by_id(research_session.id)
        assert retrieved.query_text == "What is AI?"

        # Find by topic
        topic_sessions = session_repo.find_by_topic(topic.id)
        assert len(topic_sessions) == 1

        # Update status
        session_repo.update_status(research_session.id, "complete", completed=True)
        session.commit()
        updated = session_repo.get_by_id(research_session.id)
        assert updated.status == "complete"
        assert updated.completed_at is not None

        # Add cost
        session_repo.add_cost(research_session.id, 0.25)
        session.commit()
        updated = session_repo.get_by_id(research_session.id)
        assert updated.total_cost == 0.25

    def test_research_hop_repository(self, session):
        """Test ResearchHopRepository CRUD operations."""
        topic_repo = TopicRepository(session)
        session_repo = ResearchSessionRepository(session)
        hop_repo = ResearchHopRepository(session)

        # Create research session
        topic = topic_repo.create(name="Test Topic")
        session.commit()

        research_session = session_repo.create(
            topic_id=topic.id,
            query_text="Test query",
            max_hops=3
        )
        session.commit()

        # Create hops
        hop1 = hop_repo.create(
            session_id=research_session.id,
            hop_number=1,
            search_query="initial search",
            search_strategy="broad"
        )
        session.commit()

        # Update hop results
        hop_repo.update_results(
            hop1.id,
            sources_found_count=10,
            sources_added_count=5,
            confidence_after=0.7,
            llm_calls=2,
            total_tokens=1000,
            cost=0.05
        )
        session.commit()

        updated_hop = hop_repo.get_by_id(hop1.id)
        assert updated_hop.sources_found_count == 10
        assert updated_hop.cost == 0.05

        # Find by session
        session_hops = hop_repo.find_by_session(research_session.id)
        assert len(session_hops) == 1

    def test_conflict_repository(self, session):
        """Test ConflictRepository CRUD operations."""
        topic_repo = TopicRepository(session)
        doc_repo = DocumentRepository(session)
        conflict_repo = ConflictRepository(session)

        # Create document
        topic = topic_repo.create(name="Test Topic")
        session.commit()

        doc = doc_repo.create(
            topic_id=topic.id,
            title="Test Doc",
            file_path="/doc.md"
        )
        session.commit()

        # Create conflict
        conflict = conflict_repo.create(
            document_id=doc.id,
            conflict_type="contradiction",
            description="Source A contradicts Source B",
            severity="high"
        )
        session.commit()
        assert conflict.id is not None

        # Find by document
        doc_conflicts = conflict_repo.find_by_document(doc.id)
        assert len(doc_conflicts) == 1

        # Find by severity
        high_conflicts = conflict_repo.find_by_severity("high")
        assert len(high_conflicts) == 1

        # Resolve conflict
        conflict_repo.resolve(conflict.id, "Resolved by choosing Source A")
        session.commit()
        resolved = conflict_repo.get_by_id(conflict.id)
        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None
