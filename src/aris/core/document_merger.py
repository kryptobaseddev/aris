"""Intelligent document merging and conflict detection for ARIS.

Provides strategies for merging new research findings into existing documents:
- Append: Add new content at the end with clear separation
- Integrate: Merge intelligently by sections and metadata
- Replace: Completely replace existing content

Detects and resolves conflicts between versions:
- Metadata conflicts (confidence scores, source counts)
- Content conflicts (contradictory findings)
- Structural conflicts (topic/focus divergence)
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from aris.models.document import Document, DocumentMetadata, DocumentStatus

logger = logging.getLogger(__name__)


class MergeStrategy(str, Enum):
    """Merge strategy options."""

    APPEND = "append"  # Add new content at end
    INTEGRATE = "integrate"  # Merge intelligently
    REPLACE = "replace"  # Complete replacement


class ConflictType(str, Enum):
    """Types of conflicts detected during merge."""

    METADATA = "metadata"  # Conflicting metadata values
    CONTENT = "content"  # Contradictory findings
    STRUCTURAL = "structural"  # Topic/focus divergence
    CONFIDENCE = "confidence"  # Conflicting confidence scores


class Conflict:
    """Represents a conflict detected during document merge."""

    def __init__(
        self,
        conflict_type: ConflictType,
        field: str,
        existing_value: str,
        new_value: str,
        severity: str = "medium",
    ):
        """Initialize conflict.

        Args:
            conflict_type: Type of conflict
            field: Field/area where conflict exists
            existing_value: Value in existing document
            new_value: Value in new content
            severity: "low", "medium", "high"
        """
        self.conflict_type = conflict_type
        self.field = field
        self.existing_value = existing_value
        self.new_value = new_value
        self.severity = severity
        self.detected_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of conflict."""
        return (
            f"Conflict({self.conflict_type.value}, {self.field}, "
            f"severity={self.severity})"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "type": self.conflict_type.value,
            "field": self.field,
            "existing": str(self.existing_value),
            "new": str(self.new_value),
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
        }


class DocumentMerger:
    """Intelligent document merger with conflict detection and resolution.

    Provides strategies for merging new research findings into existing documents
    while preserving content integrity and detecting conflicts.

    Example:
        merger = DocumentMerger()
        merged_doc = merger.merge_documents(
            existing_doc,
            new_content,
            strategy="integrate"
        )
        conflicts = merger.detect_conflicts(existing_doc, new_doc)
        if conflicts:
            for conflict in conflicts:
                resolved = merger.resolve_conflict(
                    conflict,
                    resolution="prefer_new"
                )
    """

    def __init__(self):
        """Initialize document merger."""
        self.conflicts: list[Conflict] = []
        self.merge_log: list[str] = []

    def merge_documents(
        self,
        existing: Document,
        new_content: str,
        new_metadata: Optional[DocumentMetadata] = None,
        strategy: MergeStrategy = MergeStrategy.INTEGRATE,
    ) -> Document:
        """Merge new content and metadata into existing document.

        Args:
            existing: Existing document to merge into
            new_content: New content to merge
            new_metadata: Optional new metadata
            strategy: Merge strategy to use

        Returns:
            Merged Document with updated content and metadata

        Raises:
            ValueError: If strategy is invalid or merge fails
        """
        self.conflicts.clear()
        self.merge_log.clear()

        logger.info(
            f"Starting merge: strategy={strategy.value}, "
            f"doc_title='{existing.metadata.title}'"
        )

        try:
            # Create working copy
            merged = existing.model_copy(deep=True)

            # Apply merge strategy
            if strategy == MergeStrategy.REPLACE:
                merged.content = new_content
                self.merge_log.append("Applied REPLACE strategy")
            elif strategy == MergeStrategy.APPEND:
                merged = self._merge_append(merged, new_content)
            elif strategy == MergeStrategy.INTEGRATE:
                merged = self._merge_integrate(merged, new_content)
            else:
                raise ValueError(f"Unknown merge strategy: {strategy}")

            # Merge metadata if provided
            if new_metadata:
                merged = self._merge_metadata(merged, new_metadata)

            # Update timestamps
            merged.metadata.updated_at = datetime.utcnow()

            logger.info(
                f"Merge completed: {len(self.conflicts)} conflicts detected, "
                f"{len(self.merge_log)} operations"
            )

            return merged

        except Exception as e:
            logger.error(f"Merge failed: {e}", exc_info=True)
            raise ValueError(f"Document merge failed: {e}") from e

    def _merge_append(self, existing: Document, new_content: str) -> Document:
        """Append new content with clear separation.

        Args:
            existing: Existing document
            new_content: Content to append

        Returns:
            Document with appended content
        """
        separator = "\n\n---\n\n"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        header = f"## Update ({timestamp})\n\n"

        existing.content = f"{existing.content}{separator}{header}{new_content}"
        self.merge_log.append(
            f"Appended content ({len(new_content)} chars) with timestamp header"
        )

        return existing

    def _merge_integrate(self, existing: Document, new_content: str) -> Document:
        """Intelligently integrate new content by sections.

        This strategy attempts to merge content intelligently by:
        1. Parsing sections (headers) in both documents
        2. Combining matching sections
        3. Adding new sections from new_content
        4. Detecting content conflicts

        Args:
            existing: Existing document
            new_content: Content to integrate

        Returns:
            Document with integrated content
        """
        existing_sections = self._extract_sections(existing.content)
        new_sections = self._extract_sections(new_content)

        # Merge sections
        merged_sections = existing_sections.copy()
        integrated_count = 0
        new_section_count = 0

        for new_section_title, new_section_content in new_sections.items():
            if new_section_title in merged_sections:
                # Section exists - detect conflicts
                conflicts = self._detect_content_conflicts(
                    merged_sections[new_section_title],
                    new_section_content,
                )

                if conflicts:
                    for conflict in conflicts:
                        self.conflicts.append(conflict)
                        logger.warning(f"Conflict detected: {conflict}")

                # Merge section content (append for safety)
                merged_sections[new_section_title] = (
                    f"{merged_sections[new_section_title]}\n\n"
                    f"### Updated Findings\n\n{new_section_content}"
                )
                integrated_count += 1
            else:
                # New section - add it
                merged_sections[new_section_title] = new_section_content
                new_section_count += 1

        # Reconstruct document
        rebuilt_content = self._rebuild_content(merged_sections)
        existing.content = rebuilt_content

        self.merge_log.append(
            f"Integrated {integrated_count} sections, added {new_section_count} new"
        )

        return existing

    def _merge_metadata(
        self, existing: Document, new_metadata: DocumentMetadata
    ) -> Document:
        """Merge metadata from new document into existing.

        Args:
            existing: Existing document
            new_metadata: New metadata to merge

        Returns:
            Document with merged metadata
        """
        # Detect metadata conflicts
        conflicts = self._detect_metadata_conflicts(
            existing.metadata, new_metadata
        )

        for conflict in conflicts:
            self.conflicts.append(conflict)
            logger.warning(f"Metadata conflict: {conflict}")

        # Update metadata fields
        if new_metadata.topics:
            # Merge topics (avoid duplicates)
            existing_topics = set(existing.metadata.topics)
            new_topics = set(new_metadata.topics)
            merged_topics = list(existing_topics | new_topics)
            existing.metadata.topics = merged_topics
            self.merge_log.append(f"Merged topics: {merged_topics}")

        if new_metadata.questions_answered:
            # Merge questions
            existing_questions = set(existing.metadata.questions_answered)
            new_questions = set(new_metadata.questions_answered)
            merged_questions = list(existing_questions | new_questions)
            existing.metadata.questions_answered = merged_questions
            self.merge_log.append(
                f"Merged questions: {len(merged_questions)} total"
            )

        # Update confidence (use higher value)
        if new_metadata.confidence > existing.metadata.confidence:
            self.merge_log.append(
                f"Updated confidence: "
                f"{existing.metadata.confidence:.2f} -> {new_metadata.confidence:.2f}"
            )
            existing.metadata.confidence = new_metadata.confidence

        # Update source count
        if new_metadata.source_count > 0:
            existing.metadata.source_count += new_metadata.source_count
            self.merge_log.append(
                f"Updated source count: {existing.metadata.source_count}"
            )

        # Update status if new is more advanced
        status_progression = {
            DocumentStatus.DRAFT: 0,
            DocumentStatus.RESEARCHING: 1,
            DocumentStatus.VALIDATING: 2,
            DocumentStatus.REVIEWED: 3,
            DocumentStatus.DEPRECATED: 4,
        }

        if (
            status_progression.get(new_metadata.status, 0)
            > status_progression.get(existing.metadata.status, 0)
        ):
            existing.metadata.status = new_metadata.status
            self.merge_log.append(f"Updated status: {new_metadata.status.value}")

        return existing

    def detect_conflicts(
        self, doc1: Document, doc2: Document
    ) -> list[Conflict]:
        """Detect conflicts between two documents.

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Detect metadata conflicts
        conflicts.extend(self._detect_metadata_conflicts(doc1.metadata, doc2.metadata))

        # Detect content conflicts
        conflicts.extend(
            self._detect_content_conflicts(doc1.content, doc2.content)
        )

        # Detect structural conflicts (topic divergence)
        structural_conflicts = self._detect_structural_conflicts(
            doc1.metadata, doc2.metadata
        )
        conflicts.extend(structural_conflicts)

        return conflicts

    def _detect_metadata_conflicts(
        self, meta1: DocumentMetadata, meta2: DocumentMetadata
    ) -> list[Conflict]:
        """Detect conflicts in metadata.

        Args:
            meta1: First metadata
            meta2: Second metadata

        Returns:
            List of metadata conflicts
        """
        conflicts = []

        # Confidence conflict
        if abs(meta1.confidence - meta2.confidence) > 0.15:
            severity = "high" if abs(meta1.confidence - meta2.confidence) > 0.3 else "medium"
            conflicts.append(
                Conflict(
                    ConflictType.CONFIDENCE,
                    "confidence",
                    f"{meta1.confidence:.2f}",
                    f"{meta2.confidence:.2f}",
                    severity=severity,
                )
            )

        # Purpose conflict (if significantly different)
        if meta1.purpose.lower() != meta2.purpose.lower():
            conflicts.append(
                Conflict(
                    ConflictType.METADATA,
                    "purpose",
                    meta1.purpose,
                    meta2.purpose,
                    severity="medium",
                )
            )

        return conflicts

    def _detect_content_conflicts(
        self, content1: str, content2: str
    ) -> list[Conflict]:
        """Detect conflicts in content (contradictions).

        Args:
            content1: First content
            content2: Second content

        Returns:
            List of content conflicts
        """
        conflicts = []

        # Simple heuristic: look for contradictory statements
        # Keywords that suggest opposing statements
        opposing_pairs = [
            ("supports", "contradicts"),
            ("true", "false"),
            ("yes", "no"),
            ("increased", "decreased"),
            ("improvement", "degradation"),
        ]

        for keyword1, keyword2 in opposing_pairs:
            has_in_1_kw1 = keyword1.lower() in content1.lower()
            has_in_1_kw2 = keyword2.lower() in content1.lower()
            has_in_2_kw1 = keyword1.lower() in content2.lower()
            has_in_2_kw2 = keyword2.lower() in content2.lower()

            # Possible contradiction if one has keyword1 and other has keyword2
            if (has_in_1_kw1 and has_in_2_kw2) or (has_in_1_kw2 and has_in_2_kw1):
                # This is a heuristic - might be false positive
                # Only flag if confidence is reasonable
                conflicts.append(
                    Conflict(
                        ConflictType.CONTENT,
                        f"opposing_{keyword1}_{keyword2}",
                        f"Contains '{keyword1}'",
                        f"Contains '{keyword2}'",
                        severity="low",
                    )
                )
                break  # Only report one conflict per pair

        return conflicts

    def _detect_structural_conflicts(
        self, meta1: DocumentMetadata, meta2: DocumentMetadata
    ) -> list[Conflict]:
        """Detect structural conflicts (significant topic divergence).

        Args:
            meta1: First metadata
            meta2: Second metadata

        Returns:
            List of structural conflicts
        """
        conflicts = []

        # Check topic overlap
        topics1 = set(meta1.topics) if meta1.topics else set()
        topics2 = set(meta2.topics) if meta2.topics else set()

        if topics1 and topics2:
            overlap = len(topics1 & topics2)
            total = len(topics1 | topics2)

            if total > 0:
                overlap_ratio = overlap / total
                if overlap_ratio < 0.3:  # Less than 30% overlap
                    conflicts.append(
                        Conflict(
                            ConflictType.STRUCTURAL,
                            "topic_divergence",
                            f"Topics: {', '.join(topics1)}",
                            f"Topics: {', '.join(topics2)}",
                            severity="medium",
                        )
                    )

        return conflicts

    def resolve_conflict(
        self, conflict: Conflict, resolution: str
    ) -> str:
        """Resolve a detected conflict.

        Args:
            conflict: Conflict to resolve
            resolution: Resolution strategy ("prefer_existing", "prefer_new", "manual")

        Returns:
            Resolved value based on strategy

        Raises:
            ValueError: If resolution strategy is invalid
        """
        if resolution == "prefer_existing":
            result = str(conflict.existing_value)
        elif resolution == "prefer_new":
            result = str(conflict.new_value)
        elif resolution == "manual":
            # In real implementation, would prompt user
            # For now, prefer new
            result = str(conflict.new_value)
        else:
            raise ValueError(f"Unknown resolution strategy: {resolution}")

        logger.info(
            f"Resolved conflict {conflict.conflict_type.value}: "
            f"'{conflict.existing_value}' -> '{result}'"
        )
        return result

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract sections from markdown content by headers.

        Args:
            content: Markdown content

        Returns:
            Dictionary of {section_title: section_content}
        """
        sections = {}
        current_section = "Introduction"
        current_content = []

        for line in content.split("\n"):
            if line.startswith("##"):
                # Found new section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                    current_content = []

                # Extract section title
                current_section = line.replace("##", "").replace("#", "").strip()
            else:
                current_content.append(line)

        # Add last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _rebuild_content(self, sections: dict[str, str]) -> str:
        """Rebuild content from sections dictionary.

        Args:
            sections: Dictionary of {section_title: section_content}

        Returns:
            Reconstructed markdown content
        """
        lines = []

        for section_title, section_content in sections.items():
            if section_title and section_content:
                lines.append(f"## {section_title}")
                lines.append("")
                lines.append(section_content)
                lines.append("")

        return "\n".join(lines).strip()

    def get_merge_report(self) -> dict:
        """Get detailed report of merge operations.

        Returns:
            Dictionary with merge statistics and logs
        """
        return {
            "conflicts_detected": len(self.conflicts),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "operations": self.merge_log,
            "operation_count": len(self.merge_log),
            "timestamp": datetime.utcnow().isoformat(),
        }
