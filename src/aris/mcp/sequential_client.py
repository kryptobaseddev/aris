"""Sequential Thinking MCP client for structured reasoning."""

import asyncio
import json
import subprocess
import uuid
from typing import Any, Optional

from pydantic import BaseModel

from aris.mcp.reasoning_schemas import (
    Hypothesis,
    HypothesisResult,
    ResearchPlan,
    Synthesis,
)


class MCPMessage(BaseModel):
    """MCP protocol message."""

    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None


class MCPSession:
    """MCP session for stdio communication with Sequential Thinking server."""

    def __init__(self, process: subprocess.Popen):
        """Initialize MCP session with subprocess."""
        self.process = process
        self.id = str(uuid.uuid4())
        self._initialized = False
        self._pending_requests: dict[str, asyncio.Future] = {}

    async def initialize(self) -> dict[str, Any]:
        """Initialize MCP connection."""
        response = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "sampling": {}
            },
            "clientInfo": {
                "name": "aris-research-agent",
                "version": "0.1.0"
            }
        })
        self._initialized = True
        return response

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send request to MCP server and wait for response."""
        request_id = str(uuid.uuid4())

        message = MCPMessage(
            jsonrpc="2.0",
            id=request_id,
            method=method,
            params=params
        )

        # Send to subprocess stdin
        request_json = message.model_dump_json() + "\n"
        self.process.stdin.write(request_json.encode())
        self.process.stdin.flush()

        # Read response from stdout
        response_line = self.process.stdout.readline().decode().strip()
        if not response_line:
            raise RuntimeError("No response from MCP server")

        response = MCPMessage.model_validate_json(response_line)

        if response.error:
            raise RuntimeError(f"MCP error: {response.error}")

        return response.result or {}

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via MCP."""
        return await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

    async def close(self) -> None:
        """Close MCP session."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class SequentialClient:
    """Sequential Thinking MCP client for structured multi-step reasoning."""

    def __init__(self, mcp_path: str = "npx"):
        """Initialize Sequential client.

        Args:
            mcp_path: Path to MCP executable (default: npx)
        """
        self.mcp_path = mcp_path
        self.session: Optional[MCPSession] = None

    async def start_session(self) -> str:
        """Start Sequential MCP session.

        Returns:
            Session ID
        """
        self.session = await self._connect_mcp()
        return self.session.id

    async def _connect_mcp(self) -> MCPSession:
        """Connect to Sequential MCP server via stdio.

        Returns:
            MCPSession instance
        """
        # Start MCP server process
        process = subprocess.Popen(
            [self.mcp_path, "@modelcontextprotocol/server-sequential-thinking"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # Line buffered
        )

        # Create and initialize session
        session = MCPSession(process)
        await session.initialize()
        return session

    async def plan_research(self, query: str, context: Optional[str] = None) -> ResearchPlan:
        """Create structured research plan from query.

        Args:
            query: Research question
            context: Optional additional context

        Returns:
            ResearchPlan with topics, hypotheses, and success criteria
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")

        prompt = f"""Analyze this research query and create a structured plan:

Query: {query}
{f'Context: {context}' if context else ''}

Provide a research plan with:
1. Key topics to research (3-5 main areas)
2. Potential hypotheses to test (2-4 testable statements)
3. Information gaps to fill (what we need to discover)
4. Success criteria (how to know research is complete)
5. Estimated number of research hops needed (1-5)

Format as JSON with fields: topics (list), hypotheses (list), information_gaps (list), success_criteria (list), estimated_hops (int)
"""

        result = await self.session.call_tool("sequential-thinking", {
            "prompt": prompt
        })

        # Parse LLM response
        return self._parse_research_plan(query, result)

    def _parse_research_plan(self, query: str, result: dict[str, Any]) -> ResearchPlan:
        """Parse LLM response into ResearchPlan."""
        # Extract content from MCP response
        content = result.get("content", [{}])[0].get("text", "{}")

        try:
            # Try to parse as JSON
            data = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: extract structured info from text
            data = {
                "topics": ["General research topic"],
                "hypotheses": ["Initial hypothesis"],
                "information_gaps": ["Information to discover"],
                "success_criteria": ["Research objectives met"],
                "estimated_hops": 3
            }

        return ResearchPlan(
            query=query,
            topics=data.get("topics", []),
            hypotheses=data.get("hypotheses", []),
            information_gaps=data.get("information_gaps", []),
            success_criteria=data.get("success_criteria", []),
            estimated_hops=data.get("estimated_hops", 3)
        )

    async def generate_hypotheses(
        self,
        context: str,
        existing_evidence: Optional[list[dict]] = None
    ) -> list[Hypothesis]:
        """Generate testable hypotheses based on context.

        Args:
            context: Research context or topic description
            existing_evidence: Optional evidence from previous research

        Returns:
            List of Hypothesis objects
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")

        evidence_text = ""
        if existing_evidence:
            evidence_text = "\n\nExisting evidence:\n" + "\n".join(
                f"- {e.get('title', 'Source')}: {e.get('summary', 'No summary')}"
                for e in existing_evidence[:5]  # Limit to 5 sources
            )

        prompt = f"""Generate testable hypotheses for this research context:

Context: {context}{evidence_text}

Generate 2-4 testable hypotheses that:
1. Are specific and falsifiable
2. Can be tested with available evidence
3. Address key aspects of the research question
4. Have clear test criteria

For each hypothesis provide:
- statement: Clear hypothesis statement
- confidence_prior: Initial confidence (0.0-1.0) before testing
- evidence_required: Types of evidence needed to test
- test_method: How to test this hypothesis

Format as JSON array of hypothesis objects.
"""

        result = await self.session.call_tool("sequential-thinking", {
            "prompt": prompt
        })

        return self._parse_hypotheses(result)

    def _parse_hypotheses(self, result: dict[str, Any]) -> list[Hypothesis]:
        """Parse LLM response into list of Hypothesis objects."""
        content = result.get("content", [{}])[0].get("text", "[]")

        try:
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
        except json.JSONDecodeError:
            # Fallback
            data = [{
                "statement": "Default hypothesis based on context",
                "confidence_prior": 0.5,
                "evidence_required": ["supporting evidence"],
                "test_method": "evidence analysis"
            }]

        hypotheses = []
        for h_data in data:
            hypotheses.append(Hypothesis(
                statement=h_data.get("statement", "Unknown hypothesis"),
                confidence_prior=float(h_data.get("confidence_prior", 0.5)),
                evidence_required=h_data.get("evidence_required", []),
                test_method=h_data.get("test_method", "evidence analysis")
            ))

        return hypotheses

    async def test_hypothesis(
        self,
        hypothesis: Hypothesis,
        evidence: list[dict[str, Any]]
    ) -> HypothesisResult:
        """Test hypothesis against available evidence.

        Args:
            hypothesis: Hypothesis to test
            evidence: List of evidence documents with title, summary, url

        Returns:
            HypothesisResult with updated confidence and supporting/contradicting evidence
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")

        evidence_text = "\n\n".join(
            f"Source: {e.get('title', 'Unknown')}\n"
            f"URL: {e.get('url', 'N/A')}\n"
            f"Summary: {e.get('summary', e.get('content', 'No content'))}"
            for e in evidence[:10]  # Limit to 10 sources
        )

        prompt = f"""Test this hypothesis against available evidence:

Hypothesis: {hypothesis.statement}
Prior confidence: {hypothesis.confidence_prior}
Test method: {hypothesis.test_method}

Evidence:
{evidence_text}

Analyze the evidence and provide:
1. confidence_posterior: Updated confidence (0.0-1.0) after testing
2. supporting_evidence: List of evidence IDs/titles that support hypothesis
3. contradicting_evidence: List of evidence IDs/titles that contradict hypothesis
4. conclusion: Brief conclusion about hypothesis validity

Format as JSON with these fields.
"""

        result = await self.session.call_tool("sequential-thinking", {
            "prompt": prompt
        })

        return self._parse_hypothesis_result(hypothesis, evidence, result)

    def _parse_hypothesis_result(
        self,
        hypothesis: Hypothesis,
        evidence: list[dict],
        result: dict[str, Any]
    ) -> HypothesisResult:
        """Parse LLM response into HypothesisResult."""
        content = result.get("content", [{}])[0].get("text", "{}")

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {
                "confidence_posterior": hypothesis.confidence_prior,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "conclusion": "Unable to test hypothesis with available evidence"
            }

        # Match evidence by title
        evidence_by_title = {e.get("title", ""): e for e in evidence}

        supporting = []
        for title in data.get("supporting_evidence", []):
            if title in evidence_by_title:
                supporting.append(evidence_by_title[title])

        contradicting = []
        for title in data.get("contradicting_evidence", []):
            if title in evidence_by_title:
                contradicting.append(evidence_by_title[title])

        return HypothesisResult(
            hypothesis=hypothesis,
            confidence_posterior=float(data.get("confidence_posterior", hypothesis.confidence_prior)),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            conclusion=data.get("conclusion", "")
        )

    async def synthesize_findings(
        self,
        results: list[HypothesisResult],
        original_query: Optional[str] = None
    ) -> Synthesis:
        """Synthesize multiple hypothesis results into coherent findings.

        Args:
            results: List of HypothesisResult objects
            original_query: Optional original research query for context

        Returns:
            Synthesis with key findings, overall confidence, and recommendations
        """
        if not self.session:
            raise RuntimeError("Session not started. Call start_session() first.")

        results_text = "\n\n".join(
            f"Hypothesis: {r.hypothesis.statement}\n"
            f"Prior confidence: {r.hypothesis.confidence_prior}\n"
            f"Posterior confidence: {r.confidence_posterior}\n"
            f"Supporting evidence: {len(r.supporting_evidence)} sources\n"
            f"Contradicting evidence: {len(r.contradicting_evidence)} sources\n"
            f"Conclusion: {r.conclusion}"
            for r in results
        )

        prompt = f"""Synthesize these hypothesis test results into coherent research findings:

{f'Original query: {original_query}' if original_query else ''}

Results:
{results_text}

Provide synthesis with:
1. key_findings: 3-5 main discoveries from the research (list)
2. confidence: Overall confidence in findings (0.0-1.0)
3. gaps_remaining: Important questions still unanswered (list)
4. recommendations: Next steps or actions to take (list)

Format as JSON with these fields.
"""

        result = await self.session.call_tool("sequential-thinking", {
            "prompt": prompt
        })

        return self._parse_synthesis(results, result)

    def _parse_synthesis(
        self,
        results: list[HypothesisResult],
        result: dict[str, Any]
    ) -> Synthesis:
        """Parse LLM response into Synthesis."""
        content = result.get("content", [{}])[0].get("text", "{}")

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {
                "key_findings": ["Research completed with mixed results"],
                "confidence": self._calculate_overall_confidence(results),
                "gaps_remaining": ["Further research needed"],
                "recommendations": ["Continue investigation"]
            }

        return Synthesis(
            key_findings=data.get("key_findings", []),
            confidence=float(data.get("confidence", self._calculate_overall_confidence(results))),
            gaps_remaining=data.get("gaps_remaining", []),
            recommendations=data.get("recommendations", [])
        )

    def _calculate_overall_confidence(self, results: list[HypothesisResult]) -> float:
        """Calculate overall confidence from hypothesis results."""
        if not results:
            return 0.0

        # Weight by evidence strength
        total_weighted = 0.0
        total_weight = 0.0
        for result in results:
            evidence_count = len(result.supporting_evidence)
            weight = min(evidence_count / 3.0, 1.0)  # Cap at 3 sources
            total_weighted += result.confidence_posterior * weight
            total_weight += weight

        # Avoid division by zero if all weights are 0
        if total_weight == 0.0:
            # Fall back to simple average if no evidence
            return sum(r.confidence_posterior for r in results) / len(results)

        return total_weighted / total_weight

    async def close(self) -> None:
        """Close Sequential MCP session."""
        if self.session:
            await self.session.close()
            self.session = None
