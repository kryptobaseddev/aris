"""Unit tests for Sequential Thinking MCP client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aris.mcp.reasoning_schemas import Hypothesis, HypothesisResult, ResearchPlan, Synthesis
from aris.mcp.sequential_client import MCPSession, SequentialClient


class TestMCPSession:
    """Tests for MCPSession."""

    @pytest.fixture
    def mock_process(self):
        """Create mock subprocess."""
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdout = MagicMock()
        process.stderr = MagicMock()
        return process

    @pytest.mark.asyncio
    async def test_initialize(self, mock_process):
        """Test MCP session initialization."""
        # Mock response
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"protocolVersion": "2024-11-05"}
        }
        mock_process.stdout.readline.return_value = (
            json.dumps(response).encode() + b"\n"
        )

        session = MCPSession(mock_process)
        result = await session.initialize()

        assert result == {"protocolVersion": "2024-11-05"}
        assert session._initialized

    @pytest.mark.asyncio
    async def test_call_tool(self, mock_process):
        """Test calling a tool via MCP."""
        # Mock response
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "result": {"content": [{"text": "result"}]}
        }
        mock_process.stdout.readline.return_value = (
            json.dumps(response).encode() + b"\n"
        )

        session = MCPSession(mock_process)
        session._initialized = True

        result = await session.call_tool("sequential-thinking", {"prompt": "test"})

        assert result["content"][0]["text"] == "result"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_process):
        """Test MCP error handling."""
        # Mock error response
        response = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "error": {"code": -32600, "message": "Invalid request"}
        }
        mock_process.stdout.readline.return_value = (
            json.dumps(response).encode() + b"\n"
        )

        session = MCPSession(mock_process)

        with pytest.raises(RuntimeError, match="MCP error"):
            await session._send_request("test", {})


class TestSequentialClient:
    """Tests for SequentialClient."""

    @pytest.fixture
    def client(self):
        """Create Sequential client."""
        return SequentialClient(mcp_path="npx")

    @pytest.fixture
    def mock_session(self):
        """Create mock MCP session."""
        session = AsyncMock(spec=MCPSession)
        session.id = "test-session-id"
        return session

    @pytest.mark.asyncio
    async def test_start_session(self, client):
        """Test starting MCP session."""
        with patch.object(client, "_connect_mcp", new_callable=AsyncMock) as mock_connect:
            mock_session = AsyncMock()
            mock_session.id = "session-123"
            mock_connect.return_value = mock_session

            session_id = await client.start_session()

            assert session_id == "session-123"
            assert client.session == mock_session
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_plan_research(self, client, mock_session):
        """Test creating research plan."""
        client.session = mock_session

        # Mock Sequential response
        mock_session.call_tool.return_value = {
            "content": [{
                "text": json.dumps({
                    "topics": ["AI reasoning", "LLM architectures"],
                    "hypotheses": ["LLMs use attention", "Transformers enable reasoning"],
                    "information_gaps": ["How attention works"],
                    "success_criteria": ["Understand mechanisms"],
                    "estimated_hops": 3
                })
            }]
        }

        plan = await client.plan_research("How do LLMs reason?")

        assert isinstance(plan, ResearchPlan)
        assert plan.query == "How do LLMs reason?"
        assert len(plan.topics) == 2
        assert len(plan.hypotheses) == 2
        assert plan.estimated_hops == 3

    @pytest.mark.asyncio
    async def test_plan_research_fallback(self, client, mock_session):
        """Test research plan fallback parsing."""
        client.session = mock_session

        # Mock invalid JSON response
        mock_session.call_tool.return_value = {
            "content": [{"text": "Not valid JSON"}]
        }

        plan = await client.plan_research("Test query")

        # Should return default plan
        assert isinstance(plan, ResearchPlan)
        assert plan.query == "Test query"
        assert len(plan.topics) > 0
        assert plan.estimated_hops == 3

    @pytest.mark.asyncio
    async def test_generate_hypotheses(self, client, mock_session):
        """Test hypothesis generation."""
        client.session = mock_session

        # Mock Sequential response
        mock_session.call_tool.return_value = {
            "content": [{
                "text": json.dumps([
                    {
                        "statement": "LLMs use attention mechanisms",
                        "confidence_prior": 0.7,
                        "evidence_required": ["papers", "experiments"],
                        "test_method": "literature review"
                    },
                    {
                        "statement": "Reasoning requires scale",
                        "confidence_prior": 0.6,
                        "evidence_required": ["benchmarks"],
                        "test_method": "performance analysis"
                    }
                ])
            }]
        }

        hypotheses = await client.generate_hypotheses("AI reasoning context")

        assert len(hypotheses) == 2
        assert isinstance(hypotheses[0], Hypothesis)
        assert hypotheses[0].statement == "LLMs use attention mechanisms"
        assert hypotheses[0].confidence_prior == 0.7

    @pytest.mark.asyncio
    async def test_test_hypothesis(self, client, mock_session):
        """Test hypothesis testing."""
        client.session = mock_session

        hypothesis = Hypothesis(
            statement="Test hypothesis",
            confidence_prior=0.5,
            evidence_required=["evidence"],
            test_method="analysis"
        )

        evidence = [
            {"title": "Source 1", "url": "http://example.com", "summary": "Supporting"},
            {"title": "Source 2", "url": "http://example.org", "summary": "Contradicting"}
        ]

        # Mock Sequential response
        mock_session.call_tool.return_value = {
            "content": [{
                "text": json.dumps({
                    "confidence_posterior": 0.7,
                    "supporting_evidence": ["Source 1"],
                    "contradicting_evidence": ["Source 2"],
                    "conclusion": "Hypothesis partially supported"
                })
            }]
        }

        result = await client.test_hypothesis(hypothesis, evidence)

        assert isinstance(result, HypothesisResult)
        assert result.hypothesis == hypothesis
        assert result.confidence_posterior == 0.7
        assert len(result.supporting_evidence) == 1
        assert len(result.contradicting_evidence) == 1
        assert result.conclusion == "Hypothesis partially supported"

    @pytest.mark.asyncio
    async def test_synthesize_findings(self, client, mock_session):
        """Test findings synthesis."""
        client.session = mock_session

        # Create hypothesis results
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )
        results = [
            HypothesisResult(
                hypothesis=hypothesis,
                confidence_posterior=0.8,
                supporting_evidence=[{"title": "Source"}],
                contradicting_evidence=[],
                conclusion="Supported"
            )
        ]

        # Mock Sequential response
        mock_session.call_tool.return_value = {
            "content": [{
                "text": json.dumps({
                    "key_findings": ["Finding 1", "Finding 2"],
                    "confidence": 0.75,
                    "gaps_remaining": ["Gap 1"],
                    "recommendations": ["Recommendation 1"]
                })
            }]
        }

        synthesis = await client.synthesize_findings(results, original_query="Test query")

        assert isinstance(synthesis, Synthesis)
        assert len(synthesis.key_findings) == 2
        assert synthesis.confidence == 0.75
        assert len(synthesis.gaps_remaining) == 1
        assert len(synthesis.recommendations) == 1

    @pytest.mark.asyncio
    async def test_calculate_overall_confidence(self, client):
        """Test confidence calculation."""
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )

        results = [
            HypothesisResult(
                hypothesis=hypothesis,
                confidence_posterior=0.8,
                supporting_evidence=[{"title": "1"}, {"title": "2"}, {"title": "3"}],
                contradicting_evidence=[],
                conclusion="Strong support"
            ),
            HypothesisResult(
                hypothesis=hypothesis,
                confidence_posterior=0.6,
                supporting_evidence=[{"title": "1"}],
                contradicting_evidence=[],
                conclusion="Weak support"
            )
        ]

        confidence = client._calculate_overall_confidence(results)

        # Should weight first result (3 sources) more than second (1 source)
        assert 0.6 < confidence < 0.8
        assert confidence == pytest.approx(0.7, abs=0.1)

    @pytest.mark.asyncio
    async def test_close(self, client, mock_session):
        """Test closing session."""
        client.session = mock_session

        await client.close()

        mock_session.close.assert_called_once()
        assert client.session is None

    @pytest.mark.asyncio
    async def test_session_not_started_error(self, client):
        """Test error when session not started."""
        with pytest.raises(RuntimeError, match="Session not started"):
            await client.plan_research("query")

        with pytest.raises(RuntimeError, match="Session not started"):
            await client.generate_hypotheses("context")

        with pytest.raises(RuntimeError, match="Session not started"):
            hypothesis = Hypothesis(
                statement="test", confidence_prior=0.5, evidence_required=[], test_method="test"
            )
            await client.test_hypothesis(hypothesis, [])


class TestReasoningSchemas:
    """Tests for reasoning schemas."""

    def test_hypothesis_str(self):
        """Test Hypothesis string representation."""
        hypothesis = Hypothesis(
            statement="Test hypothesis",
            confidence_prior=0.75,
            evidence_required=["evidence"],
            test_method="testing"
        )

        assert "Test hypothesis" in str(hypothesis)
        assert "0.75" in str(hypothesis)

    def test_hypothesis_result_confidence_change(self):
        """Test confidence change calculation."""
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )
        result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.8,
            supporting_evidence=[],
            contradicting_evidence=[],
            conclusion="Test"
        )

        assert result.confidence_change == 0.3

    def test_hypothesis_result_evidence_ratio(self):
        """Test evidence ratio calculation."""
        hypothesis = Hypothesis(
            statement="Test", confidence_prior=0.5, evidence_required=[], test_method="test"
        )
        result = HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=0.8,
            supporting_evidence=[{"a": 1}, {"b": 2}, {"c": 3}],
            contradicting_evidence=[{"d": 4}],
            conclusion="Test"
        )

        # 3 supporting / 4 total = 0.75
        assert result.evidence_ratio == 0.75

    def test_synthesis_properties(self):
        """Test Synthesis properties."""
        synthesis = Synthesis(
            key_findings=["Finding 1"],
            confidence=0.75,
            gaps_remaining=["Gap 1"],
            recommendations=["Rec 1"]
        )

        assert synthesis.has_high_confidence
        assert synthesis.has_gaps
        assert not synthesis.needs_more_research  # High confidence overrides gaps

        # Low confidence with gaps
        synthesis_low = Synthesis(
            key_findings=["Finding"],
            confidence=0.5,
            gaps_remaining=["Gap"],
            recommendations=[]
        )

        assert not synthesis_low.has_high_confidence
        assert synthesis_low.has_gaps
        assert synthesis_low.needs_more_research
