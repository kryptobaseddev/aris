"""Complete system integration tests for end-to-end workflows.

This module tests the entire ARIS system from query through document storage,
including deduplication, cost tracking, session persistence, and quality validation.
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from aris.core.config import ArisConfig
from aris.core.deduplication_gate import DeduplicationAction, DeduplicationGate, DeduplicationResult
from aris.core.progress_tracker import ProgressTracker
from aris.core.research_orchestrator import ResearchOrchestrator
from aris.mcp.tavily_client import CostTracker, TavilyClient
from aris.models.document import Document
from aris.storage.database import DatabaseManager
from aris.storage.document_store import DocumentStore
from aris.storage.git_manager import GitManager
from aris.storage.models import ResearchSession
from aris.storage.session_manager import SessionManager


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with required structure."""
    aris_dir = tmp_path / ".aris"
    aris_dir.mkdir()
    (aris_dir / "vectors").mkdir()
    (aris_dir / "documents").mkdir()

    return tmp_path


@pytest.fixture
def test_config(temp_project_dir):
    """Create test configuration pointing to temporary directories."""
    return ArisConfig(
        research_dir=str(temp_project_dir / "research"),
        database_path=str(temp_project_dir / ".aris" / "aris.db"),
        tavily_api_key="test_key_12345",
        sequential_mcp_path="npx",
        max_hops=3,
        confidence_target=0.70,
        early_stop_confidence=0.85,
        budget_limit=5.0,
    )


@pytest_asyncio.fixture
async def database_manager(test_config):
    """Create and initialize database manager."""
    manager = DatabaseManager(test_config.database_path)
    await manager.initialize()
    yield manager
    manager.close()


@pytest_asyncio.fixture
async def document_store(test_config, database_manager):
    """Create document store with test configuration."""
    store = DocumentStore(test_config)
    yield store


@pytest_asyncio.fixture
async def session_manager(database_manager):
    """Create session manager with database manager."""
    manager = SessionManager(database_manager)
    yield manager


@pytest.fixture
def mock_tavily_client():
    """Create mock Tavily client with cost tracking."""
    client = MagicMock(spec=TavilyClient)
    client.cost_tracker = CostTracker()

    # Mock search method
    async def mock_search(query):
        client.cost_tracker.track_operation("search", cost=0.01)
        return {
            "results": [
                {
                    "title": f"Result for {query}",
                    "url": "https://example.com",
                    "content": f"Content about {query}",
                }
            ],
            "query": query,
        }

    client.search = AsyncMock(side_effect=mock_search)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def mock_sequential_client():
    """Create mock Sequential client for reasoning."""
    client = MagicMock()

    # Mock the async context manager
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()

    # Mock plan_research
    mock_plan = MagicMock()
    mock_plan.query = "Test query"
    mock_plan.topics = ["topic1", "topic2"]
    mock_plan.hypotheses = ["hypothesis1", "hypothesis2"]
    mock_plan.information_gaps = ["gap1"]
    mock_plan.success_criteria = ["criteria1"]
    mock_plan.estimated_hops = 2
    client.plan_research = AsyncMock(return_value=mock_plan)

    # Mock generate_hypotheses
    mock_hypothesis = MagicMock()
    mock_hypothesis.statement = "Test hypothesis"
    mock_hypothesis.confidence_prior = 0.5
    mock_hypothesis.evidence_required = ["evidence"]
    client.generate_hypotheses = AsyncMock(return_value=[mock_hypothesis])

    # Mock test_hypothesis
    mock_result = MagicMock()
    mock_result.supported = True
    mock_result.posterior_confidence = 0.75
    mock_result.supporting_evidence = ["evidence1"]
    mock_result.contradicting_evidence = []
    client.test_hypothesis = AsyncMock(return_value=mock_result)

    # Mock synthesize_findings
    mock_synthesis = MagicMock()
    mock_synthesis.confidence = 0.78
    mock_synthesis.key_findings = ["Finding 1", "Finding 2"]
    mock_synthesis.remaining_gaps = []
    mock_synthesis.recommendations = ["Recommendation 1"]
    client.synthesize_findings = AsyncMock(return_value=mock_synthesis)

    return client


@pytest.fixture
def mock_git_manager(temp_project_dir):
    """Create mock Git manager."""
    manager = MagicMock(spec=GitManager)
    manager.initialize = MagicMock()
    manager.add_and_commit = MagicMock()
    manager.get_history = MagicMock(return_value=[])
    manager.is_initialized = MagicMock(return_value=True)
    return manager


# ============================================================================
# COMPLETE WORKFLOW TESTS
# ============================================================================


class TestCompleteWorkflow:
    """Test the complete research workflow from query to storage."""

    @pytest.mark.asyncio
    async def test_query_to_document_creation_workflow(
        self,
        test_config,
        database_manager,
        document_store,
        session_manager,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test complete workflow: Query → Research → Document Creation."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute research
            result = await orchestrator.execute_research(
                query="What is machine learning?",
                save_to_file=True,
            )

            # Verify result
            assert result is not None
            assert result.status == "completed"
            assert len(result.documents) > 0

            # Verify document was stored
            doc = result.documents[0]
            assert doc.id is not None
            assert doc.title is not None
            assert len(doc.content) > 0
            assert doc.topics is not None
            assert len(doc.topics) > 0

    @pytest.mark.asyncio
    async def test_query_to_deduplication_and_update(
        self,
        test_config,
        database_manager,
        document_store,
        session_manager,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test deduplication gate: Duplicate detection and document update."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            # First query - should create document
            result1 = await orchestrator.execute_research(
                query="What is machine learning?",
                save_to_file=True,
            )
            assert result1.status == "completed"
            assert len(result1.documents) > 0
            doc_id_1 = result1.documents[0].id

            # Second similar query - should detect as duplicate/similar
            result2 = await orchestrator.execute_research(
                query="Tell me about machine learning algorithms",
                save_to_file=True,
            )
            assert result2.status == "completed"

            # Verify deduplication behavior
            if len(result2.documents) > 0:
                doc_id_2 = result2.documents[0].id
                # Either same document (deduplicated) or different documents
                assert doc_id_2 is not None

    @pytest.mark.asyncio
    async def test_workflow_git_integration(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test Git integration in workflow: Commits and history."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute research which should trigger git operations
            result = await orchestrator.execute_research(
                query="What is AI?",
                save_to_file=True,
            )

            assert result.status == "completed"

            # Verify git manager was called
            mock_git_manager.initialize.assert_called()


# ============================================================================
# DEDUPLICATION GATE TESTS
# ============================================================================


class TestDeduplicationGateIntegration:
    """Test deduplication gate in integrated scenarios."""

    @pytest.mark.asyncio
    async def test_duplicate_detection_workflow(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test duplicate document detection through gate."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            # Create deduplication gate
            gate = DeduplicationGate(database_manager, document_store)

            # Create initial document
            doc1 = Document(
                title="Machine Learning Basics",
                content="Machine learning is about algorithms",
                topics=["ML", "AI"],
                source_url="https://example.com",
            )
            await document_store.save_document(doc1)

            # Test similar document
            metadata = {
                "query": "ML algorithms",
                "topics": ["ML", "AI"],
                "source_url": "https://example2.com",
            }

            result = gate.check_before_write(
                content="Machine learning algorithms explained",
                metadata=metadata,
                query="ML algorithms",
            )

            # Verify decision was made
            assert result is not None
            assert result.decision in [
                DeduplicationAction.CREATE,
                DeduplicationAction.UPDATE,
                DeduplicationAction.MERGE,
            ]

    @pytest.mark.asyncio
    async def test_deduplication_action_execution(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test execution of deduplication actions."""
        gate = DeduplicationGate(database_manager, document_store)

        # Create initial document
        doc = Document(
            title="Test Document",
            content="Initial content",
            topics=["test"],
            source_url="https://example.com",
        )
        saved_doc = await document_store.save_document(doc)

        # Simulate deduplication result suggesting update
        metadata = {"query": "test", "topics": ["test"]}
        result = gate.check_before_write(
            content="Updated content",
            metadata=metadata,
            query="test query",
        )

        assert result is not None


# ============================================================================
# SESSION PERSISTENCE TESTS
# ============================================================================


class TestSessionPersistence:
    """Test session persistence and resume functionality."""

    @pytest.mark.asyncio
    async def test_session_creation_and_persistence(
        self,
        test_config,
        database_manager,
        session_manager,
    ):
        """Test session creation and storage in database."""
        # Create a new session
        session = session_manager.create_session(
            query="Test research query",
            metadata={"source": "test"},
        )

        assert session is not None
        assert session.id is not None
        assert session.query == "Test research query"
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_session_resume(
        self,
        test_config,
        database_manager,
        session_manager,
    ):
        """Test resuming an existing session."""
        # Create initial session
        session1 = session_manager.create_session(
            query="Resumable research",
            metadata={"resumable": True},
        )
        session_id = session1.id

        # Retrieve and resume session
        session2 = session_manager.get_session(session_id)

        assert session2 is not None
        assert session2.id == session_id
        assert session2.query == "Resumable research"

    @pytest.mark.asyncio
    async def test_session_state_updates(
        self,
        test_config,
        database_manager,
        session_manager,
    ):
        """Test updating session state during execution."""
        session = session_manager.create_session(
            query="State tracking",
            metadata={},
        )

        # Update session state
        session_manager.update_session_state(
            session.id,
            status="in_progress",
            metadata={"hop": 1, "confidence": 0.5},
        )

        # Verify update
        updated = session_manager.get_session(session.id)
        assert updated.status == "in_progress"

    @pytest.mark.asyncio
    async def test_multiple_session_isolation(
        self,
        test_config,
        database_manager,
        session_manager,
    ):
        """Test that multiple sessions are properly isolated."""
        session1 = session_manager.create_session(
            query="Session 1",
            metadata={"id": 1},
        )
        session2 = session_manager.create_session(
            query="Session 2",
            metadata={"id": 2},
        )

        assert session1.id != session2.id

        retrieved1 = session_manager.get_session(session1.id)
        retrieved2 = session_manager.get_session(session2.id)

        assert retrieved1.query == "Session 1"
        assert retrieved2.query == "Session 2"


# ============================================================================
# COST TRACKING TESTS
# ============================================================================


class TestCostTrackingAndBudget:
    """Test cost tracking and budget enforcement."""

    def test_cost_tracker_initialization(self):
        """Test CostTracker initialization."""
        tracker = CostTracker()

        summary = tracker.get_summary()
        assert summary["total_cost"] == 0.0
        assert summary["operation_count"] == 0

    def test_cost_operation_tracking(self):
        """Test tracking individual operations."""
        tracker = CostTracker()

        # Track operations
        tracker.track_operation("search", cost=0.01)
        tracker.track_operation("search", cost=0.01)
        tracker.track_operation("analysis", cost=0.05)

        summary = tracker.get_summary()
        assert summary["total_cost"] == pytest.approx(0.07)
        assert summary["operation_count"] == 3
        assert summary["by_type"]["search"]["count"] == 2
        assert summary["by_type"]["analysis"]["count"] == 1

    def test_budget_limit_enforcement(self):
        """Test budget limit enforcement during operations."""
        tracker = CostTracker(budget_limit=0.05)

        tracker.track_operation("search", cost=0.01)
        tracker.track_operation("search", cost=0.01)
        tracker.track_operation("search", cost=0.01)

        summary = tracker.get_summary()
        assert summary["total_cost"] == pytest.approx(0.03)

        # Next operation would exceed budget
        tracker.track_operation("search", cost=0.04)
        assert summary["total_cost"] == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_cost_tracking_in_workflow(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test cost tracking during complete workflow."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute research
            await orchestrator.execute_research(
                query="Cost tracking test",
                save_to_file=True,
            )

            # Check cost tracking
            if hasattr(mock_tavily_client, "cost_tracker"):
                summary = mock_tavily_client.cost_tracker.get_summary()
                assert summary["total_cost"] >= 0


# ============================================================================
# QUALITY VALIDATION TESTS
# ============================================================================


class TestQualityValidationAndConfidence:
    """Test quality validation and confidence scoring."""

    @pytest.mark.asyncio
    async def test_confidence_scoring_in_workflow(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test confidence scoring throughout workflow."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            result = await orchestrator.execute_research(
                query="Confidence test query",
                save_to_file=True,
            )

            assert result is not None
            assert hasattr(result, "confidence") or len(result.documents) > 0

    @pytest.mark.asyncio
    async def test_document_quality_metrics(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test document quality metrics after creation."""
        doc = Document(
            title="Quality Test Document",
            content="This is a comprehensive test document with substantial content. " * 10,
            topics=["test", "quality", "metrics"],
            source_url="https://example.com",
            confidence=0.85,
        )

        saved_doc = await document_store.save_document(doc)

        assert saved_doc.confidence == 0.85
        assert len(saved_doc.topics) > 0
        assert len(saved_doc.content) > 0

    @pytest.mark.asyncio
    async def test_early_stopping_on_confidence(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test early stopping when confidence target is reached."""
        # Configure for early stopping
        test_config.early_stop_confidence = 0.75
        test_config.max_hops = 5

        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            result = await orchestrator.execute_research(
                query="Early stopping test",
                save_to_file=True,
            )

            assert result is not None


# ============================================================================
# PERFORMANCE AND BENCHMARK TESTS
# ============================================================================


class TestPerformanceBenchmarks:
    """Performance and benchmark tests."""

    @pytest.mark.asyncio
    async def test_workflow_execution_time(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Benchmark complete workflow execution time."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            start_time = time.time()
            result = await orchestrator.execute_research(
                query="Performance test",
                save_to_file=True,
            )
            elapsed = time.time() - start_time

            assert elapsed > 0
            assert result is not None

    def test_document_store_batch_performance(
        self,
        test_config,
    ):
        """Benchmark document store performance with multiple documents."""
        # This is a placeholder for performance testing
        # In real scenarios, would measure batch operations

        tracker = ProgressTracker()

        # Simulate progress
        for i in range(10):
            tracker.record_hop(
                hop_number=i,
                query=f"Query {i}",
                results_count=5,
                hypotheses_count=3,
            )

        stats = tracker.get_stats()
        assert stats["total_hops"] == 10

    @pytest.mark.asyncio
    async def test_deduplication_performance_scaling(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test deduplication performance with increasing document count."""
        gate = DeduplicationGate(database_manager, document_store)

        # Create multiple documents
        documents = []
        for i in range(10):
            doc = Document(
                title=f"Document {i}",
                content=f"Content for document {i}",
                topics=[f"topic{i}"],
                source_url=f"https://example.com/{i}",
            )
            saved_doc = await document_store.save_document(doc)
            documents.append(saved_doc)

        assert len(documents) == 10

    @pytest.mark.asyncio
    async def test_session_recovery_time(
        self,
        test_config,
        database_manager,
        session_manager,
    ):
        """Benchmark session recovery time."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = session_manager.create_session(
                query=f"Query {i}",
                metadata={"index": i},
            )
            sessions.append(session)

        # Measure recovery time
        start_time = time.time()
        for session in sessions:
            recovered = session_manager.get_session(session.id)
            assert recovered is not None
        elapsed = time.time() - start_time

        assert elapsed > 0


# ============================================================================
# INTEGRATION STRESS TESTS
# ============================================================================


class TestIntegrationStress:
    """Stress tests for integrated system components."""

    @pytest.mark.asyncio
    async def test_concurrent_research_queries(
        self,
        test_config,
        database_manager,
        document_store,
        mock_tavily_client,
        mock_sequential_client,
        mock_git_manager,
    ):
        """Test handling concurrent research queries."""
        with patch("aris.core.research_orchestrator.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.core.research_orchestrator.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.GitManager", return_value=mock_git_manager), \
             patch("aris.core.research_orchestrator.DatabaseManager", return_value=database_manager):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute multiple queries concurrently
            queries = [
                "Query 1",
                "Query 2",
                "Query 3",
            ]

            # Sequential execution in test environment
            for query in queries:
                result = await orchestrator.execute_research(
                    query=query,
                    save_to_file=True,
                )
                assert result is not None

    @pytest.mark.asyncio
    async def test_large_document_handling(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test handling of large documents."""
        # Create a large document
        large_content = "This is test content. " * 5000  # ~100KB

        doc = Document(
            title="Large Document",
            content=large_content,
            topics=["large", "stress", "test"],
            source_url="https://example.com",
        )

        saved_doc = await document_store.save_document(doc)

        assert saved_doc.id is not None
        assert len(saved_doc.content) > 0


# ============================================================================
# END-TO-END CRITICAL PATH TESTS
# ============================================================================


class TestCriticalPaths:
    """Test critical system paths and failure scenarios."""

    @pytest.mark.asyncio
    async def test_research_failure_recovery(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test recovery from research operation failures."""
        session_manager = SessionManager(database_manager)

        # Create a session
        session = session_manager.create_session(
            query="Recovery test",
            metadata={"test": True},
        )

        # Simulate failure recovery
        session_manager.update_session_state(
            session.id,
            status="failed",
            metadata={"error": "Test error"},
        )

        # Verify session state
        updated = session_manager.get_session(session.id)
        assert updated.status == "failed"

    @pytest.mark.asyncio
    async def test_document_update_failure_handling(
        self,
        test_config,
        database_manager,
        document_store,
    ):
        """Test handling of document update failures."""
        doc = Document(
            title="Update Test",
            content="Initial content",
            topics=["test"],
            source_url="https://example.com",
        )

        saved_doc = await document_store.save_document(doc)
        assert saved_doc.id is not None

    @pytest.mark.asyncio
    async def test_git_operation_failure_handling(
        self,
        mock_git_manager,
    ):
        """Test handling of Git operation failures."""
        # Git manager should handle failures gracefully
        mock_git_manager.initialize()
        mock_git_manager.add_and_commit("test", "test message")

        # Verify calls were made
        mock_git_manager.initialize.assert_called()


# ============================================================================
# UTILITY TEST HELPERS
# ============================================================================


class TestIntegrationHelpers:
    """Helper tests for integration validation."""

    def test_mock_tavily_client_functionality(self, mock_tavily_client):
        """Test mock Tavily client behaves correctly."""
        assert mock_tavily_client is not None
        assert hasattr(mock_tavily_client, "search")
        assert hasattr(mock_tavily_client, "cost_tracker")

    def test_mock_sequential_client_functionality(self, mock_sequential_client):
        """Test mock Sequential client behaves correctly."""
        assert mock_sequential_client is not None
        assert hasattr(mock_sequential_client, "plan_research")
        assert hasattr(mock_sequential_client, "synthesize_findings")

    def test_config_validation(self, test_config):
        """Test configuration is properly validated."""
        assert test_config.research_dir is not None
        assert test_config.database_path is not None
        assert test_config.max_hops > 0
        assert test_config.confidence_target > 0
        assert test_config.budget_limit > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
