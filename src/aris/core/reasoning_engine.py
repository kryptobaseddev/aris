"""High-level reasoning engine integrating Sequential Thinking and Tavily."""

from typing import Optional

from aris.mcp.reasoning_schemas import (
    HopResult,
    Hypothesis,
    HypothesisResult,
    ReasoningContext,
    ResearchPlan,
    Synthesis,
)
from aris.mcp.sequential_client import SequentialClient
from aris.mcp.tavily_client import TavilyClient
from aris.models.config import ArisConfig


class ReasoningEngine:
    """High-level reasoning engine for research workflows.

    Coordinates between Sequential Thinking (reasoning/planning) and
    Tavily (evidence gathering) to execute structured research.

    Example:
        from aris.core.config import ConfigManager
        from aris.core.reasoning_engine import ReasoningEngine

        config = ConfigManager.get_instance().get_config()
        engine = ReasoningEngine(config)

        # Analyze query and create plan
        plan = await engine.analyze_query("How do LLMs reason?")

        # Execute research hop
        hop_result = await engine.execute_research_hop(plan, hop_number=1)

        # Check confidence
        print(f"Confidence: {hop_result.synthesis.confidence:.2f}")

        # Continue until confidence threshold met
        if hop_result.synthesis.needs_more_research:
            hop_result_2 = await engine.execute_research_hop(plan, hop_number=2)
    """

    def __init__(self, config: ArisConfig):
        """Initialize reasoning engine.

        Args:
            config: ARIS configuration
        """
        self.config = config
        self.sequential = SequentialClient(config.sequential_mcp_path)
        self.tavily = TavilyClient(
            api_key=config.tavily_api_key or "",
            timeout=config.request_timeout_seconds,
        )
        self._context: Optional[ReasoningContext] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.sequential.start_session()
        await self.tavily.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.sequential.close()
        await self.tavily.__aexit__(exc_type, exc_val, exc_tb)

    async def analyze_query(
        self, query: str, context: Optional[str] = None
    ) -> ResearchPlan:
        """Analyze query and create structured research plan.

        Args:
            query: Research question
            context: Optional additional context

        Returns:
            ResearchPlan with topics, hypotheses, and success criteria
        """
        # Ensure session started
        if not self.sequential.session:
            await self.sequential.start_session()

        # Create research plan
        plan = await self.sequential.plan_research(query, context)

        # Initialize reasoning context
        self._context = ReasoningContext(query=query, plan=plan)

        return plan

    async def execute_research_hop(
        self,
        plan: ResearchPlan,
        hop_number: int,
        existing_evidence: Optional[list[dict]] = None,
    ) -> HopResult:
        """Execute single research iteration (hop).

        Args:
            plan: Research plan from analyze_query
            hop_number: Current hop number (1-indexed)
            existing_evidence: Optional evidence from previous hops

        Returns:
            HopResult with hypotheses, evidence, results, and synthesis
        """
        # Generate hypotheses for this hop
        context_text = self._build_context_text(plan)
        hypotheses = await self.sequential.generate_hypotheses(
            context=context_text, existing_evidence=existing_evidence or []
        )

        # Gather evidence via Tavily
        evidence = await self._gather_evidence(plan.topics)

        # Test hypotheses against evidence
        hypothesis_results = []
        for hypothesis in hypotheses:
            result = await self.sequential.test_hypothesis(hypothesis, evidence)
            hypothesis_results.append(result)

        # Synthesize findings
        synthesis = await self.sequential.synthesize_findings(
            hypothesis_results, original_query=plan.query
        )

        # Create hop result
        hop_result = HopResult(
            hop_number=hop_number,
            hypotheses=hypotheses,
            evidence=evidence,
            results=hypothesis_results,
            synthesis=synthesis,
        )

        # Update context if available
        if self._context:
            self._context.add_hop_result(hop_result)

        return hop_result

    async def execute_multi_hop_research(
        self, query: str, max_hops: Optional[int] = None
    ) -> ReasoningContext:
        """Execute complete multi-hop research workflow.

        Args:
            query: Research question
            max_hops: Maximum hops (default from config)

        Returns:
            ReasoningContext with all hops and final synthesis
        """
        max_hops = max_hops or self.config.max_hops
        confidence_target = self.config.confidence_target

        # Analyze query
        plan = await self.analyze_query(query)

        # Execute hops until confidence target or max hops
        for hop_num in range(1, max_hops + 1):
            # Get existing evidence
            existing_evidence = (
                self._context.cumulative_evidence if self._context else []
            )

            # Execute hop
            hop_result = await self.execute_research_hop(
                plan, hop_num, existing_evidence
            )

            # Check if we've reached confidence target
            if (
                hop_result.synthesis
                and hop_result.synthesis.confidence >= confidence_target
            ):
                break

            # Check for early stop
            if (
                hop_result.synthesis
                and hop_result.synthesis.confidence >= self.config.early_stop_confidence
            ):
                break

        # Generate final synthesis across all hops
        if self._context and len(self._context.hops) > 1:
            # Combine all hypothesis results
            all_results = []
            for hop in self._context.hops:
                all_results.extend(hop.results)

            # Create final synthesis
            final_synthesis = await self.sequential.synthesize_findings(
                all_results, original_query=query
            )
            self._context.final_synthesis = final_synthesis

        return self._context

    def _build_context_text(self, plan: ResearchPlan) -> str:
        """Build context text for hypothesis generation.

        Args:
            plan: Research plan

        Returns:
            Context text describing research scope
        """
        topics_text = ", ".join(plan.topics)
        return f"Research topics: {topics_text}\nQuery: {plan.query}"

    async def _gather_evidence(
        self, topics: list[str], max_results_per_topic: int = 3
    ) -> list[dict]:
        """Gather evidence from Tavily for research topics.

        Args:
            topics: List of research topics
            max_results_per_topic: Results per topic (default 3)

        Returns:
            List of evidence documents with title, url, summary
        """
        evidence = []

        for topic in topics:
            try:
                results = await self.tavily.search(
                    query=topic,
                    max_results=max_results_per_topic,
                    search_depth="advanced",
                )

                # Convert Tavily results to evidence format
                for result in results:
                    evidence.append(
                        {
                            "title": result.get("title", "Untitled"),
                            "url": result.get("url", ""),
                            "summary": result.get("content", ""),
                            "score": result.get("score", 0.0),
                        }
                    )
            except Exception as e:
                # Log error but continue with other topics
                print(f"Warning: Failed to gather evidence for '{topic}': {e}")
                continue

        return evidence

    async def refine_hypothesis(
        self, hypothesis: Hypothesis, additional_evidence: list[dict]
    ) -> HypothesisResult:
        """Refine hypothesis with additional evidence.

        Args:
            hypothesis: Hypothesis to refine
            additional_evidence: New evidence to test against

        Returns:
            Updated HypothesisResult
        """
        return await self.sequential.test_hypothesis(hypothesis, additional_evidence)

    async def generate_follow_up_queries(
        self, synthesis: Synthesis
    ) -> list[str]:
        """Generate follow-up queries based on synthesis gaps.

        Args:
            synthesis: Current synthesis with gaps

        Returns:
            List of follow-up query strings
        """
        if not synthesis.gaps_remaining:
            return []

        # Convert gaps to queries
        queries = []
        for gap in synthesis.gaps_remaining:
            # Simple heuristic: gaps are already question-like
            if not gap.endswith("?"):
                gap += "?"
            queries.append(gap)

        return queries

    def get_cost_summary(self) -> dict:
        """Get cost summary from Tavily operations.

        Returns:
            Cost summary dictionary
        """
        return self.tavily.cost_tracker.get_summary()

    def get_context(self) -> Optional[ReasoningContext]:
        """Get current reasoning context.

        Returns:
            Current ReasoningContext or None
        """
        return self._context

    async def close(self) -> None:
        """Close reasoning engine and cleanup resources."""
        await self.sequential.close()
        await self.tavily.close()
