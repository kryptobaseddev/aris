"""Unit tests for deduplication gate functionality.

Tests cover:
- Similarity detection and scoring
- Decision logic (CREATE vs UPDATE vs MERGE)
- Document finding and matching
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from aris.core.deduplication_gate import (
    DeduplicationAction,
    DeduplicationGate,
    DeduplicationResult,
    SimilarityMatch,
)
from aris.models.document import Document, DocumentMetadata, DocumentStatus
from aris.storage.database import DatabaseManager


class TestSimilarityMatch:
    """Test SimilarityMatch dataclass."""

    def test_valid_similarity_match(self):
        """Test creating valid similarity match."""
        doc = Document(
            metadata=DocumentMetadata(
                title="Test Doc",
                purpose="Test",
            ),
            content="Test content",
            file_path=Path("/test/doc.md"),
        )
        match = SimilarityMatch(
            document=doc,
            similarity_score=0.85,
            reason="High topic overlap",
        )
        assert match.document == doc
        assert match.similarity_score == 0.85
        assert match.reason == "High topic overlap"

    def test_similarity_score_validation(self):
        """Test similarity score must be 0.0-1.0."""
        doc = Document(
            metadata=DocumentMetadata(
                title="Test Doc",
                purpose="Test",
            ),
            content="Test content",
            file_path=Path("/test/doc.md"),
        )

        # Score > 1.0 should raise error
        with pytest.raises(ValueError, match="Similarity score must be"):
            SimilarityMatch(document=doc, similarity_score=1.5)

        # Score < 0.0 should raise error
        with pytest.raises(ValueError, match="Similarity score must be"):
            SimilarityMatch(document=doc, similarity_score=-0.1)

    def test_similarity_score_boundaries(self):
        """Test boundary values for similarity score."""
        doc = Document(
            metadata=DocumentMetadata(
                title="Test Doc",
                purpose="Test",
            ),
            content="Test content",
            file_path=Path("/test/doc.md"),
        )

        # 0.0 should be valid
        match = SimilarityMatch(document=doc, similarity_score=0.0)
        assert match.similarity_score == 0.0

        # 1.0 should be valid
        match = SimilarityMatch(document=doc, similarity_score=1.0)
        assert match.similarity_score == 1.0


class TestDeduplicationResult:
    """Test DeduplicationResult dataclass."""

    def test_create_action_without_target(self):
        """Test CREATE action doesn't require target document."""
        result = DeduplicationResult(
            action=DeduplicationAction.CREATE,
            confidence=0.95,
            reason="No similar documents found",
        )
        assert result.action == DeduplicationAction.CREATE
        assert result.should_create is True
        assert result.should_update is False
        assert result.target_document is None

    def test_update_action_requires_target(self):
        """Test UPDATE action requires target document."""
        with pytest.raises(ValueError, match="requires target_document"):
            DeduplicationResult(
                action=DeduplicationAction.UPDATE,
                target_document=None,
                confidence=0.85,
            )

    def test_merge_action_requires_target(self):
        """Test MERGE action requires target document."""
        with pytest.raises(ValueError, match="requires target_document"):
            DeduplicationResult(
                action=DeduplicationAction.MERGE,
                target_document=None,
                confidence=0.70,
            )

    def test_update_action_with_target(self):
        """Test UPDATE action with target document."""
        target_doc = Document(
            metadata=DocumentMetadata(
                title="Existing Doc",
                purpose="Test",
            ),
            content="Existing content",
            file_path=Path("/test/existing.md"),
        )
        result = DeduplicationResult(
            action=DeduplicationAction.UPDATE,
            target_document=target_doc,
            confidence=0.88,
            reason="High similarity detected",
        )
        assert result.action == DeduplicationAction.UPDATE
        assert result.should_update is True
        assert result.should_create is False
        assert result.target_document == target_doc

    def test_confidence_validation(self):
        """Test confidence score must be 0.0-1.0."""
        with pytest.raises(ValueError, match="Confidence must be"):
            DeduplicationResult(
                action=DeduplicationAction.CREATE,
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="Confidence must be"):
            DeduplicationResult(
                action=DeduplicationAction.CREATE,
                confidence=-0.1,
            )


class TestDeduplicationGate:
    """Test DeduplicationGate functionality."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(db_path)
        db_manager.initialize_database()
        yield db_manager
        db_manager.close()

    @pytest.fixture
    def gate(self, db, tmp_path):
        """Create deduplication gate instance."""
        research_dir = tmp_path / "research"
        research_dir.mkdir()
        return DeduplicationGate(
            db=db,
            research_dir=research_dir,
            similarity_threshold=0.85,
            merge_threshold=0.70,
        )

    def test_gate_initialization(self, db, tmp_path):
        """Test gate initializes with correct parameters."""
        research_dir = tmp_path / "research"
        research_dir.mkdir()
        gate = DeduplicationGate(
            db=db,
            research_dir=research_dir,
            similarity_threshold=0.80,
            merge_threshold=0.65,
        )
        assert gate.similarity_threshold == 0.80
        assert gate.merge_threshold == 0.65
        assert gate.research_dir == research_dir

    def test_threshold_validation(self, db, tmp_path):
        """Test threshold validation on initialization."""
        research_dir = tmp_path / "research"
        research_dir.mkdir()

        # Invalid similarity threshold > 1.0
        with pytest.raises(ValueError, match="similarity_threshold"):
            DeduplicationGate(db=db, research_dir=research_dir, similarity_threshold=1.5)

        # Invalid merge threshold > similarity threshold
        with pytest.raises(ValueError, match="merge_threshold"):
            DeduplicationGate(
                db=db,
                research_dir=research_dir,
                similarity_threshold=0.70,
                merge_threshold=0.85,
            )

    @pytest.mark.asyncio
    async def test_no_similar_documents_creates_new(self, gate):
        """Test that no similar documents results in CREATE decision."""
        content = "Unique research findings about quantum computing"
        metadata = {
            "title": "Quantum Computing Research",
            "topics": ["quantum", "computing"],
            "purpose": "Explore quantum algorithms",
        }

        result = await gate.check_before_write(
            content=content, metadata=metadata, query="quantum computing"
        )

        assert result.action == DeduplicationAction.CREATE
        assert result.should_create is True
        assert result.target_document is None
        assert result.matches == []
        assert result.confidence == 1.0

    def test_topic_overlap_calculation(self, gate):
        """Test topic overlap scoring."""
        # Perfect overlap
        score = gate._calculate_topic_overlap(
            ["AI", "Machine Learning"], ["AI", "Machine Learning"]
        )
        assert score == 1.0

        # Partial overlap
        score = gate._calculate_topic_overlap(
            ["AI", "ML", "NLP"], ["AI", "Computer Vision"]
        )
        assert 0 < score < 1.0

        # No overlap
        score = gate._calculate_topic_overlap(
            ["AI", "ML"], ["Physics", "Chemistry"]
        )
        assert score == 0.0

        # Empty lists
        score = gate._calculate_topic_overlap([], ["AI"])
        assert score == 0.0

    def test_content_similarity_calculation(self, gate):
        """Test content similarity scoring."""
        # Identical content
        content = "machine learning algorithms artificial intelligence neural networks"
        score = gate._calculate_content_similarity(content, content)
        assert score == 1.0

        # No overlap
        score = gate._calculate_content_similarity(
            "machine learning artificial intelligence",
            "physics quantum chemistry biology",
        )
        assert score == 0.0

        # Partial overlap
        score = gate._calculate_content_similarity(
            "machine learning algorithms neural networks artificial intelligence",
            "machine learning computer vision deep learning systems",
        )
        assert 0 < score < 1.0

    def test_overall_similarity_calculation(self, gate):
        """Test overall similarity score calculation."""
        # High topic and content overlap
        score = gate._calculate_similarity(
            content="AI and machine learning algorithms",
            existing_content="AI machine learning deep learning",
            topics=["AI", "ML"],
            existing_topics=["AI", "ML"],
            search_context="artificial intelligence",
            existing_questions=["What is AI?"],
        )
        assert score > 0.5

        # No overlap at all
        score = gate._calculate_similarity(
            content="Physics and quantum mechanics",
            existing_content="Biology and genetics",
            topics=["Physics"],
            existing_topics=["Biology"],
            search_context="quantum",
            existing_questions=["What is biology?"],
        )
        assert score == 0.0

    def test_topic_overlap_description(self, gate):
        """Test human-readable topic overlap description."""
        desc = gate._get_topic_overlap(["AI", "ML"], ["AI", "Data Science"])
        assert "AI" in desc
        assert "," not in desc  # Only one overlapping topic

        desc = gate._get_topic_overlap(["AI", "ML"], ["Physics", "Chemistry"])
        assert "No topic overlap" in desc

    def test_word_extraction_for_similarity(self, gate):
        """Test word extraction filters stop words."""
        content_a = "machine learning algorithms neural networks"
        content_b = "machine learning deep learning networks"

        # Both should extract significant words
        score = gate._calculate_content_similarity(content_a, content_b)
        # Should find overlap in "machine", "learning", "networks"
        assert score > 0.5

    def test_similarity_threshold_boundaries(self, gate):
        """Test similarity threshold at decision boundaries."""
        # Test that we can distinguish between threshold levels
        assert gate.similarity_threshold == 0.85
        assert gate.merge_threshold == 0.70
        assert gate.merge_threshold < gate.similarity_threshold


class TestDeduplicationGateIntegration:
    """Integration tests for deduplication gate with document operations."""

    @pytest.fixture
    def setup(self, tmp_path):
        """Setup test environment with database and gate."""
        db_path = tmp_path / "test.db"
        research_dir = tmp_path / "research"
        research_dir.mkdir()

        db = DatabaseManager(db_path)
        db.initialize_database()

        gate = DeduplicationGate(db=db, research_dir=research_dir)

        yield {"db": db, "gate": gate, "research_dir": research_dir}

        db.close()

    @pytest.mark.asyncio
    async def test_empty_database_creates_new(self, setup):
        """Test gate creates document when database is empty."""
        gate = setup["gate"]

        result = await gate.check_before_write(
            content="New AI research findings",
            metadata={
                "title": "AI Research",
                "topics": ["AI", "ML"],
                "purpose": "Explore AI advances",
            },
            query="AI advances",
        )

        assert result.action == DeduplicationAction.CREATE
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_decision_logging(self, setup, caplog):
        """Test that gate logs decisions appropriately."""
        gate = setup["gate"]

        await gate.check_before_write(
            content="Research about AI safety",
            metadata={
                "title": "AI Safety",
                "topics": ["AI", "safety"],
                "purpose": "Safety considerations",
            },
            query="AI safety",
        )

        # Should log validation gate check
        assert "Validation gate: Checking for duplicate documents" in caplog.text


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def gate_setup(self, tmp_path):
        """Setup for edge case testing."""
        db_path = tmp_path / "test.db"
        research_dir = tmp_path / "research"
        research_dir.mkdir()

        db = DatabaseManager(db_path)
        db.initialize_database()
        gate = DeduplicationGate(db=db, research_dir=research_dir)

        yield gate
        db.close()

    @pytest.mark.asyncio
    async def test_empty_content(self, gate_setup):
        """Test gate handles empty content."""
        gate = gate_setup

        result = await gate.check_before_write(
            content="",
            metadata={"title": "Empty", "topics": []},
            query="",
        )

        # Should still return CREATE decision
        assert result.action == DeduplicationAction.CREATE

    @pytest.mark.asyncio
    async def test_empty_topics(self, gate_setup):
        """Test gate handles empty topic lists."""
        gate = gate_setup

        result = await gate.check_before_write(
            content="Some research content",
            metadata={"title": "No Topics", "topics": []},
            query="research query",
        )

        assert result.action == DeduplicationAction.CREATE

    def test_very_high_similarity_threshold(self, tmp_path):
        """Test gate with very high similarity threshold."""
        db_path = tmp_path / "test.db"
        research_dir = tmp_path / "research"
        research_dir.mkdir()

        db = DatabaseManager(db_path)
        db.initialize_database()

        gate = DeduplicationGate(
            db=db,
            research_dir=research_dir,
            similarity_threshold=0.99,  # Very high
            merge_threshold=0.95,
        )

        assert gate.similarity_threshold == 0.99

        db.close()

    def test_question_overlap_with_empty_list(self, tmp_path):
        """Test question overlap calculation with empty questions."""
        db_path = tmp_path / "test.db"
        research_dir = tmp_path / "research"
        research_dir.mkdir()

        db = DatabaseManager(db_path)
        db.initialize_database()
        gate = DeduplicationGate(db=db, research_dir=research_dir)

        score = gate._calculate_question_overlap(
            search_context="What is AI?", existing_questions=[]
        )
        assert score == 0.0

        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
