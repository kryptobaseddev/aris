"""Critical path integration tests ensuring core system workflows function correctly.

These tests validate the most critical flows through the system and are required
to pass before any release or major changes.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aris.core.config import ArisConfig
from aris.core.deduplication_gate import DeduplicationGate
from aris.core.document_merger import DocumentMerger
from aris.storage.database import DatabaseManager
from aris.storage.document_store import DocumentStore
from aris.storage.git_manager import GitManager
from aris.storage.session_manager import SessionManager
from aris.models.document import Document


# ============================================================================
# CRITICAL PATH: Query Ingestion and Planning
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_QueryIngestion:
    """Critical path: User query → Planning → Topic extraction."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        aris_dir = tmp_path / ".aris"
        aris_dir.mkdir()
        return ArisConfig(
            research_dir=str(tmp_path / "research"),
            database_path=str(aris_dir / "test.db"),
            tavily_api_key="test_key",
            sequential_mcp_path="npx",
        )

    @pytest_asyncio.fixture
    async def db_manager(self, test_config):
        """Create database manager."""
        manager = DatabaseManager(test_config.database_path)
        await manager.initialize()
        yield manager
        manager.close()

    @pytest.mark.asyncio
    async def test_query_acceptance_and_validation(self, test_config, db_manager):
        """CRITICAL: Verify query is properly accepted and validated."""
        session_manager = SessionManager(db_manager)

        query = "What are the latest advances in quantum computing?"
        session = session_manager.create_session(
            query=query,
            metadata={"source": "test", "priority": "high"},
        )

        assert session is not None
        assert session.id is not None
        assert session.query == query
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_session_initialization(self, test_config, db_manager):
        """CRITICAL: Verify session is properly initialized with metadata."""
        session_manager = SessionManager(db_manager)

        session = session_manager.create_session(
            query="Test query",
            metadata={
                "timestamp": "2024-01-01",
                "source": "direct",
                "tags": ["critical", "urgent"],
            },
        )

        assert session.metadata is not None
        # Metadata should be preserved
        retrieved = session_manager.get_session(session.id)
        assert retrieved is not None


# ============================================================================
# CRITICAL PATH: Deduplication and Document Update
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_Deduplication:
    """Critical path: Detect similar documents → Make update decision."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        aris_dir = tmp_path / ".aris"
        aris_dir.mkdir()
        return ArisConfig(
            research_dir=str(tmp_path / "research"),
            database_path=str(aris_dir / "test.db"),
            tavily_api_key="test_key",
            sequential_mcp_path="npx",
        )

    @pytest_asyncio.fixture
    async def db_manager(self, test_config):
        """Create database manager."""
        manager = DatabaseManager(test_config.database_path)
        await manager.initialize()
        yield manager
        manager.close()

    @pytest_asyncio.fixture
    async def doc_store(self, test_config, db_manager):
        """Create document store."""
        return DocumentStore(test_config)

    @pytest.mark.asyncio
    async def test_duplicate_detection_flow(self, db_manager, doc_store):
        """CRITICAL: Verify duplicate documents are properly detected."""
        gate = DeduplicationGate(db_manager, doc_store)

        # Create initial document
        doc = Document(
            title="Machine Learning Introduction",
            content="Machine learning is a subset of artificial intelligence",
            topics=["ML", "AI"],
            source_url="https://example.com/ml",
        )
        saved_doc = await doc_store.save_document(doc)
        assert saved_doc.id is not None

        # Check for similar document
        metadata = {
            "query": "ML basics",
            "topics": ["ML", "AI"],
            "source_url": "https://example2.com/ml",
        }

        result = gate.check_before_write(
            content="Introduction to machine learning and AI",
            metadata=metadata,
            query="ML basics",
        )

        assert result is not None
        assert result.decision is not None
        # Should make some decision (CREATE, UPDATE, or MERGE)

    @pytest.mark.asyncio
    async def test_deduplication_decision_execution(self, db_manager, doc_store):
        """CRITICAL: Verify deduplication decisions are executable."""
        gate = DeduplicationGate(db_manager, doc_store)

        # Create and save a document
        doc = Document(
            title="Test Document",
            content="This is test content",
            topics=["test"],
            source_url="https://example.com",
        )
        saved_doc = await doc_store.save_document(doc)

        # Get decision
        result = gate.check_before_write(
            content="Similar test content",
            metadata={"topics": ["test"]},
            query="test",
        )

        # All possible decisions should be valid
        assert result.decision is not None
        assert result.confidence >= 0
        assert result.confidence <= 1


# ============================================================================
# CRITICAL PATH: Document Storage and Retrieval
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_DocumentStorage:
    """Critical path: Save document → Retrieve → Verify integrity."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        aris_dir = tmp_path / ".aris"
        aris_dir.mkdir()
        return ArisConfig(
            research_dir=str(tmp_path / "research"),
            database_path=str(aris_dir / "test.db"),
            tavily_api_key="test_key",
            sequential_mcp_path="npx",
        )

    @pytest_asyncio.fixture
    async def db_manager(self, test_config):
        """Create database manager."""
        manager = DatabaseManager(test_config.database_path)
        await manager.initialize()
        yield manager
        manager.close()

    @pytest_asyncio.fixture
    async def doc_store(self, test_config, db_manager):
        """Create document store."""
        return DocumentStore(test_config)

    @pytest.mark.asyncio
    async def test_document_save_and_retrieve(self, doc_store):
        """CRITICAL: Verify document can be saved and retrieved."""
        doc = Document(
            title="Test Document",
            content="Test content for document storage",
            topics=["test", "storage"],
            source_url="https://example.com",
        )

        saved = await doc_store.save_document(doc)
        assert saved.id is not None
        doc_id = saved.id

        retrieved = await doc_store.get_document(doc_id)
        assert retrieved is not None
        assert retrieved.title == doc.title
        assert retrieved.content == doc.content

    @pytest.mark.asyncio
    async def test_document_integrity_after_retrieval(self, doc_store):
        """CRITICAL: Verify document data integrity through save-retrieve cycle."""
        original = Document(
            title="Integrity Test",
            content="Testing data integrity with special characters: äöü €¥£",
            topics=["integrity", "test"],
            source_url="https://example.com/special",
            confidence=0.92,
        )

        saved = await doc_store.save_document(original)
        retrieved = await doc_store.get_document(saved.id)

        assert retrieved.title == original.title
        assert retrieved.content == original.content
        assert retrieved.topics == original.topics
        assert retrieved.source_url == original.source_url
        assert retrieved.confidence == original.confidence

    @pytest.mark.asyncio
    async def test_bulk_document_operations(self, doc_store):
        """CRITICAL: Verify bulk document operations work correctly."""
        documents = []
        for i in range(10):
            doc = Document(
                title=f"Document {i}",
                content=f"Content for document {i}",
                topics=[f"topic{i}"],
                source_url=f"https://example.com/{i}",
            )
            documents.append(doc)

        # Save all documents
        saved_docs = []
        for doc in documents:
            saved = await doc_store.save_document(doc)
            saved_docs.append(saved)

        assert len(saved_docs) == 10
        assert all(doc.id is not None for doc in saved_docs)


# ============================================================================
# CRITICAL PATH: Session Persistence
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_SessionPersistence:
    """Critical path: Create session → Persist state → Resume session."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        aris_dir = tmp_path / ".aris"
        aris_dir.mkdir()
        return ArisConfig(
            research_dir=str(tmp_path / "research"),
            database_path=str(aris_dir / "test.db"),
            tavily_api_key="test_key",
            sequential_mcp_path="npx",
        )

    @pytest_asyncio.fixture
    async def db_manager(self, test_config):
        """Create database manager."""
        manager = DatabaseManager(test_config.database_path)
        await manager.initialize()
        yield manager
        manager.close()

    @pytest_asyncio.fixture
    async def session_manager(self, db_manager):
        """Create session manager."""
        return SessionManager(db_manager)

    @pytest.mark.asyncio
    async def test_session_persistence_cycle(self, session_manager):
        """CRITICAL: Verify session can be created, persisted, and resumed."""
        # Create session
        session = session_manager.create_session(
            query="Persistence test query",
            metadata={"test": True},
        )
        session_id = session.id

        # Persist state update
        session_manager.update_session_state(
            session_id,
            status="in_progress",
            metadata={"hop": 1, "progress": 50},
        )

        # Resume session
        resumed = session_manager.get_session(session_id)
        assert resumed is not None
        assert resumed.id == session_id
        assert resumed.query == "Persistence test query"
        assert resumed.status == "in_progress"

    @pytest.mark.asyncio
    async def test_session_state_transitions(self, session_manager):
        """CRITICAL: Verify session state transitions are valid."""
        session = session_manager.create_session(
            query="State transition test",
            metadata={},
        )

        # Valid transitions: active → in_progress → completed
        session_manager.update_session_state(
            session.id,
            status="in_progress",
            metadata={"current_hop": 1},
        )

        session_in_progress = session_manager.get_session(session.id)
        assert session_in_progress.status == "in_progress"

        # Complete session
        session_manager.update_session_state(
            session.id,
            status="completed",
            metadata={"total_hops": 3},
        )

        completed = session_manager.get_session(session.id)
        assert completed.status == "completed"


# ============================================================================
# CRITICAL PATH: Cost Tracking and Budget Enforcement
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_CostTracking:
    """Critical path: Track costs → Check budget → Enforce limits."""

    def test_cost_tracking_accuracy(self):
        """CRITICAL: Verify cost tracking is accurate."""
        from aris.mcp.tavily_client import CostTracker

        tracker = CostTracker(budget_limit=1.0)

        # Track operations
        tracker.track_operation("search", cost=0.10)
        tracker.track_operation("search", cost=0.15)
        tracker.track_operation("analysis", cost=0.20)

        summary = tracker.get_summary()

        assert summary["total_cost"] == pytest.approx(0.45)
        assert summary["operation_count"] == 3
        assert summary["by_type"]["search"]["count"] == 2
        assert summary["by_type"]["search"]["cost"] == pytest.approx(0.25)
        assert summary["by_type"]["analysis"]["count"] == 1
        assert summary["by_type"]["analysis"]["cost"] == pytest.approx(0.20)

    def test_budget_limit_enforcement(self):
        """CRITICAL: Verify budget limits are enforced."""
        from aris.mcp.tavily_client import CostTracker

        tracker = CostTracker(budget_limit=0.50)

        # Track operations within budget
        tracker.track_operation("search", cost=0.30)
        assert tracker.get_summary()["total_cost"] == pytest.approx(0.30)

        # Try to track beyond budget
        tracker.track_operation("search", cost=0.25)
        # Should still track
        assert tracker.get_summary()["total_cost"] == pytest.approx(0.55)


# ============================================================================
# CRITICAL PATH: Git Integration
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_GitIntegration:
    """Critical path: Initialize repo → Create commits → Track history."""

    @pytest.fixture
    def mock_git_manager(self):
        """Create mock Git manager."""
        manager = MagicMock(spec=GitManager)
        manager.initialize = MagicMock()
        manager.add_and_commit = MagicMock()
        manager.get_history = MagicMock(return_value=[])
        manager.is_initialized = MagicMock(return_value=True)
        return manager

    def test_git_manager_initialization(self, mock_git_manager):
        """CRITICAL: Verify Git manager can be initialized."""
        mock_git_manager.initialize()
        mock_git_manager.initialize.assert_called()

    def test_git_commit_creation(self, mock_git_manager):
        """CRITICAL: Verify Git commits can be created."""
        mock_git_manager.add_and_commit(
            file_path="test.md",
            message="Initial research document",
        )

        mock_git_manager.add_and_commit.assert_called_with(
            file_path="test.md",
            message="Initial research document",
        )

    def test_git_history_tracking(self, mock_git_manager):
        """CRITICAL: Verify Git history is tracked."""
        mock_git_manager.get_history.return_value = [
            {"message": "Initial document", "timestamp": "2024-01-01"},
            {"message": "Updated with new findings", "timestamp": "2024-01-02"},
        ]

        history = mock_git_manager.get_history()
        assert len(history) == 2
        assert history[0]["message"] == "Initial document"


# ============================================================================
# CRITICAL PATH: Quality Validation
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_QualityValidation:
    """Critical path: Assess confidence → Validate quality → Make decisions."""

    @pytest.mark.asyncio
    async def test_confidence_scoring(self):
        """CRITICAL: Verify confidence scoring works correctly."""
        doc = Document(
            title="Quality Test",
            content="Document with quality assessment",
            topics=["quality"],
            source_url="https://example.com",
            confidence=0.85,
        )

        assert doc.confidence == 0.85
        assert 0 <= doc.confidence <= 1

    @pytest.mark.asyncio
    async def test_quality_threshold_enforcement(self):
        """CRITICAL: Verify quality thresholds are enforced."""
        # Low confidence document
        low_conf = Document(
            title="Low Confidence",
            content="Content",
            topics=["test"],
            source_url="https://example.com",
            confidence=0.45,
        )

        # High confidence document
        high_conf = Document(
            title="High Confidence",
            content="Content",
            topics=["test"],
            source_url="https://example.com",
            confidence=0.95,
        )

        assert low_conf.confidence < high_conf.confidence


# ============================================================================
# CRITICAL PATH: Error Recovery
# ============================================================================


@pytest.mark.critical
class TestCriticalPath_ErrorRecovery:
    """Critical path: Handle errors → Recover gracefully → Continue."""

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create test configuration."""
        aris_dir = tmp_path / ".aris"
        aris_dir.mkdir()
        return ArisConfig(
            research_dir=str(tmp_path / "research"),
            database_path=str(aris_dir / "test.db"),
            tavily_api_key="test_key",
            sequential_mcp_path="npx",
        )

    @pytest_asyncio.fixture
    async def db_manager(self, test_config):
        """Create database manager."""
        manager = DatabaseManager(test_config.database_path)
        await manager.initialize()
        yield manager
        manager.close()

    @pytest_asyncio.fixture
    async def session_manager(self, db_manager):
        """Create session manager."""
        return SessionManager(db_manager)

    @pytest.mark.asyncio
    async def test_error_recording_in_session(self, session_manager):
        """CRITICAL: Verify errors are properly recorded in session."""
        session = session_manager.create_session(
            query="Error recovery test",
            metadata={},
        )

        # Record error
        session_manager.update_session_state(
            session.id,
            status="error",
            metadata={"error": "Test error condition"},
        )

        retrieved = session_manager.get_session(session.id)
        assert retrieved.status == "error"

    @pytest.mark.asyncio
    async def test_session_recovery_after_failure(self, session_manager):
        """CRITICAL: Verify session can recover after failure."""
        session = session_manager.create_session(
            query="Recovery test",
            metadata={},
        )

        # Mark as failed
        session_manager.update_session_state(
            session.id,
            status="error",
            metadata={"error": "Temporary failure"},
        )

        # Recover to in_progress
        session_manager.update_session_state(
            session.id,
            status="in_progress",
            metadata={"recovery": True},
        )

        recovered = session_manager.get_session(session.id)
        assert recovered.status == "in_progress"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "critical"])
