"""Source credibility and citation models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class SourceTier(Enum):
    """Source credibility tiers."""

    TIER_1 = 1  # Academic journals, official docs, peer-reviewed (0.9-1.0)
    TIER_2 = 2  # Established media, industry reports, expert blogs (0.7-0.9)
    TIER_3 = 3  # Community resources, user docs, Wikipedia (0.5-0.7)
    TIER_4 = 4  # Forums, social media, personal blogs (0.3-0.5)


class SourceType(str, Enum):
    """Source content types."""

    ACADEMIC = "academic"
    DOCUMENTATION = "documentation"
    NEWS = "news"
    BLOG = "blog"
    FORUM = "forum"
    SOCIAL = "social"
    VIDEO = "video"
    OTHER = "other"


class Source(BaseModel):
    """Research source with provenance tracking."""

    id: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    title: str = Field(..., min_length=1, max_length=500)
    source_type: SourceType = SourceType.OTHER
    tier: SourceTier = SourceTier.TIER_3

    # Content
    summary: Optional[str] = None
    key_facts: list[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    # Credibility
    credibility_score: float = Field(default=0.6, ge=0.0, le=1.0)
    verification_status: str = "unverified"  # unverified | verified | disputed

    # Usage
    cited_by_documents: list[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def citation_format(self) -> str:
        """Generate citation string."""
        return f"[{self.title}]({self.url})"

    @classmethod
    def from_tavily_result(cls, result: dict) -> "Source":
        """Create Source from Tavily search result."""
        # Infer tier from domain
        tier = cls._infer_tier(result.get("url", ""))

        return cls(
            url=result["url"],
            title=result.get("title", "Untitled"),
            summary=result.get("content", ""),
            tier=tier,
            credibility_score=tier.value * 0.2  # Basic scoring
        )

    @staticmethod
    def _infer_tier(url: str) -> SourceTier:
        """Infer credibility tier from URL domain."""
        url_lower = url.lower()

        # Tier 1: Academic and official
        if any(domain in url_lower for domain in [".edu", ".gov", "arxiv.org", "doi.org"]):
            return SourceTier.TIER_1

        # Tier 2: Established media and tech docs
        if any(domain in url_lower for domain in ["medium.com", "dev.to", "docs.", "github.com/docs"]):
            return SourceTier.TIER_2

        # Tier 3: Community and wikis
        if any(domain in url_lower for domain in ["wikipedia.org", "stackoverflow.com"]):
            return SourceTier.TIER_3

        # Tier 4: Default
        return SourceTier.TIER_4
