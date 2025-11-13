"""Research workflow data models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResearchDepth(str, Enum):
    """Research depth levels with associated budgets."""

    QUICK = "quick"  # $0.20 target, 1 hop
    STANDARD = "standard"  # $0.50 target, 3 hops
    DEEP = "deep"  # $2.00 target, 5 hops


class ResearchQuery(BaseModel):
    """User research query with metadata."""

    id: UUID = Field(default_factory=uuid4)
    query_text: str = Field(..., min_length=5, max_length=2000)
    depth: ResearchDepth = ResearchDepth.STANDARD
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # User preferences
    max_cost: Optional[float] = None  # Override default budget
    preferred_llm: Optional[str] = None  # Override default LLM


class ResearchHop(BaseModel):
    """Single research iteration (search → analyze → synthesize)."""

    hop_number: int = Field(..., ge=1)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Search phase
    search_queries: list[str] = Field(default_factory=list)
    sources_found: int = 0
    tavily_cost: float = 0.0

    # Analysis phase
    input_tokens: int = 0
    output_tokens: int = 0
    llm_model: str = ""
    llm_cost: float = 0.0

    # Results
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    confidence_gain: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost for this hop."""
        return self.tavily_cost + self.llm_cost

    @property
    def duration_seconds(self) -> Optional[float]:
        """Hop duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ResearchSession(BaseModel):
    """Complete research session with multiple hops."""

    id: UUID = Field(default_factory=uuid4)
    query: ResearchQuery
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Execution state
    hops: list[ResearchHop] = Field(default_factory=list)
    current_hop: int = 1
    status: str = "planning"  # planning | searching | analyzing | validating | complete | error

    # Results
    documents_found: list[str] = Field(default_factory=list)  # Existing documents found
    document_created: Optional[str] = None  # New document created (or None if updated)
    document_updated: Optional[str] = None  # Existing document updated
    final_confidence: float = 0.0

    # Cost tracking
    total_cost: float = 0.0
    budget_target: float = 0.50
    budget_warnings_issued: list[str] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if research session completed."""
        return self.status in ("complete", "error")

    @property
    def within_budget(self) -> bool:
        """Check if session stayed within budget."""
        return self.total_cost <= self.budget_target

    @property
    def duration_seconds(self) -> Optional[float]:
        """Session duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_hop(self, hop: ResearchHop) -> None:
        """Add a research hop and update totals."""
        self.hops.append(hop)
        self.total_cost += hop.total_cost
        self.current_hop += 1


class ResearchResult(BaseModel):
    """Final research output for user."""

    session_id: UUID
    query_text: str
    success: bool

    # Output document
    document_path: Optional[str] = None
    operation: str  # "created" | "updated" | "found_existing"

    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources_analyzed: int
    hops_executed: int

    # Cost metrics
    total_cost: float
    within_budget: bool
    duration_seconds: float

    # Recommendations
    suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
