"""Pre-write validation gate for intelligent document deduplication.

Implements semantic similarity detection and intelligent decision-making
to determine whether to CREATE new documents or UPDATE existing ones.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from aris.models.document import Document, DocumentMetadata
from aris.storage.database import DatabaseManager
from aris.storage.vector_store import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)


class DeduplicationAction(str, Enum):
    """Deduplication gate decision actions."""

    CREATE = "create"
    UPDATE = "update"
    MERGE = "merge"


@dataclass
class SimilarityMatch:
    """Result of a similarity comparison between documents.

    Attributes:
        document: The matching document
        similarity_score: Similarity score (0.0-1.0)
        reason: Explanation of why this document matched
    """

    document: Document
    similarity_score: float = field(default=0.0)
    reason: str = field(default="")

    def __post_init__(self) -> None:
        """Validate similarity score."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(
                f"Similarity score must be 0.0-1.0, got {self.similarity_score}"
            )


@dataclass
class DeduplicationResult:
    """Result of deduplication gate validation.

    Attributes:
        action: Decision action (CREATE | UPDATE | MERGE)
        target_document: Document to update if action is UPDATE/MERGE
        matches: List of similar documents found
        confidence: Confidence in the decision (0.0-1.0)
        reason: Explanation of the decision
        recommendation: Additional recommendation for the user
    """

    action: DeduplicationAction
    target_document: Optional[Document] = None
    matches: list[SimilarityMatch] = field(default_factory=list)
    confidence: float = field(default=0.0)
    reason: str = field(default="")
    recommendation: str = field(default="")

    def __post_init__(self) -> None:
        """Validate result state."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        if self.action in (
            DeduplicationAction.UPDATE,
            DeduplicationAction.MERGE,
        ):
            if self.target_document is None:
                raise ValueError(
                    f"action {self.action} requires target_document to be set"
                )

    @property
    def should_update(self) -> bool:
        """Check if gate recommends updating existing document."""
        return self.action in (DeduplicationAction.UPDATE, DeduplicationAction.MERGE)

    @property
    def should_create(self) -> bool:
        """Check if gate recommends creating new document."""
        return self.action == DeduplicationAction.CREATE


class DeduplicationGate:
    """Pre-write validation gate for intelligent document deduplication.

    Analyzes incoming content for semantic similarity with existing
    documents and makes intelligent decisions about document creation
    vs. updates based on configurable thresholds and strategies.

    Example:
        gate = DeduplicationGate(db, research_dir)
        result = await gate.check_before_write(
            content="New research findings on AI safety",
            metadata={"topics": ["AI", "safety"]},
            query="AI safety considerations"
        )
        if result.should_update:
            # Merge with existing document
            print(f"Merge with {result.target_document.metadata.title}")
    """

    def __init__(
        self,
        db: DatabaseManager,
        research_dir: Path,
        similarity_threshold: float = 0.85,
        merge_threshold: float = 0.70,
        vector_store: Optional[VectorStore] = None,
    ):
        """Initialize deduplication gate.

        Args:
            db: Database manager instance
            research_dir: Research directory path
            similarity_threshold: Threshold for UPDATE decision (0.85 default)
            merge_threshold: Threshold for MERGE consideration (0.70 default)
            vector_store: Optional VectorStore for semantic similarity search

        Raises:
            ValueError: If thresholds are invalid
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be 0.0-1.0, got {similarity_threshold}"
            )
        if not 0.0 <= merge_threshold <= 1.0:
            raise ValueError(
                f"merge_threshold must be 0.0-1.0, got {merge_threshold}"
            )
        if merge_threshold > similarity_threshold:
            raise ValueError(
                f"merge_threshold ({merge_threshold}) must be <= "
                f"similarity_threshold ({similarity_threshold})"
            )

        self.db = db
        self.research_dir = research_dir
        self.similarity_threshold = similarity_threshold
        self.merge_threshold = merge_threshold
        self.vector_store = vector_store

    async def check_before_write(
        self,
        content: str,
        metadata: dict,
        query: str = "",
    ) -> DeduplicationResult:
        """Validate content before writing and decide CREATE vs UPDATE.

        Performs semantic similarity analysis to detect duplicate or
        highly similar documents. Makes intelligent decision based on:
        - Content similarity score
        - Topic overlap
        - Temporal factors
        - Configurable thresholds

        Args:
            content: Document content to validate
            metadata: Document metadata dict
            query: Original research query (optional, for context)

        Returns:
            DeduplicationResult with decision and supporting data
        """
        logger.info("Validation gate: Checking for duplicate documents")

        # Extract search context from metadata or query
        topics = metadata.get("topics", [])
        search_context = query or metadata.get("purpose", "")

        # Find similar documents using basic content and topic matching
        similar_docs = await self._find_similar_documents(
            content=content, topics=topics, search_context=search_context
        )

        # If no similar documents found, decision is to CREATE
        if not similar_docs:
            logger.info("Validation gate: No similar documents found - creating new")
            return DeduplicationResult(
                action=DeduplicationAction.CREATE,
                matches=[],
                confidence=1.0,
                reason="No documents with similar content or topics found",
                recommendation="Creating new document",
            )

        # Analyze best match
        best_match = similar_docs[0]

        # Decision logic based on similarity thresholds
        if best_match.similarity_score >= self.similarity_threshold:
            logger.warning(
                f"Validation gate: High similarity ({best_match.similarity_score:.2f}) "
                f"with '{best_match.document.metadata.title}' - recommend UPDATE"
            )
            return DeduplicationResult(
                action=DeduplicationAction.UPDATE,
                target_document=best_match.document,
                matches=similar_docs,
                confidence=best_match.similarity_score,
                reason=(
                    f"High similarity ({best_match.similarity_score:.2%}) detected with "
                    f"existing document: {best_match.document.metadata.title}"
                ),
                recommendation=(
                    f"Update existing document instead of creating duplicate. "
                    f"Merge strategy: Append new findings to existing research."
                ),
            )

        # Merge consideration threshold
        if best_match.similarity_score >= self.merge_threshold:
            logger.info(
                f"Validation gate: Moderate similarity ({best_match.similarity_score:.2f}) "
                f"with '{best_match.document.metadata.title}' - recommend MERGE"
            )
            return DeduplicationResult(
                action=DeduplicationAction.MERGE,
                target_document=best_match.document,
                matches=similar_docs,
                confidence=best_match.similarity_score,
                reason=(
                    f"Moderate similarity ({best_match.similarity_score:.2%}) with "
                    f"'{best_match.document.metadata.title}' - recommend integration"
                ),
                recommendation=(
                    f"Consider merging with existing document. "
                    f"Document contains {best_match.similarity_score:.0%} overlapping content."
                ),
            )

        # Low similarity - create new document
        logger.info(
            f"Validation gate: Low similarity ({best_match.similarity_score:.2f}) - "
            f"creating new document"
        )
        return DeduplicationResult(
            action=DeduplicationAction.CREATE,
            matches=similar_docs,
            confidence=1.0 - best_match.similarity_score,
            reason=(
                f"Low similarity with existing documents "
                f"(best match: {best_match.similarity_score:.2%})"
            ),
            recommendation="Creating new document with unique content",
        )

    async def _find_similar_documents(
        self,
        content: str,
        topics: list[str],
        search_context: str = "",
    ) -> list[SimilarityMatch]:
        """Find similar documents based on content and topics.

        Uses semantic similarity via VectorStore when available, otherwise
        falls back to database query with word-frequency matching.

        Args:
            content: Content to compare
            topics: Topic list to match
            search_context: Additional search context

        Returns:
            List of SimilarityMatch objects sorted by score descending
        """
        # Use vector store for semantic similarity if available
        if self.vector_store:
            try:
                # Use first 1000 chars for embedding (balance detail vs performance)
                query_text = content[:1000]

                # Get vector matches with threshold 0.0 to retrieve all, filter later
                vector_matches = self.vector_store.search_similar(
                    query=query_text,
                    threshold=0.0,
                    limit=10,
                )

                if not vector_matches:
                    logger.debug("Vector store search returned no matches")
                    return []

                similar_matches = []

                for doc_id, vector_similarity, metadata in vector_matches:
                    # Load document from filesystem
                    doc_path = Path(metadata.get("file_path", ""))
                    if not doc_path.exists():
                        logger.debug(f"Document file not found: {doc_path}")
                        continue

                    try:
                        with open(doc_path, "r", encoding="utf-8") as f:
                            doc_content = f.read()

                        # Load document to access full metadata
                        existing_doc = self._load_document_from_content(
                            doc_path, doc_content
                        )

                        # Combine vector similarity with topic/question overlap for final score
                        topic_score = self._calculate_topic_overlap(
                            topics, existing_doc.metadata.topics
                        )
                        question_score = self._calculate_question_overlap(
                            search_context, existing_doc.metadata.questions_answered
                        )

                        # Weighted combination: 60% vector, 30% topic, 10% question
                        final_score = (
                            vector_similarity * 0.6
                            + topic_score * 0.3
                            + question_score * 0.1
                        )

                        if final_score > 0.0:
                            similar_matches.append(
                                SimilarityMatch(
                                    document=existing_doc,
                                    similarity_score=final_score,
                                    reason=(
                                        f"Semantic similarity: {vector_similarity:.2%}, "
                                        f"Topic overlap: {self._get_topic_overlap(topics, existing_doc.metadata.topics)}"
                                    ),
                                )
                            )
                    except Exception as e:
                        logger.debug(f"Error processing document {doc_path}: {e}")
                        continue

                # Sort by similarity score (descending)
                similar_matches.sort(key=lambda m: m.similarity_score, reverse=True)
                return similar_matches

            except VectorStoreError as e:
                logger.warning(
                    f"Vector store search failed, falling back to database: {e}"
                )
                # Fall through to database fallback below

        # Fallback: Database query with word-frequency matching
        try:
            # Get all existing documents from database
            with self.db.session_scope() as session:
                from aris.storage.models import Document as DocumentModel

                existing_docs = session.query(DocumentModel).all()

            similar_matches = []

            for db_doc in existing_docs:
                # Load document from filesystem
                doc_path = Path(db_doc.file_path)
                if not doc_path.exists():
                    logger.debug(f"Document file not found: {doc_path}")
                    continue

                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        doc_content = f.read()

                    # Load document to access metadata
                    existing_doc = self._load_document_from_content(
                        doc_path, doc_content
                    )

                    # Calculate similarity score
                    score = self._calculate_similarity(
                        content=content,
                        existing_content=existing_doc.content,
                        topics=topics,
                        existing_topics=existing_doc.metadata.topics,
                        search_context=search_context,
                        existing_questions=existing_doc.metadata.questions_answered,
                    )

                    if score > 0.0:
                        similar_matches.append(
                            SimilarityMatch(
                                document=existing_doc,
                                similarity_score=score,
                                reason=(
                                    f"Topic overlap: {self._get_topic_overlap(topics, existing_doc.metadata.topics)}"
                                ),
                            )
                        )
                except Exception as e:
                    logger.debug(f"Error processing document {doc_path}: {e}")
                    continue

            # Sort by similarity score (descending)
            similar_matches.sort(key=lambda m: m.similarity_score, reverse=True)
            return similar_matches

        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []

    def _calculate_similarity(
        self,
        content: str,
        existing_content: str,
        topics: list[str],
        existing_topics: list[str],
        search_context: str = "",
        existing_questions: list[str] = None,
    ) -> float:
        """Calculate overall similarity score between documents.

        Uses weighted combination of:
        - Topic overlap (40%)
        - Content similarity (40%)
        - Question overlap (20%)

        Args:
            content: New document content
            existing_content: Existing document content
            topics: New document topics
            existing_topics: Existing document topics
            search_context: Search context for matching
            existing_questions: Existing document questions answered

        Returns:
            Similarity score 0.0-1.0
        """
        if existing_questions is None:
            existing_questions = []

        # Topic overlap score (0.0-1.0)
        topic_score = self._calculate_topic_overlap(topics, existing_topics)

        # Content similarity score (simple word frequency comparison)
        content_score = self._calculate_content_similarity(
            content, existing_content, search_context
        )

        # Question overlap score
        question_score = self._calculate_question_overlap(
            search_context, existing_questions
        )

        # Weighted combination
        total_score = (topic_score * 0.4) + (content_score * 0.4) + (question_score * 0.2)

        return min(1.0, max(0.0, total_score))

    def _calculate_topic_overlap(
        self, topics_a: list[str], topics_b: list[str]
    ) -> float:
        """Calculate topic overlap percentage.

        Args:
            topics_a: First topic list
            topics_b: Second topic list

        Returns:
            Overlap score 0.0-1.0
        """
        if not topics_a or not topics_b:
            return 0.0

        set_a = set(t.lower() for t in topics_a)
        set_b = set(t.lower() for t in topics_b)

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0

    def _calculate_content_similarity(
        self, content_a: str, content_b: str, context: str = ""
    ) -> float:
        """Calculate content similarity using word frequency.

        Simple approach: measure overlap of significant words.

        Args:
            content_a: First content
            content_b: Second content
            context: Context words to emphasize

        Returns:
            Similarity score 0.0-1.0
        """
        # Extract significant words (simple approach)
        def extract_words(text: str) -> set[str]:
            """Extract significant words from text."""
            import re

            words = re.findall(r"\b\w{3,}\b", text.lower())
            # Filter out common stop words
            stopwords = {
                "the",
                "and",
                "that",
                "this",
                "with",
                "from",
                "for",
                "are",
                "was",
                "been",
                "have",
                "has",
                "also",
            }
            return {w for w in words if w not in stopwords}

        words_a = extract_words(content_a)
        words_b = extract_words(content_b)

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0

    def _calculate_question_overlap(
        self, search_context: str, existing_questions: list[str]
    ) -> float:
        """Calculate overlap between search context and existing questions.

        Args:
            search_context: Search context/query
            existing_questions: List of questions the document answers

        Returns:
            Overlap score 0.0-1.0
        """
        if not search_context or not existing_questions:
            return 0.0

        # Simple string matching (TODO: improve with semantic matching)
        context_lower = search_context.lower()
        matching_questions = sum(
            1 for q in existing_questions if q.lower() in context_lower
        )

        return min(1.0, matching_questions / len(existing_questions))

    def _get_topic_overlap(self, topics_a: list[str], topics_b: list[str]) -> str:
        """Get human-readable topic overlap description.

        Args:
            topics_a: First topic list
            topics_b: Second topic list

        Returns:
            Description of overlapping topics
        """
        set_a = set(t.lower() for t in topics_a)
        set_b = set(t.lower() for t in topics_b)
        overlap = set_a & set_b

        if not overlap:
            return "No topic overlap"

        return f"{', '.join(sorted(overlap))}"

    def _load_document_from_content(
        self, file_path: Path, content: str
    ) -> Document:
        """Load Document object from file content.

        Args:
            file_path: Path to document file
            content: Document file content

        Returns:
            Parsed Document object

        Raises:
            ValueError: If document parsing fails
        """
        from aris.models.document import Document

        return Document.from_markdown(file_path, content)
