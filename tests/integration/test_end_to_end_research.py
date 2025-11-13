"""End-to-end integration tests for complete research workflow.

Tests the full research pipeline from query to document storage.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aris.core.research_orchestrator import ResearchOrchestrator
from aris.models.config import ArisConfig


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration with temporary directories."""
    research_dir = tmp_path / "research"
    research_dir.mkdir()

    db_path = tmp_path / "test.db"

    return ArisConfig(
        research_dir=str(research_dir),
        database_path=str(db_path),
        tavily_api_key="test_key",
        sequential_mcp_path="npx",
        max_hops=2,
        confidence_target=0.70,
    )


@pytest.fixture
def mock_tavily_client():
    """Create mock Tavily client."""
    client = MagicMock()
    client.search = AsyncMock(return_value={
        "results": [
            {"title": "Result 1", "url": "http://test1.com", "content": "Content 1"},
            {"title": "Result 2", "url": "http://test2.com", "content": "Content 2"},
        ]
    })
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def mock_sequential_client():
    """Create mock Sequential client."""
    client = MagicMock()

    # Mock analyze_query
    mock_plan = MagicMock()
    mock_plan.topics = ["AI", "ML"]
    mock_plan.hypotheses = [
        MagicMock(statement="Hypothesis 1", prior_confidence=0.5, evidence_required=["test"]),
        MagicMock(statement="Hypothesis 2", prior_confidence=0.6, evidence_required=["test"]),
    ]
    mock_plan.knowledge_gaps = ["Gap 1"]
    mock_plan.success_criteria = ["Criteria 1"]
    client.analyze_query = AsyncMock(return_value=mock_plan)

    # Mock generate_hypotheses
    client.generate_hypotheses = AsyncMock(return_value=[
        MagicMock(statement="Test hypothesis", prior_confidence=0.5, evidence_required=[])
    ])

    # Mock test_hypothesis
    mock_hyp_result = MagicMock()
    mock_hyp_result.supported = True
    mock_hyp_result.posterior_confidence = 0.75
    mock_hyp_result.supporting_evidence = ["Evidence 1"]
    mock_hyp_result.contradicting_evidence = []
    client.test_hypothesis = AsyncMock(return_value=mock_hyp_result)

    # Mock synthesize_findings
    mock_synthesis = MagicMock()
    mock_synthesis.confidence = 0.75
    mock_synthesis.key_findings = ["Finding 1", "Finding 2"]
    mock_synthesis.remaining_gaps = []
    mock_synthesis.recommendations = ["Recommendation 1"]
    client.synthesize_findings = AsyncMock(return_value=mock_synthesis)

    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


class TestEndToEndResearch:
    """Test complete research workflow from query to document."""

    @pytest.mark.asyncio
    async def test_complete_workflow(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test complete research workflow with all components."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute research
            result = await orchestrator.execute_research(
                query="What is machine learning?",
                depth="quick",
                max_cost=0.50
            )

            # Verify result
            assert result.success is True
            assert result.query_text == "What is machine learning?"
            assert result.hops_executed >= 1
            assert result.confidence > 0.0
            assert result.document_path is not None

            # Verify MCP clients were called
            mock_tavily_client.search.assert_called()
            mock_sequential_client.analyze_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_hop_workflow(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test multi-hop research workflow."""
        # Setup for multiple hops (low confidence initially)
        synthesis_low = MagicMock()
        synthesis_low.confidence = 0.50
        synthesis_low.key_findings = ["Initial finding"]
        synthesis_low.remaining_gaps = ["Gap to fill"]
        synthesis_low.recommendations = []

        synthesis_high = MagicMock()
        synthesis_high.confidence = 0.80
        synthesis_high.key_findings = ["Complete finding"]
        synthesis_high.remaining_gaps = []
        synthesis_high.recommendations = []

        # First hop low confidence, second hop high
        mock_sequential_client.synthesize_findings = AsyncMock(
            side_effect=[synthesis_low, synthesis_high]
        )

        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute with standard depth (3 hops max)
            result = await orchestrator.execute_research(
                query="Complex research question",
                depth="standard",
                max_cost=1.00
            )

            # Should execute 2 hops (stop at high confidence)
            assert result.hops_executed == 2
            assert result.confidence >= 0.70

    @pytest.mark.asyncio
    async def test_progress_tracking_integration(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test progress tracking throughout workflow."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Track progress events
            events = []
            def track_event(event):
                events.append(event.event_type)

            orchestrator.progress_tracker.register_callback(track_event)

            # Execute research
            await orchestrator.execute_research(
                query="Test query",
                depth="quick",
                max_cost=0.50
            )

            # Verify progress events
            assert len(events) > 0
            # Should have started and completed at minimum
            event_values = [e.value if hasattr(e, 'value') else str(e) for e in events]
            assert any("start" in str(e).lower() for e in event_values)
            assert any("complete" in str(e).lower() for e in event_values)

    @pytest.mark.asyncio
    async def test_document_creation_integration(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test document is actually created with proper content."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Mock document store to verify document content
            mock_document = MagicMock()
            mock_document.file_path = Path(test_config.research_dir) / "test.md"
            orchestrator.document_store.create_document = MagicMock(return_value=mock_document)

            # Execute research
            result = await orchestrator.execute_research(
                query="Test research query",
                depth="quick",
                max_cost=0.50
            )

            # Verify document was created
            orchestrator.document_store.create_document.assert_called_once()

            # Check arguments passed to create_document
            call_args = orchestrator.document_store.create_document.call_args
            assert call_args.kwargs["content"] is not None
            assert "Test research query" in call_args.kwargs["content"]
            assert call_args.kwargs["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_error_recovery(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test error handling and recovery."""
        # Make Tavily search fail
        mock_tavily_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Should handle error gracefully
            from aris.core.research_orchestrator import ResearchOrchestratorError

            with pytest.raises(ResearchOrchestratorError):
                await orchestrator.execute_research(
                    query="Test query",
                    depth="quick",
                    max_cost=0.50
                )

            # Progress tracker should have error event
            assert orchestrator.progress_tracker.has_errors

    @pytest.mark.asyncio
    async def test_budget_enforcement(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test budget limits are enforced."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            # Execute with very low budget
            result = await orchestrator.execute_research(
                query="Test query",
                depth="standard",
                max_cost=0.01  # Very low
            )

            # Should warn about budget
            assert len(result.warnings) > 0
            # May be over budget or warn about approaching limit
            budget_mentioned = any("budget" in w.lower() for w in result.warnings)
            assert budget_mentioned or not result.within_budget


class TestReasoningEngineIntegration:
    """Test integration with ReasoningEngine."""

    @pytest.mark.asyncio
    async def test_reasoning_engine_hypothesis_workflow(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test hypothesis generation and testing workflow."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            result = await orchestrator.execute_research(
                query="Test scientific question",
                depth="quick",
                max_cost=0.50
            )

            # Verify hypothesis-driven workflow
            mock_sequential_client.analyze_query.assert_called()
            mock_sequential_client.synthesize_findings.assert_called()

    @pytest.mark.asyncio
    async def test_confidence_based_early_stopping(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test early stopping when confidence target reached."""
        # High confidence on first hop
        high_conf_synthesis = MagicMock()
        high_conf_synthesis.confidence = 0.85
        high_conf_synthesis.key_findings = ["Complete answer"]
        high_conf_synthesis.remaining_gaps = []
        high_conf_synthesis.recommendations = []

        mock_sequential_client.synthesize_findings = AsyncMock(return_value=high_conf_synthesis)

        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            orchestrator = ResearchOrchestrator(test_config)

            result = await orchestrator.execute_research(
                query="Simple question",
                depth="deep",  # Allows 5 hops
                max_cost=2.00
            )

            # Should stop after 1 hop
            assert result.hops_executed == 1
            assert result.confidence >= 0.70


class TestAsyncContextManager:
    """Test orchestrator as async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_usage(
        self, test_config, mock_tavily_client, mock_sequential_client
    ):
        """Test using orchestrator as async context manager."""
        with patch("aris.mcp.tavily_client.TavilyClient", return_value=mock_tavily_client), \
             patch("aris.mcp.sequential_client.SequentialClient", return_value=mock_sequential_client), \
             patch("aris.core.research_orchestrator.DatabaseManager"), \
             patch("aris.storage.git_manager.GitManager"):

            async with ResearchOrchestrator(test_config) as orchestrator:
                result = await orchestrator.execute_research(
                    query="Test query",
                    depth="quick",
                    max_cost=0.50
                )

                assert result.success is True

            # Reasoning engine should be properly cleaned up
            # (verified by context manager not raising exceptions)
