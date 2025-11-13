"""Vector store for semantic document similarity detection using ChromaDB.

Provides:
- Document embedding generation using ChromaDB
- Semantic similarity search with configurable thresholds
- Vector store management (add, update, delete, search)
- Integration with DocumentStore for metadata
"""

import json
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Raised when vector store operations fail."""

    pass


class VectorStore:
    """ChromaDB-based vector store for semantic document similarity.

    Manages document embeddings and provides semantic similarity search
    for duplicate detection and content relationship discovery.
    """

    def __init__(self, persist_dir: Optional[Path] = None) -> None:
        """Initialize the vector store.

        Args:
            persist_dir: Directory for persistent ChromaDB storage.
                        If None, uses in-memory store.

        Raises:
            VectorStoreError: If ChromaDB initialization fails.
        """
        try:
            if persist_dir:
                persist_dir.mkdir(parents=True, exist_ok=True)
                settings = Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(persist_dir),
                    anonymized_telemetry=False,
                )
                self.client = chromadb.Client(settings)
                self.persist_dir = persist_dir
            else:
                self.client = chromadb.Client()
                self.persist_dir = None

            # Get or create the main documents collection
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize vector store: {e}") from e

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Add a document to the vector store.

        Args:
            doc_id: Unique document identifier.
            content: Document content to embed.
            metadata: Optional metadata dict (title, topic, etc).

        Returns:
            The document ID.

        Raises:
            VectorStoreError: If embedding or storage fails.
        """
        if not doc_id or not content:
            raise VectorStoreError("doc_id and content are required")

        try:
            # Prepare metadata
            meta = metadata or {}
            meta["doc_id"] = doc_id
            meta["content_length"] = str(len(content))

            # Add to collection (ChromaDB handles embedding automatically)
            self.collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta],
            )
            logger.debug(f"Document {doc_id} added to vector store")
            return doc_id
        except Exception as e:
            raise VectorStoreError(
                f"Failed to add document {doc_id}: {e}"
            ) from e

    def search_similar(
        self,
        query: str,
        threshold: float = 0.85,
        limit: int = 10,
    ) -> list[tuple[str, float, dict[str, str]]]:
        """Search for documents similar to query.

        Args:
            query: Query text for semantic search.
            threshold: Similarity threshold (0.0-1.0). Matches above this
                      are returned. Higher = more strict.
            limit: Maximum number of results to return.

        Returns:
            List of tuples (doc_id, similarity_score, metadata).
            Results are sorted by similarity score (descending).

        Raises:
            VectorStoreError: If search fails.
        """
        if not query:
            raise VectorStoreError("Query text is required")

        if not 0.0 <= threshold <= 1.0:
            raise VectorStoreError("Threshold must be between 0.0 and 1.0")

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
            )

            # Results structure: ids, distances, metadatas, documents
            # ChromaDB distances are in range [0, 2] for cosine
            # Convert to similarity: similarity = 1 - distance
            matches: list[tuple[str, float, dict[str, str]]] = []

            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    # Convert distance to similarity score
                    distance = results["distances"][0][i]
                    similarity = 1 - distance
                    metadata = results["metadatas"][0][i]

                    # Apply threshold filter
                    if similarity >= threshold:
                        matches.append((doc_id, similarity, metadata))

            logger.debug(
                f"Search found {len(matches)} matches above threshold {threshold}"
            )
            return matches
        except Exception as e:
            raise VectorStoreError(f"Search failed: {e}") from e

    def update_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> None:
        """Update a document's embedding and metadata.

        Args:
            doc_id: Document ID to update.
            content: New document content.
            metadata: Updated metadata.

        Raises:
            VectorStoreError: If update fails.
        """
        if not doc_id or not content:
            raise VectorStoreError("doc_id and content are required")

        try:
            # ChromaDB update replaces the document
            meta = metadata or {}
            meta["doc_id"] = doc_id
            meta["content_length"] = str(len(content))

            self.collection.update(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta],
            )
            logger.debug(f"Document {doc_id} updated in vector store")
        except Exception as e:
            raise VectorStoreError(
                f"Failed to update document {doc_id}: {e}"
            ) from e

    def delete_document(self, doc_id: str) -> None:
        """Delete a document from the vector store.

        Args:
            doc_id: Document ID to delete.

        Raises:
            VectorStoreError: If deletion fails.
        """
        if not doc_id:
            raise VectorStoreError("doc_id is required")

        try:
            self.collection.delete(ids=[doc_id])
            logger.debug(f"Document {doc_id} deleted from vector store")
        except Exception as e:
            raise VectorStoreError(
                f"Failed to delete document {doc_id}: {e}"
            ) from e

    def get_document(self, doc_id: str) -> Optional[dict[str, str]]:
        """Retrieve a document from the vector store.

        Args:
            doc_id: Document ID to retrieve.

        Returns:
            Document metadata if found, None otherwise.

        Raises:
            VectorStoreError: If retrieval fails.
        """
        if not doc_id:
            raise VectorStoreError("doc_id is required")

        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["metadatas", "documents"],
            )

            if results["ids"] and len(results["ids"]) > 0:
                return {
                    "id": doc_id,
                    "content": results["documents"][0],
                    "metadata": results["metadatas"][0],
                }
            return None
        except Exception as e:
            raise VectorStoreError(
                f"Failed to retrieve document {doc_id}: {e}"
            ) from e

    def delete_all(self) -> None:
        """Delete all documents from the vector store.

        WARNING: This is irreversible. Use with caution.

        Raises:
            VectorStoreError: If deletion fails.
        """
        try:
            # Get all documents first
            all_docs = self.collection.get()
            if all_docs["ids"]:
                self.collection.delete(ids=all_docs["ids"])
            logger.warning("All documents deleted from vector store")
        except Exception as e:
            raise VectorStoreError(f"Failed to clear vector store: {e}") from e

    def get_collection_stats(self) -> dict[str, int]:
        """Get statistics about the vector store.

        Returns:
            Dict with collection statistics.
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": "documents",
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"total_documents": 0}

    def persist(self) -> None:
        """Persist the vector store to disk if configured with persist_dir."""
        if self.persist_dir:
            try:
                self.client.persist()
                logger.info("Vector store persisted to disk")
            except Exception as e:
                logger.error(f"Failed to persist vector store: {e}")
