"""Performance benchmarks for ARIS system integration.

These benchmarks measure system performance across key operations
and help identify performance regressions.
"""

import asyncio
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from aris.core.config import ArisConfig
from aris.core.deduplication_gate import DeduplicationGate
from aris.core.progress_tracker import ProgressTracker
from aris.storage.database import DatabaseManager
from aris.storage.document_store import DocumentStore
from aris.storage.session_manager import SessionManager
from aris.models.document import Document


# ============================================================================
# BENCHMARK FIXTURES
# ============================================================================


@pytest.fixture
def benchmark_config(tmp_path):
    """Create config for benchmark tests."""
    aris_dir = tmp_path / ".aris"
    aris_dir.mkdir()
    return ArisConfig(
        research_dir=str(tmp_path / "research"),
        database_path=str(aris_dir / "benchmark.db"),
        tavily_api_key="test_key",
        sequential_mcp_path="npx",
    )


@pytest.fixture
async def benchmark_db(benchmark_config):
    """Create database for benchmarks."""
    manager = DatabaseManager(benchmark_config.database_path)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def benchmark_doc_store(benchmark_db):
    """Create document store for benchmarks."""
    return DocumentStore(benchmark_db)


@pytest.fixture
async def benchmark_session_manager(benchmark_db):
    """Create session manager for benchmarks."""
    return SessionManager(benchmark_db)


# ============================================================================
# PERFORMANCE: Document Operations
# ============================================================================


@pytest.mark.benchmark
class TestDocumentOperationsPerformance:
    """Benchmark document storage and retrieval operations."""

    @pytest.mark.asyncio
    async def test_single_document_save_performance(self, benchmark_doc_store):
        """Benchmark single document save operation."""
        doc = Document(
            title="Performance Test Document",
            content="Test content " * 100,
            topics=["performance", "benchmark"],
            source_url="https://example.com",
        )

        start = time.perf_counter()
        saved = await benchmark_doc_store.save_document(doc)
        elapsed = time.perf_counter() - start

        assert saved.id is not None
        assert elapsed < 1.0  # Should complete in < 1 second
        print(f"Single document save: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_bulk_document_save_performance(self, benchmark_doc_store):
        """Benchmark bulk document save operations."""
        documents = [
            Document(
                title=f"Document {i}",
                content=f"Content {i} " * 50,
                topics=[f"topic{i}"],
                source_url=f"https://example.com/{i}",
            )
            for i in range(20)
        ]

        start = time.perf_counter()
        saved_docs = []
        for doc in documents:
            saved = await benchmark_doc_store.save_document(doc)
            saved_docs.append(saved)
        elapsed = time.perf_counter() - start

        assert len(saved_docs) == 20
        assert all(doc.id is not None for doc in saved_docs)
        avg_time = elapsed / len(documents)
        assert avg_time < 0.2  # Average < 200ms per document
        print(f"Bulk document save (20 docs): {elapsed:.2f}s ({avg_time * 1000:.2f}ms per doc)")

    @pytest.mark.asyncio
    async def test_document_retrieval_performance(self, benchmark_doc_store):
        """Benchmark document retrieval operations."""
        # Save a document first
        doc = Document(
            title="Retrieval Test",
            content="Test content",
            topics=["test"],
            source_url="https://example.com",
        )
        saved = await benchmark_doc_store.save_document(doc)
        doc_id = saved.id

        # Benchmark retrieval
        start = time.perf_counter()
        retrieved = await benchmark_doc_store.get_document(doc_id)
        elapsed = time.perf_counter() - start

        assert retrieved is not None
        assert retrieved.title == doc.title
        assert elapsed < 0.5  # Should complete in < 500ms
        print(f"Document retrieval: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_document_with_large_content_performance(self, benchmark_doc_store):
        """Benchmark handling of large documents."""
        large_content = "This is test content. " * 10000  # ~200KB

        doc = Document(
            title="Large Document",
            content=large_content,
            topics=["large"],
            source_url="https://example.com",
        )

        start = time.perf_counter()
        saved = await benchmark_doc_store.save_document(doc)
        elapsed = time.perf_counter() - start

        assert saved.id is not None
        assert elapsed < 2.0  # Should complete in < 2 seconds
        print(f"Large document save (200KB): {elapsed * 1000:.2f}ms")


# ============================================================================
# PERFORMANCE: Deduplication Operations
# ============================================================================


@pytest.mark.benchmark
class TestDeduplicationPerformance:
    """Benchmark deduplication gate operations."""

    @pytest.mark.asyncio
    async def test_deduplication_check_performance(self, benchmark_db, benchmark_doc_store):
        """Benchmark deduplication checking."""
        gate = DeduplicationGate(benchmark_db, benchmark_doc_store)

        # Create initial documents
        for i in range(5):
            doc = Document(
                title=f"Reference Document {i}",
                content=f"Reference content {i}",
                topics=[f"topic{i}"],
                source_url=f"https://example.com/{i}",
            )
            await benchmark_doc_store.save_document(doc)

        # Benchmark deduplication check
        start = time.perf_counter()
        result = gate.check_before_write(
            content="New content similar to existing documents",
            metadata={"topics": ["topic1", "topic2"]},
            query="test query",
        )
        elapsed = time.perf_counter() - start

        assert result is not None
        assert elapsed < 1.0  # Should complete in < 1 second
        print(f"Deduplication check: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_deduplication_scaling_performance(self, benchmark_db, benchmark_doc_store):
        """Benchmark deduplication performance as document count increases."""
        gate = DeduplicationGate(benchmark_db, benchmark_doc_store)

        # Test with increasing document counts
        counts = [10, 50, 100]
        timings = []

        for count in counts:
            # Create documents
            for i in range(count):
                doc = Document(
                    title=f"Doc {i}",
                    content=f"Content {i}",
                    topics=["scaling"],
                    source_url=f"https://example.com/{i}",
                )
                await benchmark_doc_store.save_document(doc)

            # Measure deduplication check
            start = time.perf_counter()
            gate.check_before_write(
                content="New content",
                metadata={"topics": ["scaling"]},
                query="scaling test",
            )
            elapsed = time.perf_counter() - start
            timings.append((count, elapsed))
            print(f"Deduplication with {count} docs: {elapsed * 1000:.2f}ms")


# ============================================================================
# PERFORMANCE: Session Operations
# ============================================================================


@pytest.mark.benchmark
class TestSessionOperationsPerformance:
    """Benchmark session management operations."""

    @pytest.mark.asyncio
    async def test_session_creation_performance(self, benchmark_session_manager):
        """Benchmark session creation."""
        start = time.perf_counter()
        session = await benchmark_session_manager.create_session(
            query="Performance test",
            metadata={"test": True},
        )
        elapsed = time.perf_counter() - start

        assert session is not None
        assert elapsed < 0.5  # Should complete in < 500ms
        print(f"Session creation: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_session_state_update_performance(self, benchmark_session_manager):
        """Benchmark session state updates."""
        session = await benchmark_session_manager.create_session(
            query="State update test",
            metadata={},
        )

        start = time.perf_counter()
        await benchmark_session_manager.update_session_state(
            session.id,
            status="in_progress",
            metadata={"progress": 50},
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5  # Should complete in < 500ms
        print(f"Session state update: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_session_retrieval_performance(self, benchmark_session_manager):
        """Benchmark session retrieval."""
        session = await benchmark_session_manager.create_session(
            query="Retrieval test",
            metadata={},
        )
        session_id = session.id

        start = time.perf_counter()
        retrieved = await benchmark_session_manager.get_session(session_id)
        elapsed = time.perf_counter() - start

        assert retrieved is not None
        assert elapsed < 0.5  # Should complete in < 500ms
        print(f"Session retrieval: {elapsed * 1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_bulk_session_operations_performance(self, benchmark_session_manager):
        """Benchmark bulk session operations."""
        start = time.perf_counter()

        # Create multiple sessions
        sessions = []
        for i in range(10):
            session = await benchmark_session_manager.create_session(
                query=f"Query {i}",
                metadata={"index": i},
            )
            sessions.append(session)

        elapsed_create = time.perf_counter() - start

        # Retrieve all sessions
        start = time.perf_counter()
        retrieved = []
        for session in sessions:
            s = await benchmark_session_manager.get_session(session.id)
            retrieved.append(s)
        elapsed_retrieve = time.perf_counter() - start

        assert len(retrieved) == 10
        assert elapsed_create < 2.0  # Create 10 in < 2 seconds
        assert elapsed_retrieve < 1.0  # Retrieve 10 in < 1 second
        print(f"Create 10 sessions: {elapsed_create:.2f}s")
        print(f"Retrieve 10 sessions: {elapsed_retrieve:.2f}s")


# ============================================================================
# PERFORMANCE: Cost Tracking
# ============================================================================


@pytest.mark.benchmark
class TestCostTrackingPerformance:
    """Benchmark cost tracking operations."""

    def test_cost_operation_tracking_performance(self):
        """Benchmark cost tracking overhead."""
        from aris.mcp.tavily_client import CostTracker

        tracker = CostTracker()

        start = time.perf_counter()
        for i in range(1000):
            tracker.track_operation("search", cost=0.01)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5  # 1000 operations in < 500ms
        avg_per_op = (elapsed / 1000) * 1000000  # microseconds
        print(f"Cost tracking: {avg_per_op:.2f}µs per operation")

    def test_cost_summary_generation_performance(self):
        """Benchmark cost summary generation."""
        from aris.mcp.tavily_client import CostTracker

        tracker = CostTracker()

        # Create data
        for i in range(100):
            tracker.track_operation("search", cost=0.01)
            tracker.track_operation("analysis", cost=0.05)

        # Benchmark summary
        start = time.perf_counter()
        for _ in range(100):
            summary = tracker.get_summary()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5
        print(f"Cost summary (100 calls): {elapsed * 1000:.2f}ms")


# ============================================================================
# PERFORMANCE: Progress Tracking
# ============================================================================


@pytest.mark.benchmark
class TestProgressTrackingPerformance:
    """Benchmark progress tracking operations."""

    def test_hop_recording_performance(self):
        """Benchmark hop recording performance."""
        tracker = ProgressTracker()

        start = time.perf_counter()
        for i in range(100):
            tracker.record_hop(
                hop_number=i,
                query=f"Query {i}",
                results_count=10,
                hypotheses_count=5,
            )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5  # 100 hops in < 500ms
        print(f"Hop recording: {elapsed * 1000:.2f}ms for 100 hops")

    def test_stats_computation_performance(self):
        """Benchmark stats computation."""
        tracker = ProgressTracker()

        # Record hops
        for i in range(50):
            tracker.record_hop(
                hop_number=i,
                query=f"Query {i}",
                results_count=10,
                hypotheses_count=5,
            )

        # Benchmark stats computation
        start = time.perf_counter()
        for _ in range(100):
            stats = tracker.get_stats()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5
        print(f"Stats computation (100 calls): {elapsed * 1000:.2f}ms")


# ============================================================================
# PERFORMANCE: End-to-End Workflow
# ============================================================================


@pytest.mark.benchmark
class TestEndToEndWorkflowPerformance:
    """Benchmark complete workflow performance."""

    @pytest.mark.asyncio
    async def test_workflow_step_timing(self, benchmark_config, benchmark_db, benchmark_doc_store, benchmark_session_manager):
        """Benchmark individual workflow steps."""
        timings = {}

        # 1. Session creation
        start = time.perf_counter()
        session = await benchmark_session_manager.create_session(
            query="Performance workflow test",
            metadata={},
        )
        timings["session_creation"] = time.perf_counter() - start

        # 2. Document save
        start = time.perf_counter()
        doc = Document(
            title="Workflow Test",
            content="Test content",
            topics=["workflow"],
            source_url="https://example.com",
        )
        saved_doc = await benchmark_doc_store.save_document(doc)
        timings["document_save"] = time.perf_counter() - start

        # 3. Session update
        start = time.perf_counter()
        await benchmark_session_manager.update_session_state(
            session.id,
            status="in_progress",
            metadata={"document_id": saved_doc.id},
        )
        timings["session_update"] = time.perf_counter() - start

        # 4. Document retrieval
        start = time.perf_counter()
        retrieved = await benchmark_doc_store.get_document(saved_doc.id)
        timings["document_retrieval"] = time.perf_counter() - start

        # Print results
        total = sum(timings.values())
        print("\nWorkflow Performance Breakdown:")
        for step, elapsed in timings.items():
            print(f"  {step}: {elapsed * 1000:.2f}ms ({(elapsed/total*100):.1f}%)")
        print(f"  Total: {total * 1000:.2f}ms")

        # All steps should complete quickly
        assert total < 2.0


# ============================================================================
# PERFORMANCE HELPER FUNCTIONS
# ============================================================================


def assert_performance_target(elapsed_ms: float, target_ms: float, operation: str):
    """Assert operation met performance target."""
    if elapsed_ms > target_ms:
        pytest.fail(f"{operation} took {elapsed_ms:.2f}ms (target: {target_ms}ms)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "benchmark"])
