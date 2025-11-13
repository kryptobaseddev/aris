"""Integration tests for Sequential + Tavily reasoning workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aris.core.reasoning_engine import ReasoningEngine
from aris.mcp.reasoning_schemas import Hypothesis, HypothesisResult, ResearchPlan, Synthesis
from aris.models.config import ArisConfig


@pytest.fixture
def mock_config():
    """Create mock ARIS config."""
    config = MagicMock(spec=ArisConfig)
    config.sequential_mcp_path = "npx"
    config.tavily_api_key = "test-api-key"
    config.request_timeout_seconds = 30
    config.max_hops = 5
    config.confidence_target = 0.7
    config.early_stop_confidence = 0.85
    return config


@pytest.fixture
def mock_sequential_client():
    """Create mock Sequential client."""
    client = AsyncMock()
    client.session = MagicMock()
    client.session.id = "test-session"
    return client


@pytest.fixture
def mock_tavily_client():
    """Create mock Tavily client."""
    client = AsyncMock()
    client.cost_tracker = MagicMock()
    client.cost_tracker.get_summary.return_value = {
        "total_cost": 0.05,
        "operation_count": 5,
        "by_type": {"search": {"count": 5, "cost": 0.05}}
    }
    return client


class TestReasoningEngine:
    """Integration tests for ReasoningEngine."""

    @pytest.mark.asyncio
    async def test_analyze_query(self, mock_config, mock_sequential_client, mock_tavily_client):
        """Test query analysis creating research plan."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Mock research plan
        expected_plan = ResearchPlan(
            query="How do LLMs reason?",
            topics=["attention mechanisms", "transformer architecture"],
            hypotheses=["Attention enables reasoning", "Scale improves reasoning"],
            information_gaps=["How attention relates to reasoning"],
            success_criteria=["Understand mechanisms"],
            estimated_hops=3
        )
        mock_sequential_client.plan_research.return_value = expected_plan

        plan = await engine.analyze_query("How do LLMs reason?")

        assert plan.query == "How do LLMs reason?"
        assert len(plan.topics) == 2
        assert engine._context is not None
        assert engine._context.plan == plan

    @pytest.mark.asyncio
    async def test_execute_research_hop(self, mock_config, mock_sequential_client, mock_tavily_client):
        """Test executing single research hop."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Setup plan
        plan = ResearchPlan(
            query="Test query",
            topics=["topic1", "topic2"],
            hypotheses=["hyp1"],
            information_gaps=["gap1"],
            success_criteria=["criteria1"],
            estimated_hops=2
        )

        # Mock hypothesis generation
        hypotheses = [
            Hypothesis(
                statement="Test hypothesis",
                confidence_prior=0.5,
                evidence_required=["evidence"],
                test_method="analysis"
            )
        ]
        mock_sequential_client.generate_hypotheses.return_value = hypotheses

        # Mock evidence gathering
        evidence = [
            {"title": "Source 1", "url": "http://example.com", "content": "Content 1", "score": 0.9}
        ]
        mock_tavily_client.search.return_value = evidence

        # Mock hypothesis testing
        hypothesis_result = HypothesisResult(
            hypothesis=hypotheses[0],
            confidence_posterior=0.75,
            supporting_evidence=[evidence[0]],
            contradicting_evidence=[],
            conclusion="Hypothesis supported"
        )
        mock_sequential_client.test_hypothesis.return_value = hypothesis_result

        # Mock synthesis
        synthesis = Synthesis(
            key_findings=["Finding 1"],
            confidence=0.75,
            gaps_remaining=[],
            recommendations=["Next step"]
        )
        mock_sequential_client.synthesize_findings.return_value = synthesis

        # Execute hop
        hop_result = await engine.execute_research_hop(plan, hop_number=1)

        assert hop_result.hop_number == 1
        assert len(hop_result.hypotheses) == 1
        assert len(hop_result.evidence) >= 1  # May have evidence from multiple topics
        assert len(hop_result.results) == 1
        assert hop_result.synthesis == synthesis

    @pytest.mark.asyncio
    async def test_multi_hop_research_early_stop(
        self, mock_config, mock_sequential_client, mock_tavily_client
    ):
        """Test multi-hop research with early stopping on high confidence."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Mock plan
        plan = ResearchPlan(
            query="Test query",
            topics=["topic1"],
            hypotheses=["hyp1"],
            information_gaps=["gap1"],
            success_criteria=["criteria1"],
            estimated_hops=5
        )
        mock_sequential_client.plan_research.return_value = plan

        # Mock hypothesis
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )
        mock_sequential_client.generate_hypotheses.return_value = [hypothesis]

        # Mock evidence
        evidence = [{"title": "Source", "url": "http://example.com", "content": "Content", "score": 0.9}]
        mock_tavily_client.search.return_value = evidence

        # Mock hypothesis result
        result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.9,
            supporting_evidence=[evidence[0]],
            contradicting_evidence=[],
            conclusion="Strong support"
        )
        mock_sequential_client.test_hypothesis.return_value = result

        # Mock high-confidence synthesis (triggers early stop)
        synthesis = Synthesis(
            key_findings=["Finding 1"],
            confidence=0.9,  # Above early_stop_confidence
            gaps_remaining=[],
            recommendations=[]
        )
        mock_sequential_client.synthesize_findings.return_value = synthesis

        # Execute multi-hop research
        context = await engine.execute_multi_hop_research("Test query", max_hops=5)

        # Should stop after 1 hop due to high confidence
        assert len(context.hops) == 1
        assert context.hops[0].synthesis.confidence >= mock_config.early_stop_confidence

    @pytest.mark.asyncio
    async def test_multi_hop_research_max_hops(
        self, mock_config, mock_sequential_client, mock_tavily_client
    ):
        """Test multi-hop research reaching max hops."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Mock plan
        plan = ResearchPlan(
            query="Test query",
            topics=["topic1"],
            hypotheses=["hyp1"],
            information_gaps=["gap1"],
            success_criteria=["criteria1"],
            estimated_hops=3
        )
        mock_sequential_client.plan_research.return_value = plan

        # Mock hypothesis
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )
        mock_sequential_client.generate_hypotheses.return_value = [hypothesis]

        # Mock evidence
        evidence = [{"title": "Source", "url": "http://example.com", "content": "Content", "score": 0.8}]
        mock_tavily_client.search.return_value = evidence

        # Mock hypothesis result
        result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.6,  # Below target
            supporting_evidence=[evidence[0]],
            contradicting_evidence=[],
            conclusion="Moderate support"
        )
        mock_sequential_client.test_hypothesis.return_value = result

        # Mock low-confidence synthesis (doesn't trigger early stop)
        synthesis = Synthesis(
            key_findings=["Finding 1"],
            confidence=0.6,  # Below confidence_target
            gaps_remaining=["Gap 1"],
            recommendations=["Continue"]
        )
        mock_sequential_client.synthesize_findings.return_value = synthesis

        # Execute multi-hop research with max_hops=3
        context = await engine.execute_multi_hop_research("Test query", max_hops=3)

        # Should reach max hops
        assert len(context.hops) == 3
        assert context.overall_confidence < mock_config.confidence_target

    @pytest.mark.asyncio
    async def test_gather_evidence_error_handling(
        self, mock_config, mock_sequential_client, mock_tavily_client
    ):
        """Test evidence gathering with API errors."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Mock search failure for first topic, success for second
        async def mock_search(query, **kwargs):
            if query == "failing_topic":
                raise Exception("API Error")
            return [{"title": "Source", "url": "http://example.com", "content": "Content", "score": 0.8}]

        mock_tavily_client.search = mock_search

        # Should handle error gracefully
        evidence = await engine._gather_evidence(["failing_topic", "working_topic"])

        # Should have evidence from working_topic only
        assert len(evidence) >= 1
        assert evidence[0]["title"] == "Source"

    @pytest.mark.asyncio
    async def test_refine_hypothesis(self, mock_config, mock_sequential_client, mock_tavily_client):
        """Test hypothesis refinement."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        hypothesis = Hypothesis(
            statement="Test hypothesis",
            confidence_prior=0.5,
            evidence_required=["evidence"],
            test_method="analysis"
        )

        additional_evidence = [
            {"title": "New Source", "url": "http://new.com", "content": "New content"}
        ]

        # Mock refined result
        refined_result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.8,
            supporting_evidence=additional_evidence,
            contradicting_evidence=[],
            conclusion="Hypothesis strengthened"
        )
        mock_sequential_client.test_hypothesis.return_value = refined_result

        result = await engine.refine_hypothesis(hypothesis, additional_evidence)

        assert result.confidence_posterior == 0.8
        assert result.confidence_change == 0.3
        mock_sequential_client.test_hypothesis.assert_called_once_with(hypothesis, additional_evidence)

    @pytest.mark.asyncio
    async def test_generate_follow_up_queries(
        self, mock_config, mock_sequential_client, mock_tavily_client
    ):
        """Test generating follow-up queries from gaps."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        synthesis = Synthesis(
            key_findings=["Finding 1"],
            confidence=0.6,
            gaps_remaining=["How does attention work", "What is scale effect"],
            recommendations=["Continue research"]
        )

        queries = await engine.generate_follow_up_queries(synthesis)

        assert len(queries) == 2
        assert all(q.endswith("?") for q in queries)

    @pytest.mark.asyncio
    async def test_cost_tracking(self, mock_config, mock_sequential_client, mock_tavily_client):
        """Test cost tracking throughout research."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        cost_summary = engine.get_cost_summary()

        assert "total_cost" in cost_summary
        assert "operation_count" in cost_summary
        assert cost_summary["total_cost"] == 0.05

    @pytest.mark.asyncio
    async def test_context_management(self, mock_config, mock_sequential_client, mock_tavily_client):
        """Test reasoning context management."""
        engine = ReasoningEngine(mock_config)
        engine.sequential = mock_sequential_client
        engine.tavily = mock_tavily_client

        # Initially no context
        assert engine.get_context() is None

        # After analyze_query, context exists
        plan = ResearchPlan(
            query="Test",
            topics=["topic"],
            hypotheses=["hyp"],
            information_gaps=["gap"],
            success_criteria=["criteria"],
            estimated_hops=2
        )
        mock_sequential_client.plan_research.return_value = plan

        await engine.analyze_query("Test")

        context = engine.get_context()
        assert context is not None
        assert context.query == "Test"
        assert context.plan == plan

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_config):
        """Test ReasoningEngine as async context manager."""
        async with ReasoningEngine(mock_config) as engine:
            assert engine.sequential.session is not None
            # Tavily client should be initialized

        # After exit, resources should be closed
        # (Can't easily test this without actual connections)


class TestReasoningContext:
    """Tests for ReasoningContext tracking."""

    def test_add_hop_result(self):
        """Test adding hop results to context."""
        from aris.mcp.reasoning_schemas import HopResult, ReasoningContext

        context = ReasoningContext(query="Test query")

        hop1 = HopResult(
            hop_number=1,
            hypotheses=[],
            evidence=[{"title": "Source 1"}],
            results=[],
            synthesis=None
        )

        hop2 = HopResult(
            hop_number=2,
            hypotheses=[],
            evidence=[{"title": "Source 2"}],
            results=[],
            synthesis=None
        )

        context.add_hop_result(hop1)
        assert context.current_hop == 1
        assert context.total_evidence == 1

        context.add_hop_result(hop2)
        assert context.current_hop == 2
        assert context.total_evidence == 2

    def test_overall_confidence_calculation(self):
        """Test overall confidence calculation."""
        from aris.mcp.reasoning_schemas import (
            Hypothesis,
            HypothesisResult,
            HopResult,
            ReasoningContext,
            Synthesis,
        )

        context = ReasoningContext(query="Test")

        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )

        # Hop 1: confidence 0.8
        hop1 = HopResult(
            hop_number=1,
            hypotheses=[hypothesis],
            evidence=[],
            results=[
                HypothesisResult(
                    hypothesis=hypothesis,
                    confidence_posterior=0.8,
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    conclusion="Test"
                )
            ],
            synthesis=Synthesis(key_findings=[], confidence=0.8, gaps_remaining=[], recommendations=[])
        )

        # Hop 2: confidence 0.6
        hop2 = HopResult(
            hop_number=2,
            hypotheses=[hypothesis],
            evidence=[],
            results=[
                HypothesisResult(
                    hypothesis=hypothesis,
                    confidence_posterior=0.6,
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    conclusion="Test"
                )
            ],
            synthesis=Synthesis(key_findings=[], confidence=0.6, gaps_remaining=[], recommendations=[])
        )

        context.add_hop_result(hop1)
        context.add_hop_result(hop2)

        # Overall confidence should be average of hop confidences
        assert context.overall_confidence == pytest.approx(0.7, abs=0.01)
