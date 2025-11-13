"""Semantic document discovery and ranking system.

Provides intelligent document retrieval using:
- Vector similarity search for semantic deduplication
- Topic-based filtering for focused discovery
- Multi-factor ranking (relevance, recency, confidence)
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from aris.models.document import Document
from aris.storage.database import DatabaseManager
from aris.storage.document_store import DocumentStore
from aris.storage.repositories import DocumentRepository
from aris.storage.vector_store import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)


class DocumentFinderError(Exception):
    """Raised when document discovery operations fail."""

    pass


class DocumentFinder:
    """Semantic search engine for finding related documents.

    Combines vector similarity search with database queries to intelligently
    locate existing documents before creating new ones. Ranks results by
    relevance, recency, and confidence score.

    Attributes:
        vector_store: VectorStore instance for semantic similarity
        db: DatabaseManager for database access
        document_store: DocumentStore for file operations

    Example:
        finder = DocumentFinder(config)
        similar = finder.find_similar_documents("AI safety", threshold=0.85)
        for doc, score in similar:
            print(f"{doc.metadata.title}: {score:.2%}")
    """

    def __init__(
        self,
        config,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        """Initialize document finder.

        Args:
            config: ARIS configuration with database_path and research_dir
            vector_store: Optional VectorStore instance. If None, creates new one.

        Raises:
            DocumentFinderError: If initialization fails
        """
        self.config = config
        self.db = DatabaseManager(Path(config.database_path))
        self.document_store = DocumentStore(config)

        # Initialize vector store
        try:
            if vector_store:
                self.vector_store = vector_store
            else:
                # Use persistent vector store in .aris/vectors directory
                vector_dir = Path(config.research_dir).parent / ".aris" / "vectors"
                self.vector_store = VectorStore(persist_dir=vector_dir)
            logger.info("Document finder initialized")
        except Exception as e:
            raise DocumentFinderError(f"Failed to initialize vector store: {e}") from e

    def find_similar_documents(
        self,
        query: str,
        threshold: float = 0.85,
        limit: int = 10,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[tuple[Document, float]]:
        """Find documents semantically similar to query.

        Performs vector similarity search using ChromaDB embeddings.
        Returns documents ranked by semantic similarity score.

        Args:
            query: Search query text
            threshold: Minimum similarity score (0.0-1.0). Default 0.85 is strict.
                      Lower values (e.g., 0.70) return more results.
            limit: Maximum number of results to return
            exclude_ids: Document IDs to exclude from results

        Returns:
            List of (Document, similarity_score) tuples sorted by score (highest first)

        Raises:
            DocumentFinderError: If search fails
        """
        if not query or not query.strip():
            raise DocumentFinderError("Query text cannot be empty")

        exclude_ids = exclude_ids or []

        try:
            # Search vector store for similar content
            vector_matches = self.vector_store.search_similar(
                query=query,
                threshold=threshold,
                limit=limit * 2,  # Get more to filter
            )

            if not vector_matches:
                logger.debug(f"No similar documents found for query: {query}")
                return []

            # Load full document objects from database
            results: list[tuple[Document, float]] = []
            for doc_id, similarity_score, metadata in vector_matches:
                # Skip excluded documents
                if doc_id in exclude_ids:
                    continue

                # Load from database
                with self.db.session_scope() as session:
                    repo = DocumentRepository(session)
                    db_doc = repo.get_by_id(doc_id)

                if db_doc and db_doc.file_path:
                    try:
                        # Load file content to create Document object
                        file_path = Path(db_doc.file_path)
                        if file_path.exists():
                            doc = self.document_store.load_document(file_path)
                            results.append((doc, similarity_score))
                    except Exception as e:
                        logger.warning(
                            f"Failed to load document {doc_id}: {e}. Skipping."
                        )

            # Sort by similarity score (highest first)
            results.sort(key=lambda x: x[1], reverse=True)

            # Limit results
            results = results[:limit]

            logger.info(
                f"Found {len(results)} similar documents for query with threshold {threshold}"
            )
            return results

        except VectorStoreError as e:
            raise DocumentFinderError(f"Vector similarity search failed: {e}") from e
        except Exception as e:
            raise DocumentFinderError(f"Document search failed: {e}") from e

    def find_by_topics(
        self,
        topics: list[str],
        status: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> list[Document]:
        """Find documents by topic tags.

        Queries database for documents matching specified topics.
        Results are filtered by status and confidence, then sorted by recency.

        Args:
            topics: List of topic strings to search for
            status: Optional status filter (draft | review | published | archived)
            min_confidence: Minimum confidence score filter (0.0-1.0)
            limit: Maximum number of results to return

        Returns:
            List of Document objects sorted by recency (newest first)

        Raises:
            DocumentFinderError: If query fails
        """
        if not topics:
            raise DocumentFinderError("At least one topic is required")

        try:
            with self.db.session_scope() as session:
                repo = DocumentRepository(session)

                # Get all documents (no direct topic filter in DB)
                # Will implement advanced topic filtering
                all_docs = []

                # For now, search by title/content for topic relevance
                # Future: Add document_topics table for efficient filtering
                for topic in topics:
                    topic_docs = repo.search_by_title(topic)
                    all_docs.extend(topic_docs)

                # Remove duplicates (same document from multiple topics)
                seen_ids = set()
                unique_docs = []
                for doc in all_docs:
                    if doc.id not in seen_ids:
                        seen_ids.add(doc.id)
                        unique_docs.append(doc)

                # Filter by confidence
                filtered = [
                    doc for doc in unique_docs if doc.confidence >= min_confidence
                ]

                # Filter by status if provided
                if status:
                    filtered = [doc for doc in filtered if doc.status == status]

                # Sort by recency (newest first)
                filtered.sort(key=lambda d: d.updated_at, reverse=True)

                # Limit results
                results = filtered[:limit]

                logger.info(
                    f"Found {len(results)} documents for topics: {', '.join(topics)}"
                )
                return results

        except Exception as e:
            raise DocumentFinderError(f"Topic search failed: {e}") from e

    def rank_by_relevance(
        self,
        documents: list[tuple[Document, float]],
        query: str,
        recency_weight: float = 0.2,
    ) -> list[tuple[Document, float]]:
        """Re-rank documents using multi-factor scoring.

        Combines semantic similarity with:
        - Document recency (how recently updated)
        - Confidence score (research quality)
        - Content length (more comprehensive documents ranked higher)

        Args:
            documents: List of (Document, similarity_score) tuples
            query: Original search query for context
            recency_weight: Weight for recency in final score (0.0-1.0)

        Returns:
            Re-ranked list of (Document, final_score) tuples

        Raises:
            DocumentFinderError: If ranking fails
        """
        if not documents:
            return []

        try:
            scored = []

            now = datetime.utcnow()
            thirty_days = timedelta(days=30)

            for doc, sim_score in documents:
                # Start with similarity score
                final_score = sim_score

                # Add recency factor
                if recency_weight > 0:
                    age = now - doc.metadata.updated_at
                    # Documents updated recently get bonus
                    if age <= thirty_days:
                        recency_boost = 0.1 * (1 - age.days / 30)
                        final_score += recency_boost * recency_weight

                # Add confidence factor
                confidence_boost = doc.metadata.confidence * 0.1
                final_score += confidence_boost

                # Add content length factor (longer = more comprehensive)
                content_length = len(doc.content)
                if content_length > 500:
                    length_boost = min(0.05, content_length / 10000)
                    final_score += length_boost

                scored.append((doc, min(final_score, 1.0)))

            # Sort by final score
            scored.sort(key=lambda x: x[1], reverse=True)

            logger.debug(f"Re-ranked {len(scored)} documents")
            return scored

        except Exception as e:
            raise DocumentFinderError(f"Ranking failed: {e}") from e

    def get_related_documents(
        self,
        doc_id: str,
        limit: int = 5,
    ) -> list[Document]:
        """Get documents related to a specific document.

        Returns documents linked via relationship table and
        semantically similar documents.

        Args:
            doc_id: Document ID to find related documents for
            limit: Maximum results to return

        Returns:
            List of related Document objects

        Raises:
            DocumentFinderError: If operation fails
        """
        try:
            with self.db.session_scope() as session:
                repo = DocumentRepository(session)
                source_doc = repo.get_by_id(doc_id)

                if not source_doc:
                    raise DocumentFinderError(f"Document not found: {doc_id}")

                related = set()

                # Get explicitly linked documents
                if source_doc.outgoing_relationships:
                    for rel in source_doc.outgoing_relationships:
                        if rel.target_document:
                            related.add(rel.target_document)

                if source_doc.incoming_relationships:
                    for rel in source_doc.incoming_relationships:
                        if rel.source_document:
                            related.add(rel.source_document)

                # Get semantically similar documents
                if source_doc.file_path:
                    try:
                        content = Path(source_doc.file_path).read_text()
                        similar = self.find_similar_documents(
                            query=content,
                            threshold=0.75,
                            limit=limit,
                            exclude_ids=[doc_id],
                        )
                        for doc, _ in similar:
                            related.add(doc)
                    except Exception as e:
                        logger.warning(f"Failed to find similar docs: {e}")

                # Convert to list and limit
                result = list(related)[:limit]
                logger.info(f"Found {len(result)} related documents")
                return result

        except DocumentFinderError:
            raise
        except Exception as e:
            raise DocumentFinderError(f"Failed to get related documents: {e}") from e

    def index_document(self, doc_id: str, content: str) -> None:
        """Add or update document in vector index.

        Args:
            doc_id: Document ID
            content: Document content to index

        Raises:
            DocumentFinderError: If indexing fails
        """
        if not doc_id or not content:
            raise DocumentFinderError("doc_id and content are required")

        try:
            self.vector_store.add_document(
                doc_id=doc_id,
                content=content,
                metadata={"indexed_at": datetime.utcnow().isoformat()},
            )
            logger.debug(f"Document {doc_id} indexed")
        except VectorStoreError as e:
            raise DocumentFinderError(f"Failed to index document: {e}") from e

    def deindex_document(self, doc_id: str) -> None:
        """Remove document from vector index.

        Args:
            doc_id: Document ID to remove

        Raises:
            DocumentFinderError: If removal fails
        """
        if not doc_id:
            raise DocumentFinderError("doc_id is required")

        try:
            self.vector_store.delete_document(doc_id)
            logger.debug(f"Document {doc_id} removed from index")
        except VectorStoreError as e:
            raise DocumentFinderError(f"Failed to deindex document: {e}") from e

    def get_search_stats(self) -> dict:
        """Get statistics about indexed documents.

        Returns:
            Dictionary with collection statistics
        """
        try:
            return self.vector_store.get_collection_stats()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"total_documents": 0, "error": str(e)}

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        try:
            self.vector_store.persist()
        except Exception as e:
            logger.error(f"Failed to persist vector store: {e}")
