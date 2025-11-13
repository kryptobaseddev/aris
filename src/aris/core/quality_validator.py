"""Quality validation and metrics system for research results.

Provides automated quality gates, confidence scoring, and source credibility
assessment to ensure research meets quality standards before and after execution.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from aris.models.quality import (
    ConfidenceBreakdown,
    ConfidenceComponent,
    Contradiction,
    PostExecutionReport,
    PreExecutionReport,
    QualityGateLevel,
    QualityMetrics,
    SourceCredibilityRecord,
    SourceCredibilityTier,
)
from aris.models.source import Source, SourceTier

logger = logging.getLogger(__name__)


class SourceCredibilityTracker:
    """Tracks and classifies source credibility across citations."""

    # Domain patterns for credibility classification
    TIER_1_PATTERNS = [".edu", ".gov", "arxiv.org", "doi.org", "pubmed.gov", "nature.com"]
    TIER_2_PATTERNS = [
        "medium.com",
        "dev.to",
        "github.com",
        "docs.",
        "documentation",
        "official-blog",
        "research.google.com",
    ]
    TIER_3_PATTERNS = ["wikipedia.org", "stackoverflow.com", "reddit.com", "medium.com"]
    TIER_4_PATTERNS = []  # Default fallback

    def __init__(self):
        """Initialize source credibility tracker."""
        self.source_records: dict[str, SourceCredibilityRecord] = {}
        self.verification_cache: dict[str, tuple[str, datetime]] = {}

    def classify_source(self, url: str, source_type: str = "other") -> SourceCredibilityTier:
        """Classify source credibility tier based on URL patterns.

        Args:
            url: Source URL to classify
            source_type: Type of source (academic, documentation, etc.)

        Returns:
            SourceCredibilityTier classification
        """
        url_lower = url.lower()

        # Check tier patterns
        if any(pattern in url_lower for pattern in self.TIER_1_PATTERNS):
            return SourceCredibilityTier.TIER_1

        if any(pattern in url_lower for pattern in self.TIER_2_PATTERNS):
            return SourceCredibilityTier.TIER_2

        if any(pattern in url_lower for pattern in self.TIER_3_PATTERNS):
            return SourceCredibilityTier.TIER_3

        # Default to TIER_4
        return SourceCredibilityTier.TIER_4

    def calculate_credibility_score(
        self, tier: SourceCredibilityTier, verification_count: int = 0
    ) -> float:
        """Calculate credibility score based on tier and verification.

        Args:
            tier: Source credibility tier
            verification_count: Number of times source has been verified

        Returns:
            Credibility score (0.0-1.0)
        """
        # Base scores by tier
        base_scores = {
            SourceCredibilityTier.TIER_1: 0.95,
            SourceCredibilityTier.TIER_2: 0.80,
            SourceCredibilityTier.TIER_3: 0.60,
            SourceCredibilityTier.TIER_4: 0.40,
        }

        base_score = base_scores.get(tier, 0.5)

        # Verification boost (max 10% improvement)
        verification_boost = min(0.10, verification_count * 0.02)
        final_score = min(1.0, base_score + verification_boost)

        return round(final_score, 3)

    def track_source(self, source: Source, domain: Optional[str] = None) -> SourceCredibilityRecord:
        """Create or update source credibility record.

        Args:
            source: Source object to track
            domain: Domain extracted from URL (optional)

        Returns:
            SourceCredibilityRecord with credibility assessment
        """
        source_id = str(source.id)

        # Extract domain if not provided
        if not domain:
            from urllib.parse import urlparse

            parsed = urlparse(str(source.url))
            domain = parsed.netloc

        # Check if already tracked
        if source_id in self.source_records:
            record = self.source_records[source_id]
            record.times_cited += 1
            record.updated_at = datetime.utcnow()
            return record

        # Classify tier
        tier = self.classify_source(str(source.url))
        credibility_score = self.calculate_credibility_score(tier)

        # Create record
        record = SourceCredibilityRecord(
            source_id=source_id,
            domain=domain,
            url=str(source.url),
            tier=tier,
            credibility_score=credibility_score,
            verification_status="unverified",
        )

        self.source_records[source_id] = record
        logger.debug(f"Tracked source {domain} with tier {tier} and score {credibility_score}")

        return record

    def get_source_record(self, source_id: str) -> Optional[SourceCredibilityRecord]:
        """Retrieve source credibility record.

        Args:
            source_id: Source ID to look up

        Returns:
            SourceCredibilityRecord or None if not found
        """
        return self.source_records.get(source_id)

    def verify_source(self, source_id: str) -> SourceCredibilityRecord:
        """Mark source as verified and boost credibility.

        Args:
            source_id: Source ID to verify

        Returns:
            Updated SourceCredibilityRecord
        """
        record = self.source_records.get(source_id)
        if not record:
            raise ValueError(f"Source {source_id} not found in tracker")

        record.verification_count += 1
        record.verification_status = "verified"
        record.last_verified = datetime.utcnow()

        # Recalculate credibility score
        record.credibility_score = self.calculate_credibility_score(
            record.tier, record.verification_count
        )

        logger.info(f"Verified source {source_id}, new score: {record.credibility_score}")

        return record


class QualityValidator:
    """Validates research quality with pre- and post-execution gates."""

    def __init__(self, gate_level: QualityGateLevel = QualityGateLevel.STANDARD):
        """Initialize quality validator.

        Args:
            gate_level: Validation strictness level (permissive/standard/strict)
        """
        self.gate_level = gate_level
        self.credibility_tracker = SourceCredibilityTracker()

        # Gate thresholds
        self.thresholds = self._get_thresholds_for_level(gate_level)

        logger.info(f"Initialized QualityValidator with {gate_level} gate level")

    def _get_thresholds_for_level(self, level: QualityGateLevel) -> dict[str, float]:
        """Get validation thresholds for gate level.

        Args:
            level: Quality gate level

        Returns:
            Dictionary of threshold values
        """
        thresholds = {
            QualityGateLevel.PERMISSIVE: {
                "query_clarity_min": 0.4,
                "query_specificity_min": 0.4,
                "budget_sufficiency_min": 0.5,
                "feasibility_min": 0.5,
                "avg_credibility_min": 0.5,
                "source_diversity_min": 2,
                "confidence_target": 0.70,
                "coverage_min": 0.60,
                "contradiction_tolerance": 0.3,
            },
            QualityGateLevel.STANDARD: {
                "query_clarity_min": 0.6,
                "query_specificity_min": 0.6,
                "budget_sufficiency_min": 0.7,
                "feasibility_min": 0.6,
                "avg_credibility_min": 0.6,
                "source_diversity_min": 3,
                "confidence_target": 0.80,
                "coverage_min": 0.75,
                "contradiction_tolerance": 0.2,
            },
            QualityGateLevel.STRICT: {
                "query_clarity_min": 0.8,
                "query_specificity_min": 0.8,
                "budget_sufficiency_min": 0.85,
                "feasibility_min": 0.8,
                "avg_credibility_min": 0.75,
                "source_diversity_min": 5,
                "confidence_target": 0.90,
                "coverage_min": 0.90,
                "contradiction_tolerance": 0.1,
            },
        }

        return thresholds.get(level, thresholds[QualityGateLevel.STANDARD])

    async def validate_pre_execution(
        self,
        session_id: str,
        query: str,
        depth: str,
        budget: float,
    ) -> PreExecutionReport:
        """Validate research before execution.

        Checks query clarity, specificity, budget sufficiency, and feasibility.

        Args:
            session_id: Research session ID
            query: Research query text
            depth: Research depth (quick/standard/deep)
            budget: Available budget for research

        Returns:
            PreExecutionReport with validation results
        """
        logger.info(f"Starting pre-execution validation for session {session_id}")

        # Calculate scores
        query_clarity = self._score_query_clarity(query)
        query_specificity = self._score_query_specificity(query)
        budget_sufficiency = self._score_budget_sufficiency(depth, budget)
        feasibility = self._score_feasibility(query, depth)

        overall_readiness = (
            query_clarity * 0.25
            + query_specificity * 0.25
            + budget_sufficiency * 0.25
            + feasibility * 0.25
        )

        # Build confidence factors
        confidence_factors = {
            "query_clarity": query_clarity,
            "query_specificity": query_specificity,
            "budget_sufficiency": budget_sufficiency,
            "feasibility": feasibility,
        }

        # Determine if can proceed
        issues = []
        recommendations = []

        if query_clarity < self.thresholds["query_clarity_min"]:
            issues.append(f"Query clarity {query_clarity:.2f} below minimum {self.thresholds['query_clarity_min']}")
            recommendations.append("Refine query to be more specific and clear")

        if query_specificity < self.thresholds["query_specificity_min"]:
            issues.append(
                f"Query specificity {query_specificity:.2f} below minimum {self.thresholds['query_specificity_min']}"
            )
            recommendations.append("Add more specific keywords to narrow research scope")

        if budget_sufficiency < self.thresholds["budget_sufficiency_min"]:
            issues.append(f"Budget may be insufficient for {depth} research")
            recommendations.append(f"Increase budget or switch to 'quick' research depth")

        if feasibility < self.thresholds["feasibility_min"]:
            issues.append("Research may not be feasible with available resources")
            recommendations.append("Simplify query or reduce expected research depth")

        can_proceed = len(issues) == 0 or self.gate_level == QualityGateLevel.PERMISSIVE

        report = PreExecutionReport(
            session_id=session_id,
            query=query,
            depth=depth,
            budget=budget,
            query_clarity_score=query_clarity,
            query_specificity_score=query_specificity,
            budget_sufficiency_score=budget_sufficiency,
            feasibility_score=feasibility,
            can_proceed=can_proceed,
            overall_readiness=overall_readiness,
            issues=issues,
            recommendations=recommendations,
            confidence_factors=confidence_factors,
        )

        logger.info(
            f"Pre-execution validation complete: can_proceed={can_proceed}, readiness={overall_readiness:.2f}"
        )

        return report

    async def validate_post_execution(
        self,
        session_id: str,
        query: str,
        sources: list[Source],
        findings: list[str],
        duration_seconds: float,
    ) -> PostExecutionReport:
        """Validate research after execution.

        Checks source credibility, diversity, finding coverage, and contradictions.

        Args:
            session_id: Research session ID
            query: Original research query
            sources: Sources used in research
            findings: Research findings/conclusions
            duration_seconds: Research execution duration

        Returns:
            PostExecutionReport with validation results
        """
        logger.info(f"Starting post-execution validation for session {session_id}")

        # Track sources and calculate metrics
        for source in sources:
            self.credibility_tracker.track_source(source)

        # Calculate metrics
        source_count = len(sources)
        distinct_sources = len(set(str(s.url) for s in sources))
        avg_credibility = self._calculate_avg_credibility(sources)
        coverage = self._score_coverage(query, findings)
        consistency = self._score_consistency(findings)

        # Detect contradictions
        contradictions = self._detect_contradictions(findings)
        contradiction_count = len(contradictions)

        # Build issues and recommendations
        issues = []
        warnings = []
        recommendations = []

        if avg_credibility < self.thresholds["avg_credibility_min"]:
            issues.append(f"Average source credibility {avg_credibility:.2f} below minimum")
            recommendations.append("Consider additional searches for more reputable sources")

        if distinct_sources < self.thresholds["source_diversity_min"]:
            issues.append(f"Only {distinct_sources} distinct sources found (minimum {self.thresholds['source_diversity_min']})")
            recommendations.append("Expand research with additional search queries")

        if coverage < self.thresholds["coverage_min"]:
            warnings.append(f"Coverage score {coverage:.2f} below minimum")
            recommendations.append("Ensure findings adequately address all aspects of query")

        if consistency < 0.7:
            warnings.append(f"Finding consistency score {consistency:.2f} indicates potential contradictions")

        # Calculate overall quality
        quality_score = (
            avg_credibility * 0.3
            + coverage * 0.3
            + consistency * 0.2
            + (1.0 - min(contradiction_count / max(1, len(findings)), 1.0)) * 0.2
        )

        # Determine pass/fail
        passed = (
            avg_credibility >= self.thresholds["avg_credibility_min"]
            and distinct_sources >= self.thresholds["source_diversity_min"]
            and coverage >= self.thresholds["coverage_min"]
            and len(issues) == 0
        )

        report = PostExecutionReport(
            session_id=session_id,
            query=query,
            duration_seconds=duration_seconds,
            passed_validation=passed,
            quality_score=quality_score,
            source_count=source_count,
            distinct_source_count=distinct_sources,
            average_source_credibility=avg_credibility,
            query_coverage_score=coverage,
            finding_consistency_score=consistency,
            contradictions_detected=contradiction_count,
            contradictions=contradictions,
            issues=issues,
            recommendations=recommendations,
            warnings=warnings,
        )

        logger.info(
            f"Post-execution validation complete: passed={passed}, quality={quality_score:.2f}"
        )

        return report

    async def calculate_confidence_breakdown(
        self, sources: list[Source], findings: list[str], duration_seconds: float
    ) -> ConfidenceBreakdown:
        """Calculate detailed confidence breakdown.

        Args:
            sources: Research sources used
            findings: Research findings
            duration_seconds: Research duration

        Returns:
            ConfidenceBreakdown with component analysis
        """
        logger.debug("Calculating confidence breakdown")

        # Component scores
        source_credibility = self._calculate_avg_credibility(sources)
        consistency = self._score_consistency(findings)
        coverage = self._score_coverage("", findings)  # Will improve in future
        recency = self._score_recency(sources)
        diversity = self._score_source_diversity(sources)

        # Create components
        components = [
            ConfidenceComponent(
                name="Source Credibility",
                weight=0.30,
                score=source_credibility,
                rationale="Average credibility of sources used",
            ),
            ConfidenceComponent(
                name="Finding Consistency",
                weight=0.25,
                score=consistency,
                rationale="Consistency of findings across sources",
            ),
            ConfidenceComponent(
                name="Coverage Completeness",
                weight=0.25,
                score=coverage,
                rationale="Completeness of coverage for research scope",
            ),
            ConfidenceComponent(
                name="Source Recency",
                weight=0.10,
                score=recency,
                rationale="Freshness of sources used",
            ),
            ConfidenceComponent(
                name="Source Diversity",
                weight=0.10,
                score=diversity,
                rationale="Diversity of sources used",
            ),
        ]

        # Calculate overall
        overall = sum(c.weighted_contribution for c in components)

        breakdown = ConfidenceBreakdown(
            overall_confidence=overall,
            components=components,
            source_credibility_score=source_credibility,
            consistency_score=consistency,
            coverage_score=coverage,
            recency_score=recency,
            diversity_score=diversity,
        )

        logger.debug(f"Confidence breakdown: {overall:.2f}")

        return breakdown

    # Private scoring methods

    def _score_query_clarity(self, query: str) -> float:
        """Score query clarity.

        Args:
            query: Query text

        Returns:
            Clarity score (0.0-1.0)
        """
        if not query or len(query) < 10:
            return 0.0

        # Length bonus (up to 0.3)
        length_score = min(0.3, len(query) / 100)

        # Check for question words (clarity indicator)
        question_words = ["what", "how", "why", "when", "where", "which", "who", "whose"]
        has_question = any(word in query.lower() for word in question_words)
        question_score = 0.3 if has_question else 0.1

        # Check for specific keywords (1+ points)
        keyword_count = len(query.split())
        keyword_score = min(0.4, keyword_count * 0.05)

        return min(1.0, length_score + question_score + keyword_score)

    def _score_query_specificity(self, query: str) -> float:
        """Score query specificity.

        Args:
            query: Query text

        Returns:
            Specificity score (0.0-1.0)
        """
        if not query:
            return 0.0

        words = query.lower().split()

        # Penalize very short queries
        if len(words) < 3:
            return 0.3

        # Check for vague words (reduce score)
        vague_words = ["thing", "stuff", "something", "everything", "anything", "whatever"]
        vague_count = sum(1 for word in words if word in vague_words)
        vagueness_penalty = vague_count * 0.15

        # Check for specific terms (boost score)
        specific_bonus = min(0.3, (len(words) - 2) * 0.05)

        return max(0.0, min(1.0, 0.6 + specific_bonus - vagueness_penalty))

    def _score_budget_sufficiency(self, depth: str, budget: float) -> float:
        """Score budget sufficiency for depth.

        Args:
            depth: Research depth (quick/standard/deep)
            budget: Available budget

        Returns:
            Budget sufficiency score (0.0-1.0)
        """
        # Expected budgets by depth
        budget_targets = {
            "quick": 0.20,
            "standard": 0.50,
            "deep": 2.00,
        }

        target = budget_targets.get(depth, 0.50)

        if budget >= target:
            return 1.0
        elif budget >= target * 0.5:
            return 0.7
        elif budget > 0:
            return 0.4
        else:
            return 0.0

    def _score_feasibility(self, query: str, depth: str) -> float:
        """Score research feasibility.

        Args:
            query: Research query
            depth: Research depth

        Returns:
            Feasibility score (0.0-1.0)
        """
        # Short, vague queries are less feasible
        query_score = min(0.5, len(query) / 50)

        # Depth feasibility (deeper = harder)
        depth_scores = {"quick": 0.8, "standard": 0.6, "deep": 0.4}
        depth_score = depth_scores.get(depth, 0.5)

        return min(1.0, query_score + depth_score)

    def _calculate_avg_credibility(self, sources: list[Source]) -> float:
        """Calculate average source credibility.

        Args:
            sources: List of sources

        Returns:
            Average credibility score (0.0-1.0)
        """
        if not sources:
            return 0.0

        total_score = 0.0
        for source in sources:
            record = self.credibility_tracker.track_source(source)
            total_score += record.credibility_score

        return total_score / len(sources)

    def _score_coverage(self, query: str, findings: list[str]) -> float:
        """Score coverage of query by findings.

        Args:
            query: Research query
            findings: Research findings

        Returns:
            Coverage score (0.0-1.0)
        """
        if not findings:
            return 0.0

        # Simple heuristic: more findings = better coverage
        # This will be enhanced in future versions with semantic analysis
        finding_count = len(findings)

        if finding_count >= 5:
            return 1.0
        elif finding_count >= 3:
            return 0.8
        elif finding_count >= 2:
            return 0.6
        else:
            return 0.3

    def _score_consistency(self, findings: list[str]) -> float:
        """Score consistency of findings.

        Args:
            findings: Research findings

        Returns:
            Consistency score (0.0-1.0)
        """
        if len(findings) <= 1:
            return 1.0

        # Count findings that don't contradict each other
        # Simple approach: exact duplicates indicate consistency
        unique_findings = len(set(findings))
        total_findings = len(findings)

        if unique_findings == total_findings:
            return 0.8  # All unique (possibly contradictory)
        else:
            # Some duplication indicates agreement
            duplication_ratio = 1 - (unique_findings / total_findings)
            return min(1.0, 0.8 + duplication_ratio * 0.2)

    def _score_recency(self, sources: list[Source]) -> float:
        """Score source recency.

        Args:
            sources: Research sources

        Returns:
            Recency score (0.0-1.0)
        """
        if not sources:
            return 0.5

        now = datetime.utcnow()
        days_old_list = []

        for source in sources:
            age = (now - source.retrieved_at).days
            days_old_list.append(age)

        avg_age = sum(days_old_list) / len(days_old_list) if days_old_list else 0

        # Score based on average age
        if avg_age <= 30:
            return 1.0
        elif avg_age <= 90:
            return 0.8
        elif avg_age <= 365:
            return 0.6
        elif avg_age <= 730:
            return 0.4
        else:
            return 0.2

    def _score_source_diversity(self, sources: list[Source]) -> float:
        """Score diversity of sources.

        Args:
            sources: Research sources

        Returns:
            Diversity score (0.0-1.0)
        """
        if not sources:
            return 0.0

        # Extract domains
        from urllib.parse import urlparse

        domains = set()
        for source in sources:
            parsed = urlparse(str(source.url))
            domains.add(parsed.netloc)

        # Calculate diversity ratio
        unique_domains = len(domains)
        diversity_ratio = unique_domains / len(sources)

        # Score: 1.0 if all different, lower if duplicates
        return min(1.0, diversity_ratio * 1.2)

    def _detect_contradictions(self, findings: list[str]) -> list[Contradiction]:
        """Detect contradictions in findings.

        Args:
            findings: Research findings

        Returns:
            List of detected contradictions
        """
        contradictions = []

        # Simple heuristic: check for negation patterns
        negation_words = ["not", "no ", "never", "opposite", "contradicts"]

        for i, finding1 in enumerate(findings):
            for finding2 in findings[i + 1 :]:
                # Check if any negation patterns suggest contradiction
                finding1_lower = finding1.lower()
                finding2_lower = finding2.lower()

                # If findings contain negation of each other's main terms
                tokens1 = set(finding1_lower.split())
                tokens2 = set(finding2_lower.split())

                # Check for direct negation pattern
                is_negated = any(
                    f"not {word}" in finding1_lower or f"never {word}" in finding1_lower
                    for word in tokens2
                )

                if is_negated:
                    contradictions.append(
                        Contradiction(
                            finding_1=finding1,
                            finding_2=finding2,
                            conflict_score=0.7,
                            severity="medium",
                            resolution_suggestion="Further investigation needed to resolve contradiction",
                        )
                    )

        return contradictions
