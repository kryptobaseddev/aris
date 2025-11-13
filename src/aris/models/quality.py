"""Quality validation and metrics models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class QualityGateLevel(str, Enum):
    """Quality validation gate strictness levels."""

    PERMISSIVE = "permissive"  # Only reject obviously bad research
    STANDARD = "standard"  # Balanced validation (default)
    STRICT = "strict"  # Rigorous validation for critical decisions


class SourceCredibilityTier(str, Enum):
    """Source credibility classification tiers."""

    TIER_1 = "tier_1"  # Academic, peer-reviewed, official (0.9-1.0)
    TIER_2 = "tier_2"  # Established media, expert sources (0.7-0.9)
    TIER_3 = "tier_3"  # Community, user-generated content (0.5-0.7)
    TIER_4 = "tier_4"  # Forums, unverified sources (0.3-0.5)


class ConfidenceComponent(BaseModel):
    """Single component of confidence calculation."""

    name: str
    weight: float = Field(..., ge=0.0, le=1.0)
    score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = ""

    @property
    def weighted_contribution(self) -> float:
        """Calculate weighted contribution to overall confidence."""
        return self.score * self.weight


class ConfidenceBreakdown(BaseModel):
    """Detailed confidence analysis with component breakdown."""

    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    components: list[ConfidenceComponent]

    source_credibility_score: float = Field(..., ge=0.0, le=1.0)
    consistency_score: float = Field(..., ge=0.0, le=1.0)
    coverage_score: float = Field(..., ge=0.0, le=1.0)
    recency_score: float = Field(..., ge=0.0, le=1.0)
    diversity_score: float = Field(..., ge=0.0, le=1.0)

    @property
    def confidence_summary(self) -> str:
        """Human-readable confidence summary."""
        if self.overall_confidence >= 0.85:
            return "High confidence"
        elif self.overall_confidence >= 0.70:
            return "Medium confidence"
        elif self.overall_confidence >= 0.50:
            return "Low confidence"
        else:
            return "Very low confidence"


class Contradiction(BaseModel):
    """Detected contradiction between findings."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    finding_1: str = Field(..., description="First contradicting finding")
    finding_2: str = Field(..., description="Second contradicting finding")
    conflict_score: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(..., description="low | medium | high")
    sources_involved: list[str] = Field(default_factory=list)
    resolution_suggestion: str = ""

    @property
    def requires_resolution(self) -> bool:
        """Check if contradiction requires attention."""
        return self.conflict_score >= 0.6


class PreExecutionReport(BaseModel):
    """Quality assessment before research execution."""

    session_id: str
    query: str
    depth: str
    budget: float

    # Validation results
    query_clarity_score: float = Field(..., ge=0.0, le=1.0)
    query_specificity_score: float = Field(..., ge=0.0, le=1.0)
    budget_sufficiency_score: float = Field(..., ge=0.0, le=1.0)
    feasibility_score: float = Field(..., ge=0.0, le=1.0)

    can_proceed: bool
    overall_readiness: float = Field(..., ge=0.0, le=1.0)

    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence_factors: dict[str, float] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostExecutionReport(BaseModel):
    """Quality assessment after research execution."""

    session_id: str
    query: str
    duration_seconds: float

    # Validation checks
    passed_validation: bool
    quality_score: float = Field(..., ge=0.0, le=1.0)

    # Detailed metrics
    source_count: int = 0
    distinct_source_count: int = 0
    average_source_credibility: float = Field(default=0.6, ge=0.0, le=1.0)

    # Coverage
    query_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_issues: list[str] = Field(default_factory=list)

    # Consistency
    finding_consistency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    contradictions_detected: int = 0
    contradictions: list[Contradiction] = Field(default_factory=list)

    # Final results
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SourceCredibilityRecord(BaseModel):
    """Source credibility tracking and history."""

    source_id: str
    domain: str
    url: str

    # Credibility assessment
    tier: SourceCredibilityTier
    credibility_score: float = Field(..., ge=0.0, le=1.0)

    # Verification
    verification_status: str = "unverified"  # unverified | verified | disputed
    verification_count: int = 0
    last_verified: Optional[datetime] = None

    # Tracking
    times_cited: int = 0
    citation_contexts: list[str] = Field(default_factory=list)

    # Historical
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def confidence_range(self) -> tuple[float, float]:
        """Get credibility range for this tier."""
        tier_ranges = {
            SourceCredibilityTier.TIER_1: (0.9, 1.0),
            SourceCredibilityTier.TIER_2: (0.7, 0.9),
            SourceCredibilityTier.TIER_3: (0.5, 0.7),
            SourceCredibilityTier.TIER_4: (0.3, 0.5),
        }
        return tier_ranges.get(self.tier, (0.0, 1.0))


class QualityMetrics(BaseModel):
    """Comprehensive quality metrics for a session."""

    session_id: str
    query: str

    # Execution metrics
    total_sources: int = 0
    distinct_sources: int = 0
    hops_executed: int = 0
    total_cost: float = 0.0
    duration_seconds: float = 0.0

    # Quality components
    pre_execution_report: Optional[PreExecutionReport] = None
    post_execution_report: Optional[PostExecutionReport] = None
    confidence_breakdown: Optional[ConfidenceBreakdown] = None

    # Overall assessment
    overall_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    validation_passed: bool = False
    gate_level_used: QualityGateLevel = QualityGateLevel.STANDARD

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def quality_rating(self) -> str:
        """Human-readable quality rating."""
        if self.overall_quality_score >= 0.85:
            return "Excellent"
        elif self.overall_quality_score >= 0.70:
            return "Good"
        elif self.overall_quality_score >= 0.55:
            return "Fair"
        elif self.overall_quality_score >= 0.40:
            return "Poor"
        else:
            return "Unacceptable"


class ValidationRule(BaseModel):
    """Single validation rule for quality gates."""

    name: str
    description: str
    metric_name: str
    operator: str  # ">=", "<=", ">", "<", "in", "not_in"
    threshold: Any
    gate_level: QualityGateLevel
    severity: str = "warning"  # warning | error | critical


class ValidationGate(BaseModel):
    """Quality validation gate configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    rules: list[ValidationRule] = Field(default_factory=list)
    gate_level: QualityGateLevel = QualityGateLevel.STANDARD
    enabled: bool = True

    # Blocking behavior
    blocks_execution: bool = False
    block_on_fail: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
