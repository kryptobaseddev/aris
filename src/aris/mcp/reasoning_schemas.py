"""Pydantic schemas for Sequential Thinking reasoning workflows."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Structured research plan with topics and hypotheses."""

    query: str = Field(description="Original research query")
    topics: list[str] = Field(description="Key topics to research", default_factory=list)
    hypotheses: list[str] = Field(description="Potential hypotheses to test", default_factory=list)
    information_gaps: list[str] = Field(description="Information gaps to fill", default_factory=list)
    success_criteria: list[str] = Field(description="Success criteria for research completion", default_factory=list)
    estimated_hops: int = Field(description="Estimated research iterations needed", default=3, ge=1, le=10)

    @classmethod
    def from_llm_response(cls, response: dict[str, Any]) -> "ResearchPlan":
        """Create ResearchPlan from LLM response.

        Args:
            response: LLM response dict

        Returns:
            ResearchPlan instance
        """
        # Extract from structured response or default
        return cls(
            query=response.get("query", ""),
            topics=response.get("topics", []),
            hypotheses=response.get("hypotheses", []),
            information_gaps=response.get("information_gaps", []),
            success_criteria=response.get("success_criteria", []),
            estimated_hops=response.get("estimated_hops", 3)
        )


class Hypothesis(BaseModel):
    """Testable hypothesis with confidence and evidence requirements."""

    statement: str = Field(description="Hypothesis statement")
    confidence_prior: float = Field(
        description="Initial confidence before testing",
        ge=0.0,
        le=1.0,
        default=0.5
    )
    evidence_required: list[str] = Field(
        description="Types of evidence needed to test",
        default_factory=list
    )
    test_method: str = Field(
        description="Method to test hypothesis",
        default="evidence analysis"
    )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.statement} (prior: {self.confidence_prior:.2f})"


class HypothesisResult(BaseModel):
    """Result of hypothesis testing with updated confidence."""

    hypothesis: Hypothesis = Field(description="Original hypothesis")
    confidence_posterior: float = Field(
        description="Updated confidence after testing",
        ge=0.0,
        le=1.0
    )
    supporting_evidence: list[dict[str, Any]] = Field(
        description="Evidence supporting hypothesis",
        default_factory=list
    )
    contradicting_evidence: list[dict[str, Any]] = Field(
        description="Evidence contradicting hypothesis",
        default_factory=list
    )
    conclusion: str = Field(
        description="Conclusion about hypothesis validity",
        default=""
    )

    @property
    def confidence_change(self) -> float:
        """Calculate change in confidence from prior to posterior."""
        return self.confidence_posterior - self.hypothesis.confidence_prior

    @property
    def evidence_ratio(self) -> float:
        """Calculate ratio of supporting to total evidence."""
        total = len(self.supporting_evidence) + len(self.contradicting_evidence)
        if total == 0:
            return 0.5
        return len(self.supporting_evidence) / total

    def __str__(self) -> str:
        """String representation."""
        return (
            f"{self.hypothesis.statement}\n"
            f"Confidence: {self.hypothesis.confidence_prior:.2f} → {self.confidence_posterior:.2f} "
            f"({self.confidence_change:+.2f})\n"
            f"Evidence: {len(self.supporting_evidence)} supporting, "
            f"{len(self.contradicting_evidence)} contradicting"
        )


class Synthesis(BaseModel):
    """Synthesis of research findings with confidence and recommendations."""

    key_findings: list[str] = Field(
        description="Main discoveries from research",
        default_factory=list
    )
    confidence: float = Field(
        description="Overall confidence in findings",
        ge=0.0,
        le=1.0,
        default=0.5
    )
    gaps_remaining: list[str] = Field(
        description="Important unanswered questions",
        default_factory=list
    )
    recommendations: list[str] = Field(
        description="Next steps or actions",
        default_factory=list
    )

    @property
    def has_high_confidence(self) -> bool:
        """Check if synthesis has high confidence (>= 0.7)."""
        return self.confidence >= 0.7

    @property
    def has_gaps(self) -> bool:
        """Check if there are remaining gaps."""
        return len(self.gaps_remaining) > 0

    @property
    def needs_more_research(self) -> bool:
        """Determine if more research is needed."""
        return not self.has_high_confidence or self.has_gaps

    def __str__(self) -> str:
        """String representation."""
        findings_text = "\n".join(f"  - {f}" for f in self.key_findings)
        gaps_text = "\n".join(f"  - {g}" for g in self.gaps_remaining) if self.gaps_remaining else "  None"
        recs_text = "\n".join(f"  - {r}" for r in self.recommendations)

        return (
            f"Research Synthesis (confidence: {self.confidence:.2f})\n\n"
            f"Key Findings:\n{findings_text}\n\n"
            f"Remaining Gaps:\n{gaps_text}\n\n"
            f"Recommendations:\n{recs_text}"
        )


class HopResult(BaseModel):
    """Result of a single research hop (iteration)."""

    hop_number: int = Field(description="Hop iteration number", ge=1)
    hypotheses: list[Hypothesis] = Field(
        description="Hypotheses tested in this hop",
        default_factory=list
    )
    evidence: list[dict[str, Any]] = Field(
        description="Evidence gathered in this hop",
        default_factory=list
    )
    results: list[HypothesisResult] = Field(
        description="Hypothesis test results",
        default_factory=list
    )
    synthesis: Optional[Synthesis] = Field(
        description="Synthesis of this hop's findings",
        default=None
    )

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence across all hypothesis results."""
        if not self.results:
            return 0.0
        return sum(r.confidence_posterior for r in self.results) / len(self.results)

    @property
    def evidence_count(self) -> int:
        """Count total evidence gathered."""
        return len(self.evidence)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Hop {self.hop_number}:\n"
            f"  Hypotheses tested: {len(self.hypotheses)}\n"
            f"  Evidence gathered: {self.evidence_count}\n"
            f"  Average confidence: {self.average_confidence:.2f}\n"
            f"  {'Synthesis available' if self.synthesis else 'No synthesis'}"
        )


class ReasoningContext(BaseModel):
    """Context for reasoning workflow across multiple hops."""

    query: str = Field(description="Original research query")
    plan: Optional[ResearchPlan] = Field(description="Research plan", default=None)
    hops: list[HopResult] = Field(description="Completed research hops", default_factory=list)
    cumulative_evidence: list[dict[str, Any]] = Field(
        description="All evidence gathered across hops",
        default_factory=list
    )
    final_synthesis: Optional[Synthesis] = Field(
        description="Final synthesis across all hops",
        default=None
    )

    @property
    def current_hop(self) -> int:
        """Get current hop number."""
        return len(self.hops)

    @property
    def total_evidence(self) -> int:
        """Count total evidence gathered."""
        return len(self.cumulative_evidence)

    @property
    def overall_confidence(self) -> float:
        """Calculate overall confidence across all hops."""
        if self.final_synthesis:
            return self.final_synthesis.confidence
        if not self.hops:
            return 0.0
        # Average of all hop confidences
        return sum(h.average_confidence for h in self.hops) / len(self.hops)

    def add_hop_result(self, hop_result: HopResult) -> None:
        """Add a hop result to context.

        Args:
            hop_result: HopResult to add
        """
        self.hops.append(hop_result)
        self.cumulative_evidence.extend(hop_result.evidence)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Reasoning Context: {self.query}\n"
            f"Hops completed: {self.current_hop}\n"
            f"Total evidence: {self.total_evidence}\n"
            f"Overall confidence: {self.overall_confidence:.2f}"
        )
