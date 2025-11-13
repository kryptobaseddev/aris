"""Tests for DocumentMerger and merge strategies."""

import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from aris.core.document_merger import (
    DocumentMerger,
    MergeStrategy,
    Conflict,
    ConflictType,
)
from aris.models.document import (
    Document,
    DocumentMetadata,
    DocumentStatus,
)


@pytest.fixture
def merger():
    """Create a fresh DocumentMerger instance."""
    return DocumentMerger()


@pytest.fixture
def existing_doc():
    """Create an existing document for testing."""
    metadata = DocumentMetadata(
        title="AI Research Overview",
        purpose="Comprehensive overview of AI developments",
        topics=["AI", "Machine Learning"],
        questions_answered=["What is AI?", "How does ML work?"],
        confidence=0.75,
        source_count=5,
        status=DocumentStatus.RESEARCHING,
    )

    return Document(
        metadata=metadata,
        content="# AI Research Overview\n\nArtificial Intelligence has made significant progress.",
        file_path=Path("/research/ai/overview.md"),
    )


@pytest.fixture
def new_content_simple():
    """Simple new content for merging."""
    return "Recent advances in neural networks show promising results."


@pytest.fixture
def new_metadata():
    """New metadata for merging."""
    return DocumentMetadata(
        title="AI Research Overview",
        purpose="Updated AI research findings",
        topics=["AI", "Deep Learning", "Neural Networks"],
        questions_answered=["What is deep learning?"],
        confidence=0.85,
        source_count=8,
        status=DocumentStatus.VALIDATING,
    )


class TestMergeStrategies:
    """Test different merge strategies."""

    def test_merge_append_strategy(self, merger, existing_doc, new_content_simple):
        """Test APPEND merge strategy."""
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            strategy=MergeStrategy.APPEND,
        )

        # Should contain both old and new content
        assert existing_doc.content in result.content
        assert new_content_simple in result.content
        assert "---" in result.content  # Separator should be present
        assert len(result.content) > len(existing_doc.content)

    def test_merge_replace_strategy(self, merger, existing_doc, new_content_simple):
        """Test REPLACE merge strategy."""
        original_content = existing_doc.content

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            strategy=MergeStrategy.REPLACE,
        )

        # Should completely replace content
        assert result.content == new_content_simple
        assert original_content not in result.content

    def test_merge_integrate_strategy(self, merger, existing_doc, new_content_simple):
        """Test INTEGRATE merge strategy."""
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            strategy=MergeStrategy.INTEGRATE,
        )

        # Should contain integrated content
        assert len(result.content) > len(existing_doc.content)
        # Integration strategy should preserve sections
        assert "## " in result.content or new_content_simple in result.content

    def test_invalid_merge_strategy(self, merger, existing_doc, new_content_simple):
        """Test that invalid strategy raises error."""
        with pytest.raises(ValueError):
            merger.merge_documents(
                existing_doc,
                new_content_simple,
                strategy="invalid_strategy",  # type: ignore
            )


class TestMetadataMerge:
    """Test metadata merging."""

    def test_merge_topics(self, merger, existing_doc, new_content_simple, new_metadata):
        """Test merging topic lists."""
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_metadata,
        )

        # Should have union of topics
        expected_topics = {"AI", "Machine Learning", "Deep Learning", "Neural Networks"}
        assert set(result.metadata.topics) == expected_topics

    def test_merge_questions(self, merger, existing_doc, new_content_simple, new_metadata):
        """Test merging questions answered."""
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_metadata,
        )

        # Should have union of questions
        expected_questions = {
            "What is AI?",
            "How does ML work?",
            "What is deep learning?",
        }
        assert set(result.metadata.questions_answered) == expected_questions

    def test_merge_confidence_higher(self, merger, existing_doc, new_content_simple):
        """Test that higher confidence is kept."""
        new_meta = DocumentMetadata(
            title="AI Research Overview",
            purpose="Updated findings",
            confidence=0.95,  # Higher than existing 0.75
        )

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_meta,
        )

        assert result.metadata.confidence == 0.95

    def test_merge_confidence_lower(self, merger, existing_doc, new_content_simple):
        """Test that lower confidence is ignored."""
        new_meta = DocumentMetadata(
            title="AI Research Overview",
            purpose="Updated findings",
            confidence=0.60,  # Lower than existing 0.75
        )

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_meta,
        )

        assert result.metadata.confidence == 0.75

    def test_merge_source_count(self, merger, existing_doc, new_content_simple, new_metadata):
        """Test that source counts are summed."""
        # Existing has 5, new has 8
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_metadata,
        )

        assert result.metadata.source_count == 13


class TestConflictDetection:
    """Test conflict detection between documents."""

    def test_detect_confidence_conflict(self, merger, existing_doc):
        """Test detection of confidence conflicts."""
        new_doc = existing_doc.model_copy(deep=True)
        new_doc.metadata.confidence = 0.30  # Significant difference from 0.75

        conflicts = merger.detect_conflicts(existing_doc, new_doc)

        # Should detect confidence conflict
        conf_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.CONFIDENCE]
        assert len(conf_conflicts) > 0
        assert conf_conflicts[0].severity == "high"

    def test_detect_purpose_conflict(self, merger, existing_doc):
        """Test detection of purpose conflicts."""
        new_doc = existing_doc.model_copy(deep=True)
        new_doc.metadata.purpose = "Completely different purpose"

        conflicts = merger.detect_conflicts(existing_doc, new_doc)

        # Should detect purpose conflict
        purpose_conflicts = [
            c for c in conflicts if c.conflict_type == ConflictType.METADATA and c.field == "purpose"
        ]
        assert len(purpose_conflicts) > 0

    def test_detect_topic_divergence(self, merger, existing_doc):
        """Test detection of structural (topic) conflicts."""
        new_doc = existing_doc.model_copy(deep=True)
        new_doc.metadata.topics = ["Quantum Computing", "Physics"]  # Completely different

        conflicts = merger.detect_conflicts(existing_doc, new_doc)

        # Should detect structural conflict due to low topic overlap
        struct_conflicts = [
            c for c in conflicts if c.conflict_type == ConflictType.STRUCTURAL
        ]
        assert len(struct_conflicts) > 0

    def test_detect_content_contradictions(self, merger):
        """Test detection of contradictory content."""
        doc1 = Document(
            metadata=DocumentMetadata(title="Test"),
            content="The results were positive and showed improvement.",
            file_path=Path("/test/doc1.md"),
        )

        doc2 = Document(
            metadata=DocumentMetadata(title="Test"),
            content="The results were negative and showed degradation.",
            file_path=Path("/test/doc2.md"),
        )

        conflicts = merger.detect_conflicts(doc1, doc2)

        # Should detect potential contradictions
        assert len(conflicts) > 0

    def test_no_conflict_similar_docs(self, merger):
        """Test that similar documents don't generate conflicts."""
        doc1 = Document(
            metadata=DocumentMetadata(
                title="Research",
                topics=["AI"],
                confidence=0.75,
            ),
            content="Initial research findings.",
            file_path=Path("/test/doc1.md"),
        )

        doc2 = Document(
            metadata=DocumentMetadata(
                title="Research",
                topics=["AI"],
                confidence=0.78,  # Close confidence
            ),
            content="Additional research findings.",
            file_path=Path("/test/doc2.md"),
        )

        conflicts = merger.detect_conflicts(doc1, doc2)

        # Minimal or no conflicts for similar documents
        assert len(conflicts) <= 1


class TestConflictResolution:
    """Test conflict resolution."""

    def test_resolve_conflict_prefer_existing(self, merger):
        """Test resolution using PREFER_EXISTING strategy."""
        conflict = Conflict(
            ConflictType.CONFIDENCE,
            "confidence",
            "0.75",
            "0.85",
        )

        result = merger.resolve_conflict(conflict, "prefer_existing")
        assert result == "0.75"

    def test_resolve_conflict_prefer_new(self, merger):
        """Test resolution using PREFER_NEW strategy."""
        conflict = Conflict(
            ConflictType.CONFIDENCE,
            "confidence",
            "0.75",
            "0.85",
        )

        result = merger.resolve_conflict(conflict, "prefer_new")
        assert result == "0.85"

    def test_resolve_conflict_manual(self, merger):
        """Test resolution using MANUAL strategy (defaults to new)."""
        conflict = Conflict(
            ConflictType.CONFIDENCE,
            "confidence",
            "0.75",
            "0.85",
        )

        result = merger.resolve_conflict(conflict, "manual")
        assert result == "0.85"

    def test_invalid_resolution_strategy(self, merger):
        """Test that invalid resolution strategy raises error."""
        conflict = Conflict(
            ConflictType.CONFIDENCE,
            "confidence",
            "0.75",
            "0.85",
        )

        with pytest.raises(ValueError):
            merger.resolve_conflict(conflict, "invalid_strategy")


class TestMergeReporting:
    """Test merge reporting and logging."""

    def test_merge_report_structure(self, merger, existing_doc, new_content_simple):
        """Test that merge report has required structure."""
        merger.merge_documents(
            existing_doc,
            new_content_simple,
            strategy=MergeStrategy.APPEND,
        )

        report = merger.get_merge_report()

        assert "conflicts_detected" in report
        assert "conflicts" in report
        assert "operations" in report
        assert "operation_count" in report
        assert "timestamp" in report

    def test_merge_log_entries(self, merger, existing_doc, new_content_simple):
        """Test that merge operations are logged."""
        merger.merge_documents(
            existing_doc,
            new_content_simple,
            strategy=MergeStrategy.APPEND,
        )

        report = merger.get_merge_report()

        assert len(report["operations"]) > 0
        assert any("Appended" in op for op in report["operations"])

    def test_conflict_recording(self, merger):
        """Test that conflicts are recorded in report."""
        doc1 = Document(
            metadata=DocumentMetadata(
                title="Test",
                confidence=0.75,
            ),
            content="Content",
            file_path=Path("/test.md"),
        )

        doc2 = Document(
            metadata=DocumentMetadata(
                title="Test",
                confidence=0.30,  # Will cause conflict
            ),
            content="Content",
            file_path=Path("/test.md"),
        )

        merger.detect_conflicts(doc1, doc2)
        report = merger.get_merge_report()

        assert report["conflicts_detected"] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_merge_empty_content(self, merger, existing_doc):
        """Test merging with empty new content."""
        result = merger.merge_documents(
            existing_doc,
            "",  # Empty content
            strategy=MergeStrategy.APPEND,
        )

        # Should handle gracefully
        assert result.content is not None

    def test_merge_preserves_metadata(self, merger, existing_doc, new_content_simple):
        """Test that merge preserves essential metadata."""
        original_id = existing_doc.metadata.id
        original_created = existing_doc.metadata.created_at

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
        )

        # Should preserve ID and creation date
        assert result.metadata.id == original_id
        assert result.metadata.created_at == original_created
        # But update the modified date
        assert result.metadata.updated_at >= original_created

    def test_merge_updates_timestamp(self, merger, existing_doc, new_content_simple):
        """Test that merge updates the updated_at timestamp."""
        original_time = existing_doc.metadata.updated_at

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
        )

        # Timestamp should be updated
        assert result.metadata.updated_at >= original_time

    def test_section_extraction(self, merger):
        """Test extraction of sections from markdown."""
        content = """## Introduction
Some intro text.

## Findings
Key findings here.

## Conclusion
Final notes."""

        sections = merger._extract_sections(content)

        assert "Introduction" in sections
        assert "Findings" in sections
        assert "Conclusion" in sections

    def test_section_reconstruction(self, merger):
        """Test reconstruction of content from sections."""
        sections = {
            "Introduction": "Intro text",
            "Findings": "Key findings",
            "Conclusion": "Final notes",
        }

        content = merger._rebuild_content(sections)

        assert "## Introduction" in content
        assert "## Findings" in content
        assert "## Conclusion" in content


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_merge_workflow(self, merger, existing_doc, new_content_simple, new_metadata):
        """Test complete merge workflow."""
        # Merge with new metadata
        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_metadata,
            strategy=MergeStrategy.INTEGRATE,
        )

        # Check all aspects of merge
        assert result.metadata.confidence == 0.85  # Higher of two
        assert result.metadata.source_count == 13  # Sum
        assert "Deep Learning" in result.metadata.topics  # Union
        assert len(result.content) > len(existing_doc.content)  # Content grown

        # Get report
        report = merger.get_merge_report()
        assert report["strategy"] == "integrate"

    def test_multiple_sequential_merges(self, merger, existing_doc):
        """Test multiple sequential merges."""
        doc = existing_doc

        # First merge
        doc = merger.merge_documents(
            doc,
            "First update content.",
            strategy=MergeStrategy.APPEND,
        )

        # Second merge
        merger2 = DocumentMerger()
        doc = merger2.merge_documents(
            doc,
            "Second update content.",
            strategy=MergeStrategy.APPEND,
        )

        # Should have accumulated content
        assert "First update" in doc.content
        assert "Second update" in doc.content

    def test_merge_with_status_progression(self, merger, existing_doc, new_content_simple):
        """Test that document status can progress during merge."""
        assert existing_doc.metadata.status == DocumentStatus.RESEARCHING

        new_metadata = DocumentMetadata(
            title="AI Research Overview",
            purpose="Finalized research",
            status=DocumentStatus.REVIEWED,  # More advanced status
        )

        result = merger.merge_documents(
            existing_doc,
            new_content_simple,
            new_metadata=new_metadata,
        )

        assert result.metadata.status == DocumentStatus.REVIEWED
