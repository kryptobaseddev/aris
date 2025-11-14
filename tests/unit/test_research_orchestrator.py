"""Unit tests for ResearchOrchestrator."""

import sys
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Mock chromadb before any imports that depend on it
chromadb_mock = MagicMock()
chromadb_mock.config = MagicMock()
chromadb_mock.config.Settings = MagicMock()
sys.modules["chromadb"] = chromadb_mock
sys.modules["chromadb.config"] = chromadb_mock.config

from aris.core.research_orchestrator import ResearchOrchestrator, ResearchOrchestratorError
from aris.models.config import ArisConfig
from aris.models.research import ResearchDepth, ResearchQuery, ResearchSession


class FormattableMock(MagicMock):
    """Mock that supports format strings."""
    def __format__(self, format_spec):
        """Support format strings by returning the mock's value."""
        # If we have a real value set, use it
        if hasattr(self, '_format_value'):
            return format(self._format_value, format_spec)
        # Otherwise return a placeholder
        return f"<mock:{format_spec}>"


@pytest.fixture
def mock_config():
    """Create mock ARIS config."""
    return ArisConfig(
        research_dir="./research",
        database_path="./test.db",
        tavily_api_key="test_key",
        sequential_mcp_path="npx",
    )


@pytest.fixture
def mock_reasoning_engine():
    """Create mock reasoning engine."""
    engine = MagicMock()
    engine.analyze_query = AsyncMock()
    engine.execute_research_hop = AsyncMock()
    engine.sequential = MagicMock()
    engine.sequential.synthesize_findings = AsyncMock()

    # Fix: Use side_effect for proper async context manager behavior
    engine.__aenter__ = AsyncMock(side_effect=lambda: engine)
    engine.__aexit__ = AsyncMock(side_effect=lambda *args: None)

    return engine


@pytest.fixture
def mock_document_store():
    """Create mock document store."""
    store = MagicMock()
    store.create_document = MagicMock()
    return store


@pytest.fixture
def orchestrator(mock_config, mock_reasoning_engine, mock_document_store):
    """Create ResearchOrchestrator with mocked dependencies."""
    with patch("aris.core.research_orchestrator.ReasoningEngine", return_value=mock_reasoning_engine), \
         patch("aris.storage.DocumentStore", return_value=mock_document_store), \
         patch("aris.core.research_orchestrator.DatabaseManager"), \
         patch("aris.core.document_finder.DocumentFinder"), \
         patch("aris.core.deduplication_gate.DeduplicationGate"), \
         patch("aris.mcp.serena_client.SerenaClient"):
        return ResearchOrchestrator(mock_config)


class TestResearchOrchestrator:
    """Test ResearchOrchestrator functionality."""

    def test_initialization(self, mock_config):
        """Test orchestrator initialization."""
        with patch("aris.core.research_orchestrator.ReasoningEngine"), \
             patch("aris.storage.DocumentStore"), \
             patch("aris.core.research_orchestrator.DatabaseManager"):
            orchestrator = ResearchOrchestrator(mock_config)

            assert orchestrator.config == mock_config
            assert orchestrator.progress_tracker is not None

    def test_get_max_hops(self, orchestrator):
        """Test max hops calculation for different depths."""
        assert orchestrator._get_max_hops("quick") == 1
        assert orchestrator._get_max_hops("standard") == 3
        assert orchestrator._get_max_hops("deep") == 5
        assert orchestrator._get_max_hops("unknown") == 3  # Default

    def test_generate_title(self, orchestrator):
        """Test title generation from query."""
        title = orchestrator._generate_title("What is quantum computing?")
        assert title == "What is quantum computing?"

        # Test long query truncation
        long_query = "x" * 100
        title = orchestrator._generate_title(long_query)
        assert len(title) <= 80
        assert title.endswith("...")

    def test_create_research_session(self, orchestrator):
        """Test research session creation."""
        query = "Test query"
        depth = "standard"

        session = orchestrator._create_research_session(query, depth, None)

        assert session.query.query_text == query
        assert session.query.depth == ResearchDepth.STANDARD
        assert session.budget_target == 0.50
        assert session.status == "planning"

    def test_create_research_session_with_cost_override(self, orchestrator):
        """Test research session with cost override."""
        query = "Test query"
        depth = "standard"
        max_cost = 1.00

        session = orchestrator._create_research_session(query, depth, max_cost)

        assert session.budget_target == 1.00
        assert session.query.max_cost == 1.00

    def test_create_research_session_budgets(self, orchestrator):
        """Test default budgets for different depths."""
        query = "test query"  # Must be ≥5 chars for validation

        quick_session = orchestrator._create_research_session(query, "quick", None)
        assert quick_session.budget_target == 0.20

        standard_session = orchestrator._create_research_session(query, "standard", None)
        assert standard_session.budget_target == 0.50

        deep_session = orchestrator._create_research_session(query, "deep", None)
        assert deep_session.budget_target == 2.00


class TestResearchExecution:
    """Test research execution workflows."""

    @pytest.mark.asyncio
    async def test_execute_research_basic(self, orchestrator, mock_reasoning_engine):
        """Test basic research execution."""
        # Patch _update_session and logger to avoid format issues with mocks
        with patch.object(orchestrator, '_update_session', return_value=None), \
             patch('aris.core.research_orchestrator.logger'):
            # Setup mocks - use real Pydantic models where needed
            from aris.mcp.reasoning_schemas import HopResult, Synthesis

            mock_plan = MagicMock()
            mock_plan.hypotheses = [MagicMock(), MagicMock()]
            mock_reasoning_engine.analyze_query.return_value = mock_plan

            # Create real HopResult to avoid format string issues
            mock_synthesis = Synthesis(
                confidence=0.75,
                key_findings=["Finding 1"],
                gaps_remaining=[],
                recommendations=[]
            )
            mock_hop_result = HopResult(
                hop_number=1,
                evidence=[{"url": "source1"}, {"url": "source2"}],
                results=[],
                synthesis=mock_synthesis
            )
            mock_reasoning_engine.execute_research_hop.return_value = mock_hop_result

            final_synthesis = Synthesis(
                confidence=0.75,
                key_findings=["Final finding"],
                gaps_remaining=[],
                recommendations=[]
            )
            mock_reasoning_engine.sequential.synthesize_findings.return_value = final_synthesis

            mock_document = MagicMock()
            mock_document.file_path = Path("research/test.md")
            orchestrator.document_store.create_document.return_value = mock_document

            # Execute research
            result = await orchestrator.execute_research(
                query="Test query",
                depth="quick",
                max_cost=None
            )

            # Verify result
            assert result.success is True
            assert result.query_text == "Test query"
            assert result.document_path == str(mock_document.file_path)
            assert result.operation == "created"
            assert result.hops_executed > 0

            # Verify calls
            mock_reasoning_engine.analyze_query.assert_called_once()
            mock_reasoning_engine.execute_research_hop.assert_called()

    @pytest.mark.asyncio
    async def test_execute_research_early_stopping(self, orchestrator, mock_reasoning_engine):
        """Test early stopping at high confidence."""
        with patch.object(orchestrator, '_update_session', return_value=None), \
             patch('aris.core.research_orchestrator.logger'):
            # Setup for high confidence on first hop
            mock_plan = MagicMock()
            mock_plan.hypotheses = [MagicMock()]
            mock_reasoning_engine.analyze_query.return_value = mock_plan

            mock_hop_result = MagicMock()
            mock_hop_result.evidence = ["source1"]
            mock_hop_result.hypothesis_results = []
            mock_hop_result.synthesis = MagicMock()
            mock_hop_result.synthesis.confidence = 0.80  # Above target
            mock_hop_result.synthesis.key_findings = ["Finding 1"]
            mock_reasoning_engine.execute_research_hop.return_value = mock_hop_result

            mock_synthesis = MagicMock()
            mock_synthesis.key_findings = []
            mock_synthesis.remaining_gaps = []
            mock_synthesis.recommendations = []
            mock_reasoning_engine.sequential.synthesize_findings.return_value = mock_synthesis

            mock_document = MagicMock()
            mock_document.file_path = Path("research/test.md")
            orchestrator.document_store.create_document.return_value = mock_document

            # Execute with max_hops=5 but should stop at 1
            result = await orchestrator.execute_research(
                query="Test query",
                depth="deep",  # 5 hops
                max_cost=None
            )

            # Should stop after 1 hop due to confidence
            assert result.hops_executed == 1
            assert result.confidence >= 0.70

    @pytest.mark.asyncio
    async def test_execute_research_budget_limit(self, orchestrator, mock_reasoning_engine):
        """Test research stops at budget limit."""
        with patch.object(orchestrator, '_update_session', return_value=None), \
             patch('aris.core.research_orchestrator.logger'):
            # Setup high-cost hops
            mock_plan = MagicMock()
            mock_plan.hypotheses = [MagicMock()]
            mock_reasoning_engine.analyze_query.return_value = mock_plan

            mock_hop_result = MagicMock()
            mock_hop_result.evidence = []
            mock_hop_result.hypothesis_results = []
            mock_hop_result.synthesis = MagicMock()
            mock_hop_result.synthesis.confidence = 0.50  # Low confidence
            mock_hop_result.synthesis.key_findings = []
            mock_reasoning_engine.execute_research_hop.return_value = mock_hop_result

            mock_synthesis = MagicMock()
            mock_synthesis.key_findings = []
            mock_synthesis.remaining_gaps = []
            mock_synthesis.recommendations = []
            mock_reasoning_engine.sequential.synthesize_findings.return_value = mock_synthesis

            mock_document = MagicMock()
            mock_document.file_path = Path("research/test.md")
            orchestrator.document_store.create_document.return_value = mock_document

            # Execute with very low budget
            result = await orchestrator.execute_research(
                query="Test query",
                depth="standard",
                max_cost=0.01  # Very low budget
            )

            # Should warn about budget
            assert len(result.warnings) > 0
            assert any("budget" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_research_handles_errors(self, orchestrator, mock_reasoning_engine):
        """Test error handling in research execution."""
        # Make analyze_query fail
        mock_reasoning_engine.analyze_query.side_effect = Exception("Analysis failed")

        # Should raise ResearchOrchestratorError
        with pytest.raises(ResearchOrchestratorError) as exc_info:
            await orchestrator.execute_research(
                query="Test query",
                depth="quick",
                max_cost=None
            )

        assert "Analysis failed" in str(exc_info.value)


class TestProgressTracking:
    """Test progress tracking functionality."""

    @pytest.mark.asyncio
    async def test_progress_tracking(self, orchestrator, mock_reasoning_engine):
        """Test progress events are emitted."""
        with patch.object(orchestrator, '_update_session', return_value=None), \
             patch('aris.core.research_orchestrator.logger'):
            # Setup mocks
            mock_plan = MagicMock()
            mock_plan.hypotheses = []
            mock_reasoning_engine.analyze_query.return_value = mock_plan

            mock_hop_result = MagicMock()
            mock_hop_result.evidence = []
            mock_hop_result.hypothesis_results = []
            mock_hop_result.synthesis = MagicMock()
            mock_hop_result.synthesis.confidence = 0.75
            mock_hop_result.synthesis.key_findings = []
            mock_reasoning_engine.execute_research_hop.return_value = mock_hop_result

            mock_synthesis = MagicMock()
            mock_synthesis.key_findings = []
            mock_synthesis.remaining_gaps = []
            mock_synthesis.recommendations = []
            mock_reasoning_engine.sequential.synthesize_findings.return_value = mock_synthesis

            mock_document = MagicMock()
            mock_document.file_path = Path("research/test.md")
            orchestrator.document_store.create_document.return_value = mock_document

            # Track progress events
            events = []
            def track_event(event):
                events.append(event)

            orchestrator.progress_tracker.register_callback(track_event)

            # Execute research
            await orchestrator.execute_research(
                query="Test query",
                depth="quick",
                max_cost=None
            )

            # Verify progress events
            assert len(events) > 0
            event_types = [e.event_type for e in events]
            assert "started" in event_types or event_types[0].value == "started"
            assert "completed" in event_types or event_types[-1].value == "completed"


class TestDocumentFormatting:
    """Test document formatting."""

    def test_format_research_findings(self, orchestrator):
        """Test markdown formatting of research results."""
        from aris.mcp.reasoning_schemas import (
            ReasoningContext,
            HopResult,
            Hypothesis,
            HypothesisResult,
            Synthesis,
        )

        # Create test data
        session = ResearchSession(
            query=ResearchQuery(query_text="Test query", depth=ResearchDepth.STANDARD),
            budget_target=0.50,
            total_cost=0.25,
        )

        hypothesis = Hypothesis(
            statement="Test hypothesis",
            confidence_prior=0.5,
            evidence_required=["test"]
        )

        hyp_result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.8,
            supporting_evidence=[{"source": "evidence1", "text": "Supporting text"}],
            contradicting_evidence=[],
            conclusion="Hypothesis supported by evidence"
        )

        synthesis = Synthesis(
            confidence=0.75,
            key_findings=["Finding 1", "Finding 2"],
            gaps_remaining=[],
            recommendations=[]
        )

        hop_result = HopResult(
            hop_number=1,
            hypothesis_results=[hyp_result],
            evidence=["source1", "source2"],
            synthesis=synthesis
        )

        context = ReasoningContext(query="Test query")
        context.add_hop_result(hop_result)
        context.final_synthesis = synthesis

        # Format document
        content = orchestrator._format_research_findings(context, "Test query", session)

        # Verify formatting
        assert "# Research: Test query" in content
        assert "Confidence Score" in content
        assert "Sources Analyzed" in content
        assert "Finding 1" in content
        assert "Finding 2" in content
        assert "Test hypothesis" in content

    def test_format_research_findings_with_gaps(self, orchestrator):
        """Test formatting includes gaps and recommendations."""
        from aris.mcp.reasoning_schemas import ReasoningContext, Synthesis

        query = "Test query"  # Must be ≥5 chars

        session = ResearchSession(
            query=ResearchQuery(query_text=query, depth=ResearchDepth.QUICK),
            budget_target=0.20,
        )

        synthesis = Synthesis(
            confidence=0.60,
            key_findings=["Finding"],
            gaps_remaining=["Gap 1", "Gap 2"],
            recommendations=["Rec 1"]
        )

        context = ReasoningContext(query=query)
        context.final_synthesis = synthesis

        content = orchestrator._format_research_findings(context, query, session)

        assert "Remaining Questions" in content
        assert "Gap 1" in content
        assert "Gap 2" in content
        assert "Recommendations" in content
        assert "Rec 1" in content


class TestAsyncContextManager:
    """Test async context manager support."""

    @pytest.mark.timeout(5)
    @pytest.mark.asyncio
    async def test_async_context_manager(self, orchestrator, mock_reasoning_engine):
        """Test orchestrator works as async context manager."""
        async with orchestrator as orch:
            assert orch is orchestrator

        # Verify reasoning engine was properly entered and exited
        mock_reasoning_engine.__aenter__.assert_called_once()
        mock_reasoning_engine.__aexit__.assert_called_once()
