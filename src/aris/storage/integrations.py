"""Integration utilities for VectorStore with DocumentStore.

Provides helper functions for seamless integration between the vector store
and the document storage layer for semantic search and duplicate detection.
"""

import logging
from pathlib import Path
from typing import Optional

from aris.storage.document_store import DocumentStore
from aris.storage.vector_store import VectorStore, VectorStoreError

logger = logging.getLogger(__name__)


class VectorStoreIntegration:
    """Integration layer between VectorStore and DocumentStore.

    Handles syncing documents between the database and vector store,
    maintaining consistency and enabling semantic search capabilities.
    """

    def __init__(
        self,
        document_store: DocumentStore,
        vector_store: VectorStore,
    ) -> None:
        """Initialize the integration layer.

        Args:
            document_store: DocumentStore instance for document metadata.
            vector_store: VectorStore instance for embeddings.
        """
        self.document_store = document_store
        self.vector_store = vector_store

    def index_document(
        self,
        doc_id: str,
        content: str,
        title: str = "",
        topic: str = "",
    ) -> None:
        """Add a document to the vector store with metadata.

        Args:
            doc_id: Unique document identifier.
            content: Document content to embed.
            title: Document title.
            topic: Document topic/category.

        Raises:
            VectorStoreError: If indexing fails.
        """
        metadata = {
            "title": title,
            "topic": topic,
        }
        self.vector_store.add_document(doc_id, content, metadata)

    def update_indexed_document(
        self,
        doc_id: str,
        content: str,
        title: str = "",
        topic: str = "",
    ) -> None:
        """Update a document's embedding and metadata.

        Args:
            doc_id: Document ID to update.
            content: Updated document content.
            title: Updated document title.
            topic: Updated document topic.

        Raises:
            VectorStoreError: If update fails.
        """
        metadata = {
            "title": title,
            "topic": topic,
        }
        self.vector_store.update_document(doc_id, content, metadata)

    def find_duplicates(
        self,
        content: str,
        threshold: float = 0.85,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Find documents similar to the given content.

        Args:
            content: Query content for semantic search.
            threshold: Similarity threshold (0.0-1.0). Default 0.85 for duplicates.
            limit: Maximum number of results to return.

        Returns:
            List of (doc_id, similarity_score) tuples sorted by score descending.

        Raises:
            VectorStoreError: If search fails.
        """
        results = self.vector_store.search_similar(
            content,
            threshold=threshold,
            limit=limit,
        )
        # Return simplified tuples with just ID and score
        return [(doc_id, score) for doc_id, score, _ in results]

    def find_related_documents(
        self,
        content: str,
        threshold: float = 0.70,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Find documents related to the given content.

        Uses a lower threshold (0.70) to find related but non-duplicate content.

        Args:
            content: Query content for semantic search.
            threshold: Similarity threshold. Default 0.70 for related content.
            limit: Maximum number of results to return.

        Returns:
            List of (doc_id, similarity_score) tuples.

        Raises:
            VectorStoreError: If search fails.
        """
        results = self.vector_store.search_similar(
            content,
            threshold=threshold,
            limit=limit,
        )
        return [(doc_id, score) for doc_id, score, _ in results]

    def remove_indexed_document(self, doc_id: str) -> None:
        """Remove a document from the vector store.

        Args:
            doc_id: Document ID to remove.

        Raises:
            VectorStoreError: If deletion fails.
        """
        self.vector_store.delete_document(doc_id)

    def get_indexing_stats(self) -> dict[str, int]:
        """Get statistics about indexed documents.

        Returns:
            Dictionary with indexing statistics.
        """
        return self.vector_store.get_collection_stats()
