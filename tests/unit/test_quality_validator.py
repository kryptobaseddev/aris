"""Unit tests for quality validation system.

Tests cover:
- SourceCredibilityTracker classification and scoring
- PreExecutionReport validation
- PostExecutionReport validation
- Confidence breakdown calculation
- Contradiction detection
- Quality gate enforcement
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from aris.core.quality_validator import QualityValidator, SourceCredibilityTracker
from aris.models.quality import (
    ConfidenceBreakdown,
    Contradiction,
    PostExecutionReport,
    PreExecutionReport,
    QualityGateLevel,
    SourceCredibilityTier,
)
from aris.models.source import Source, SourceType


class TestSourceCredibilityTracker:
    """Tests for SourceCredibilityTracker."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return SourceCredibilityTracker()

    def test_classify_tier1_source(self, tracker):
        """Test classification of Tier 1 academic source."""
        tier = tracker.classify_source("https://www.arxiv.org/paper/12345")
        assert tier == SourceCredibilityTier.TIER_1

    def test_classify_tier1_gov_source(self, tracker):
        """Test classification of Tier 1 government source."""
        tier = tracker.classify_source("https://www.example.gov/data")
        assert tier == SourceCredibilityTier.TIER_1

    def test_classify_tier1_edu_source(self, tracker):
        """Test classification of Tier 1 educational source."""
        tier = tracker.classify_source("https://cs.stanford.edu/research")
        assert tier == SourceCredibilityTier.TIER_1

    def test_classify_tier2_source(self, tracker):
        """Test classification of Tier 2 established source."""
        tier = tracker.classify_source("https://medium.com/author/article")
        assert tier == SourceCredibilityTier.TIER_2

    def test_classify_tier2_documentation(self, tracker):
        """Test classification of Tier 2 documentation."""
        tier = tracker.classify_source("https://docs.example.com/guide")
        assert tier == SourceCredibilityTier.TIER_2

    def test_classify_tier3_source(self, tracker):
        """Test classification of Tier 3 community source."""
        tier = tracker.classify_source("https://en.wikipedia.org/wiki/Example")
        assert tier == SourceCredibilityTier.TIER_3

    def test_classify_tier4_source(self, tracker):
        """Test classification of Tier 4 default source."""
        tier = tracker.classify_source("https://example-blog.blogspot.com/post")
        assert tier == SourceCredibilityTier.TIER_4

    def test_calculate_tier1_credibility(self, tracker):
        """Test credibility scoring for Tier 1."""
        score = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_1)
        assert 0.90 <= score <= 1.0

    def test_calculate_tier2_credibility(self, tracker):
        """Test credibility scoring for Tier 2."""
        score = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_2)
        assert 0.70 <= score <= 0.90

    def test_calculate_tier3_credibility(self, tracker):
        """Test credibility scoring for Tier 3."""
        score = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_3)
        assert 0.50 <= score <= 0.70

    def test_calculate_tier4_credibility(self, tracker):
        """Test credibility scoring for Tier 4."""
        score = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_4)
        assert 0.30 <= score <= 0.50

    def test_verification_boost(self, tracker):
        """Test credibility boost from verification."""
        score_unverified = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_3, 0)
        score_verified_once = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_3, 1)
        score_verified_thrice = tracker.calculate_credibility_score(SourceCredibilityTier.TIER_3, 3)

        assert score_verified_once > score_unverified
        assert score_verified_thrice > score_verified_once

    def test_track_new_source(self, tracker):
        """Test tracking a new source."""
        source = Source(
            url="https://example.edu/paper",
            title="Example Paper",
            source_type=SourceType.ACADEMIC,
        )

        record = tracker.track_source(source)

        assert record.source_id == str(source.id)
        assert record.tier == SourceCredibilityTier.TIER_1
        assert record.times_cited == 1

    def test_track_existing_source(self, tracker):
        """Test tracking an existing source (increment citations)."""
        source = Source(
            url="https://example.edu/paper",
            title="Example Paper",
            source_type=SourceType.ACADEMIC,
        )

        record1 = tracker.track_source(source)
        record2 = tracker.track_source(source)

        assert record1.source_id == record2.source_id
        assert record2.times_cited == 2

    def test_verify_source(self, tracker):
        """Test source verification."""
        source = Source(
            url="https://example.edu/paper",
            title="Example Paper",
            source_type=SourceType.ACADEMIC,
        )

        tracker.track_source(source)
        original_score = tracker.source_records[str(source.id)].credibility_score

        tracker.verify_source(str(source.id))
        verified_score = tracker.source_records[str(source.id)].credibility_score

        assert verified_score >= original_score
        assert tracker.source_records[str(source.id)].verification_status == "verified"


class TestQualityValidatorPreExecution:
    """Tests for pre-execution validation."""

    @pytest.fixture
    def validator(self):
        """Create validator with standard gate level."""
        return QualityValidator(QualityGateLevel.STANDARD)

    @pytest.mark.asyncio
    async def test_validate_clear_specific_query(self, validator):
        """Test validation of clear, specific query."""
        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="What are the latest advances in CRISPR gene therapy for treating cancer?",
            depth="standard",
            budget=0.50,
        )

        assert report.can_proceed == True
        assert report.query_clarity_score > 0.6
        assert report.query_specificity_score > 0.6
        assert len(report.issues) == 0

    @pytest.mark.asyncio
    async def test_validate_vague_query(self, validator):
        """Test validation of vague query."""
        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="stuff and things",
            depth="standard",
            budget=0.50,
        )

        assert report.query_clarity_score < 0.6
        assert len(report.issues) > 0
        assert report.can_proceed == False

    @pytest.mark.asyncio
    async def test_validate_insufficient_budget(self, validator):
        """Test validation with insufficient budget."""
        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="What is machine learning?",
            depth="deep",
            budget=0.10,
        )

        assert any("budget" in issue.lower() for issue in report.issues)

    @pytest.mark.asyncio
    async def test_validate_short_query(self, validator):
        """Test validation of very short query."""
        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="ML",
            depth="standard",
            budget=0.50,
        )

        assert report.query_clarity_score < 0.6

    @pytest.mark.asyncio
    async def test_permissive_gate_allows_marginal(self, validator):
        """Test that permissive gate allows marginal queries."""
        validator.gate_level = QualityGateLevel.PERMISSIVE
        validator.thresholds = validator._get_thresholds_for_level(QualityGateLevel.PERMISSIVE)

        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="something",
            depth="standard",
            budget=0.10,
        )

        assert report.can_proceed == True

    @pytest.mark.asyncio
    async def test_strict_gate_rejects_marginal(self, validator):
        """Test that strict gate rejects marginal queries."""
        validator.gate_level = QualityGateLevel.STRICT
        validator.thresholds = validator._get_thresholds_for_level(QualityGateLevel.STRICT)

        report = await validator.validate_pre_execution(
            session_id="test-session",
            query="What is something?",
            depth="standard",
            budget=0.50,
        )

        assert report.can_proceed == False


class TestQualityValidatorPostExecution:
    """Tests for post-execution validation."""

    @pytest.fixture
    def validator(self):
        """Create validator with standard gate level."""
        return QualityValidator(QualityGateLevel.STANDARD)

    @pytest.fixture
    def good_sources(self):
        """Create high-quality sources."""
        return [
            Source(
                url="https://www.arxiv.org/paper/1",
                title="Academic Paper 1",
                source_type=SourceType.ACADEMIC,
            ),
            Source(
                url="https://github.com/docs/guide",
                title="Official Documentation",
                source_type=SourceType.DOCUMENTATION,
            ),
            Source(
                url="https://www.cs.stanford.edu/research",
                title="Stanford Research",
                source_type=SourceType.ACADEMIC,
            ),
            Source(
                url="https://medium.com/article",
                title="Expert Blog Post",
                source_type=SourceType.BLOG,
            ),
            Source(
                url="https://www.nature.com/article",
                title="Nature Article",
                source_type=SourceType.ACADEMIC,
            ),
        ]

    @pytest.fixture
    def poor_sources(self):
        """Create low-quality sources."""
        return [
            Source(
                url="https://example-blog.blogspot.com/post",
                title="Personal Blog",
                source_type=SourceType.BLOG,
            ),
            Source(
                url="https://forum.example.com/post",
                title="Forum Post",
                source_type=SourceType.FORUM,
            ),
        ]

    @pytest.mark.asyncio
    async def test_validate_good_research(self, validator, good_sources):
        """Test validation of good research."""
        report = await validator.validate_post_execution(
            session_id="test-session",
            query="What are advances in CRISPR therapy?",
            sources=good_sources,
            findings=[
                "CRISPR technology has advanced significantly",
                "Clinical trials show promising results",
                "Off-target effects have been reduced",
            ],
            duration_seconds=120,
        )

        assert report.passed_validation == True
        assert report.quality_score > 0.7
        assert report.source_count == 5
        assert report.distinct_source_count == 5

    @pytest.mark.asyncio
    async def test_validate_poor_research_sources(self, validator, poor_sources):
        """Test validation of research with poor sources."""
        report = await validator.validate_post_execution(
            session_id="test-session",
            query="What is machine learning?",
            sources=poor_sources,
            findings=["Finding 1", "Finding 2"],
            duration_seconds=60,
        )

        assert report.passed_validation == False
        assert any("credibility" in issue.lower() for issue in report.issues)

    @pytest.mark.asyncio
    async def test_validate_insufficient_sources(self, validator):
        """Test validation with insufficient source diversity."""
        sources = [
            Source(
                url="https://example.com/article1",
                title="Article 1",
                source_type=SourceType.OTHER,
            ),
            Source(
                url="https://example.com/article2",
                title="Article 2",
                source_type=SourceType.OTHER,
            ),
        ]

        report = await validator.validate_post_execution(
            session_id="test-session",
            query="What is something?",
            sources=sources,
            findings=["Finding 1"],
            duration_seconds=60,
        )

        assert any("sources" in issue.lower() for issue in report.issues)

    @pytest.mark.asyncio
    async def test_validate_with_contradictions(self, validator, good_sources):
        """Test validation that detects contradictions."""
        report = await validator.validate_post_execution(
            session_id="test-session",
            query="Query",
            sources=good_sources,
            findings=[
                "Technology X is effective",
                "Technology X is not effective",
            ],
            duration_seconds=60,
        )

        assert report.contradictions_detected > 0

    @pytest.mark.asyncio
    async def test_no_sources_yields_zero_credibility(self, validator):
        """Test that no sources yields zero average credibility."""
        report = await validator.validate_post_execution(
            session_id="test-session",
            query="Query",
            sources=[],
            findings=[],
            duration_seconds=0,
        )

        assert report.average_source_credibility == 0.0


class TestConfidenceCalculation:
    """Tests for confidence breakdown calculation."""

    @pytest.fixture
    def validator(self):
        """Create validator."""
        return QualityValidator()

    @pytest.mark.asyncio
    async def test_confidence_breakdown_high_quality(self, validator):
        """Test confidence breakdown for high-quality research."""
        sources = [
            Source(
                url="https://arxiv.org/paper/1",
                title="Paper",
                source_type=SourceType.ACADEMIC,
            ),
            Source(
                url="https://example.edu/article",
                title="Article",
                source_type=SourceType.ACADEMIC,
            ),
            Source(
                url="https://docs.example.com",
                title="Docs",
                source_type=SourceType.DOCUMENTATION,
            ),
        ]

        breakdown = await validator.calculate_confidence_breakdown(
            sources=sources,
            findings=["Finding 1", "Finding 2", "Finding 3"],
            duration_seconds=120,
        )

        assert breakdown.overall_confidence > 0.7
        assert len(breakdown.components) == 5
        assert breakdown.source_credibility_score > 0.6

    @pytest.mark.asyncio
    async def test_confidence_breakdown_components_sum(self, validator):
        """Test that confidence components sum correctly."""
        sources = [
            Source(
                url="https://arxiv.org/paper/1",
                title="Paper",
                source_type=SourceType.ACADEMIC,
            ),
        ]

        breakdown = await validator.calculate_confidence_breakdown(
            sources=sources,
            findings=["Finding 1"],
            duration_seconds=60,
        )

        # Overall should equal sum of weighted components
        calculated_overall = sum(c.weighted_contribution for c in breakdown.components)
        assert abs(breakdown.overall_confidence - calculated_overall) < 0.01

    @pytest.mark.asyncio
    async def test_confidence_empty_sources(self, validator):
        """Test confidence calculation with no sources."""
        breakdown = await validator.calculate_confidence_breakdown(
            sources=[],
            findings=[],
            duration_seconds=0,
        )

        assert breakdown.overall_confidence < 0.5


class TestContradictionDetection:
    """Tests for contradiction detection."""

    @pytest.fixture
    def validator(self):
        """Create validator."""
        return QualityValidator()

    def test_detect_simple_contradiction(self, validator):
        """Test detection of simple contradiction."""
        findings = [
            "Technology X is effective",
            "Technology X is not effective",
        ]

        contradictions = validator._detect_contradictions(findings)

        assert len(contradictions) > 0

    def test_detect_no_contradiction(self, validator):
        """Test that similar findings don't create false contradictions."""
        findings = [
            "Technology X shows promise",
            "Technology X appears beneficial",
            "Technology X demonstrates potential",
        ]

        contradictions = validator._detect_contradictions(findings)

        # Should detect no or very few contradictions
        assert len(contradictions) <= 1

    def test_detect_multiple_contradictions(self, validator):
        """Test detection of multiple contradictions."""
        findings = [
            "Technology X is effective",
            "Technology X is not effective",
            "Method A is superior",
            "Method A is never superior",
        ]

        contradictions = validator._detect_contradictions(findings)

        assert len(contradictions) > 0

    def test_contradiction_has_severity(self, validator):
        """Test that detected contradictions have severity levels."""
        findings = [
            "Finding A",
            "Finding not A",
        ]

        contradictions = validator._detect_contradictions(findings)

        if contradictions:
            for c in contradictions:
                assert c.severity in ["low", "medium", "high"]


class TestQualityScoringMethods:
    """Tests for individual quality scoring methods."""

    @pytest.fixture
    def validator(self):
        """Create validator."""
        return QualityValidator()

    def test_score_query_clarity_high(self, validator):
        """Test query clarity scoring for clear query."""
        score = validator._score_query_clarity(
            "What are the latest advances in quantum computing technology?"
        )
        assert score > 0.6

    def test_score_query_clarity_low(self, validator):
        """Test query clarity scoring for unclear query."""
        score = validator._score_query_clarity("stuff")
        assert score < 0.5

    def test_score_query_specificity_high(self, validator):
        """Test query specificity scoring for specific query."""
        score = validator._score_query_specificity("How does CRISPR gene therapy treat cancer?")
        assert score > 0.6

    def test_score_query_specificity_low(self, validator):
        """Test query specificity scoring for vague query."""
        score = validator._score_query_specificity("What is stuff?")
        assert score < 0.6

    def test_score_budget_sufficient(self, validator):
        """Test budget sufficiency for adequate budget."""
        score = validator._score_budget_sufficiency("standard", 0.50)
        assert score >= 1.0

    def test_score_budget_insufficient(self, validator):
        """Test budget insufficiency."""
        score = validator._score_budget_sufficiency("deep", 0.10)
        assert score < 0.8

    def test_score_coverage_good(self, validator):
        """Test coverage scoring with many findings."""
        score = validator._score_coverage("query", ["F1", "F2", "F3", "F4", "F5"])
        assert score >= 0.9

    def test_score_coverage_poor(self, validator):
        """Test coverage scoring with few findings."""
        score = validator._score_coverage("query", ["F1"])
        assert score < 0.5

    def test_score_consistency_all_unique(self, validator):
        """Test consistency when all findings are unique."""
        score = validator._score_consistency(["Finding 1", "Finding 2", "Finding 3"])
        assert score >= 0.7

    def test_score_consistency_with_duplicates(self, validator):
        """Test consistency with duplicates (higher score)."""
        unique_score = validator._score_consistency(
            ["Finding 1", "Finding 2", "Finding 3"]
        )
        duplicate_score = validator._score_consistency(
            ["Finding 1", "Finding 1", "Finding 1"]
        )
        assert duplicate_score >= unique_score

    def test_score_recency_recent(self, validator):
        """Test recency scoring for recent sources."""
        from datetime import timedelta

        source = Source(
            url="https://example.com",
            title="Recent",
            source_type=SourceType.OTHER,
            retrieved_at=datetime.utcnow() - timedelta(days=10),
        )

        score = validator._score_recency([source])
        assert score >= 0.9

    def test_score_recency_old(self, validator):
        """Test recency scoring for old sources."""
        from datetime import timedelta

        source = Source(
            url="https://example.com",
            title="Old",
            source_type=SourceType.OTHER,
            retrieved_at=datetime.utcnow() - timedelta(days=1000),
        )

        score = validator._score_recency([source])
        assert score <= 0.3

    def test_score_diversity_all_different(self, validator):
        """Test diversity scoring when all sources are from different domains."""
        sources = [
            Source(
                url="https://site1.com/article",
                title="Source 1",
                source_type=SourceType.OTHER,
            ),
            Source(
                url="https://site2.edu/paper",
                title="Source 2",
                source_type=SourceType.ACADEMIC,
            ),
            Source(
                url="https://site3.org/page",
                title="Source 3",
                source_type=SourceType.OTHER,
            ),
        ]

        score = validator._score_source_diversity(sources)
        assert score >= 0.9

    def test_score_diversity_all_same(self, validator):
        """Test diversity scoring when all sources are from same domain."""
        sources = [
            Source(
                url="https://site1.com/article1",
                title="Article 1",
                source_type=SourceType.OTHER,
            ),
            Source(
                url="https://site1.com/article2",
                title="Article 2",
                source_type=SourceType.OTHER,
            ),
            Source(
                url="https://site1.com/article3",
                title="Article 3",
                source_type=SourceType.OTHER,
            ),
        ]

        score = validator._score_source_diversity(sources)
        assert score < 0.5
