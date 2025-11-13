"""Unit tests for VectorStore."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aris.storage.vector_store import VectorStore, VectorStoreError


@pytest.fixture
def vector_store():
    """Create an in-memory vector store for testing."""
    return VectorStore(persist_dir=None)


@pytest.fixture
def persistent_vector_store(tmp_path):
    """Create a persistent vector store for testing."""
    return VectorStore(persist_dir=tmp_path / "vector_store")


class TestVectorStoreInitialization:
    """Test VectorStore initialization."""

    def test_init_in_memory(self):
        """Test creating an in-memory vector store."""
        store = VectorStore(persist_dir=None)
        assert store.client is not None
        assert store.collection is not None
        assert store.persist_dir is None

    def test_init_persistent(self, tmp_path):
        """Test creating a persistent vector store."""
        persist_dir = tmp_path / "vector_store"
        store = VectorStore(persist_dir=persist_dir)
        assert store.client is not None
        assert store.collection is not None
        assert store.persist_dir == persist_dir
        assert persist_dir.exists()

    def test_init_creates_collection(self, vector_store):
        """Test that initialization creates the documents collection."""
        stats = vector_store.get_collection_stats()
        assert stats["collection_name"] == "documents"
        assert stats["total_documents"] == 0


class TestAddDocument:
    """Test adding documents to vector store."""

    def test_add_single_document(self, vector_store):
        """Test adding a single document."""
        doc_id = "doc_001"
        content = "This is a research document about machine learning."
        metadata = {"title": "ML Research", "topic": "AI"}

        result = vector_store.add_document(doc_id, content, metadata)

        assert result == doc_id
        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 1

    def test_add_multiple_documents(self, vector_store):
        """Test adding multiple documents."""
        for i in range(3):
            vector_store.add_document(
                f"doc_{i:03d}",
                f"Content for document {i}",
                {"title": f"Document {i}"},
            )

        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 3

    def test_add_document_without_metadata(self, vector_store):
        """Test adding a document without metadata."""
        doc_id = "doc_no_meta"
        content = "Document without explicit metadata"

        result = vector_store.add_document(doc_id, content)

        assert result == doc_id
        retrieved = vector_store.get_document(doc_id)
        assert retrieved is not None
        assert retrieved["id"] == doc_id
        assert retrieved["content"] == content

    def test_add_document_with_empty_id(self, vector_store):
        """Test adding a document with empty ID raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.add_document("", "Some content")

    def test_add_document_with_empty_content(self, vector_store):
        """Test adding a document with empty content raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.add_document("doc_001", "")

    def test_add_document_preserves_metadata(self, vector_store):
        """Test that metadata is preserved when adding documents."""
        doc_id = "doc_meta_test"
        content = "Test content"
        metadata = {"title": "Test Title", "topic": "Testing", "status": "draft"}

        vector_store.add_document(doc_id, content, metadata)
        retrieved = vector_store.get_document(doc_id)

        assert retrieved is not None
        assert retrieved["metadata"]["title"] == "Test Title"
        assert retrieved["metadata"]["topic"] == "Testing"
        assert retrieved["metadata"]["status"] == "draft"


class TestSearchSimilar:
    """Test similarity search functionality."""

    @pytest.fixture(autouse=True)
    def setup_documents(self, vector_store):
        """Setup test documents for search tests."""
        docs = [
            (
                "doc_ml",
                "Machine learning is a subset of artificial intelligence "
                "that enables systems to learn from data.",
            ),
            (
                "doc_ai",
                "Artificial intelligence refers to computer systems that can "
                "perform tasks that typically require human intelligence.",
            ),
            (
                "doc_dl",
                "Deep learning uses neural networks with multiple layers to "
                "process data and make predictions.",
            ),
            (
                "doc_python",
                "Python is a high-level programming language used for web "
                "development and data science.",
            ),
        ]

        for doc_id, content in docs:
            vector_store.add_document(doc_id, content)

    def test_search_basic(self, vector_store):
        """Test basic similarity search."""
        results = vector_store.search_similar(
            "machine learning and artificial intelligence",
            threshold=0.0,
        )

        assert len(results) > 0
        for doc_id, score, metadata in results:
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
            assert doc_id is not None

    def test_search_with_threshold(self, vector_store):
        """Test search with similarity threshold."""
        results_low = vector_store.search_similar("learning", threshold=0.5)
        results_high = vector_store.search_similar("learning", threshold=0.9)

        # Higher threshold should return same or fewer results
        assert len(results_high) <= len(results_low)

    def test_search_returns_high_similarity_first(self, vector_store):
        """Test that search results are sorted by similarity (highest first)."""
        results = vector_store.search_similar(
            "machine learning neural networks",
            threshold=0.0,
            limit=10,
        )

        assert len(results) > 1
        # Verify results are sorted by similarity descending
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]

    def test_search_respects_limit(self, vector_store):
        """Test that search respects the result limit."""
        results = vector_store.search_similar(
            "artificial intelligence",
            threshold=0.0,
            limit=2,
        )

        assert len(results) <= 2

    def test_search_with_invalid_threshold(self, vector_store):
        """Test search with invalid threshold raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.search_similar("test", threshold=-0.1)

        with pytest.raises(VectorStoreError):
            vector_store.search_similar("test", threshold=1.5)

    def test_search_with_empty_query(self, vector_store):
        """Test search with empty query raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.search_similar("")

    def test_search_no_results_above_threshold(self, vector_store):
        """Test search with high threshold returning no results."""
        results = vector_store.search_similar(
            "xyz abc qwerty programming",
            threshold=0.99,
        )

        # Should return empty list, not raise error
        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_returns_metadata(self, vector_store):
        """Test that search results include metadata."""
        vector_store.add_document(
            "doc_special",
            "Special document about deep learning",
            {"title": "Deep Learning Guide", "importance": "high"},
        )

        results = vector_store.search_similar("deep learning", threshold=0.0)

        # Find our special document
        special_doc = next((r for r in results if r[0] == "doc_special"), None)
        assert special_doc is not None
        doc_id, score, metadata = special_doc
        assert metadata["title"] == "Deep Learning Guide"
        assert metadata["importance"] == "high"


class TestUpdateDocument:
    """Test updating documents."""

    def test_update_document_content(self, vector_store):
        """Test updating a document's content."""
        doc_id = "doc_update"
        original = "Original content about machine learning"
        updated = "Updated content with new information about deep learning"

        vector_store.add_document(doc_id, original)
        vector_store.update_document(doc_id, updated)

        retrieved = vector_store.get_document(doc_id)
        assert retrieved is not None
        assert retrieved["content"] == updated

    def test_update_document_metadata(self, vector_store):
        """Test updating document metadata."""
        doc_id = "doc_meta_update"
        content = "Some content"
        original_meta = {"title": "Original", "status": "draft"}
        updated_meta = {"title": "Updated", "status": "published"}

        vector_store.add_document(doc_id, content, original_meta)
        vector_store.update_document(doc_id, content, updated_meta)

        retrieved = vector_store.get_document(doc_id)
        assert retrieved["metadata"]["title"] == "Updated"
        assert retrieved["metadata"]["status"] == "published"

    def test_update_nonexistent_document(self, vector_store):
        """Test updating a non-existent document creates it."""
        doc_id = "doc_new"
        content = "New document content"

        # This should not raise an error; ChromaDB creates it if not exists
        vector_store.update_document(doc_id, content)

        retrieved = vector_store.get_document(doc_id)
        assert retrieved is not None

    def test_update_with_empty_id(self, vector_store):
        """Test update with empty ID raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.update_document("", "content")

    def test_update_with_empty_content(self, vector_store):
        """Test update with empty content raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.update_document("doc_001", "")


class TestDeleteDocument:
    """Test deleting documents."""

    def test_delete_single_document(self, vector_store):
        """Test deleting a single document."""
        doc_id = "doc_to_delete"
        vector_store.add_document(doc_id, "Content to delete")

        assert vector_store.get_document(doc_id) is not None

        vector_store.delete_document(doc_id)

        assert vector_store.get_document(doc_id) is None

    def test_delete_updates_count(self, vector_store):
        """Test that deletion updates collection count."""
        vector_store.add_document("doc_1", "Content 1")
        vector_store.add_document("doc_2", "Content 2")

        stats_before = vector_store.get_collection_stats()
        assert stats_before["total_documents"] == 2

        vector_store.delete_document("doc_1")

        stats_after = vector_store.get_collection_stats()
        assert stats_after["total_documents"] == 1

    def test_delete_with_empty_id(self, vector_store):
        """Test delete with empty ID raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.delete_document("")

    def test_delete_nonexistent_document(self, vector_store):
        """Test deleting a non-existent document doesn't raise error."""
        # ChromaDB doesn't raise an error for deleting non-existent docs
        vector_store.delete_document("nonexistent")
        # Should not raise


class TestGetDocument:
    """Test retrieving documents."""

    def test_get_existing_document(self, vector_store):
        """Test retrieving an existing document."""
        doc_id = "doc_retrieve"
        content = "Document to retrieve"
        metadata = {"title": "Retrieve Test"}

        vector_store.add_document(doc_id, content, metadata)
        result = vector_store.get_document(doc_id)

        assert result is not None
        assert result["id"] == doc_id
        assert result["content"] == content
        assert result["metadata"]["title"] == "Retrieve Test"

    def test_get_nonexistent_document(self, vector_store):
        """Test retrieving a non-existent document returns None."""
        result = vector_store.get_document("nonexistent")
        assert result is None

    def test_get_with_empty_id(self, vector_store):
        """Test get with empty ID raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.get_document("")


class TestDeleteAll:
    """Test clearing the vector store."""

    def test_delete_all_documents(self, vector_store):
        """Test deleting all documents."""
        for i in range(5):
            vector_store.add_document(f"doc_{i}", f"Content {i}")

        stats_before = vector_store.get_collection_stats()
        assert stats_before["total_documents"] == 5

        vector_store.delete_all()

        stats_after = vector_store.get_collection_stats()
        assert stats_after["total_documents"] == 0

    def test_delete_all_empty_store(self, vector_store):
        """Test delete_all on empty store doesn't raise error."""
        vector_store.delete_all()  # Should not raise
        assert vector_store.get_collection_stats()["total_documents"] == 0


class TestPersistence:
    """Test vector store persistence."""

    def test_persist_to_disk(self, persistent_vector_store):
        """Test persisting vector store to disk."""
        doc_id = "doc_persist"
        content = "Content to persist"

        persistent_vector_store.add_document(doc_id, content)
        persistent_vector_store.persist()

        # Verify file was created
        assert persistent_vector_store.persist_dir.exists()

    def test_persist_idempotent(self, persistent_vector_store):
        """Test that calling persist multiple times is safe."""
        persistent_vector_store.add_document("doc_1", "Content 1")

        # Should not raise
        persistent_vector_store.persist()
        persistent_vector_store.persist()


class TestCollectionStats:
    """Test collection statistics."""

    def test_empty_store_stats(self, vector_store):
        """Test stats on empty store."""
        stats = vector_store.get_collection_stats()

        assert stats["total_documents"] == 0
        assert stats["collection_name"] == "documents"

    def test_stats_after_adds(self, vector_store):
        """Test stats after adding documents."""
        for i in range(3):
            vector_store.add_document(f"doc_{i}", f"Content {i}")

        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 3

    def test_stats_after_delete(self, vector_store):
        """Test stats after deleting documents."""
        vector_store.add_document("doc_1", "Content 1")
        vector_store.add_document("doc_2", "Content 2")
        vector_store.delete_document("doc_1")

        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 1


class TestDuplicateDetection:
    """Test duplicate detection using similarity threshold."""

    def test_detect_near_duplicate(self, vector_store):
        """Test detecting near-duplicate documents."""
        doc_id_1 = "doc_original"
        doc_id_2 = "doc_near_dup"
        content = (
            "This is a research document about machine learning and deep neural networks. "
            "It covers the fundamentals of AI."
        )

        # Very similar content with minor variations
        similar_content = (
            "This is a research document about machine learning and deep neural networks. "
            "It covers the fundamentals of AI systems."
        )

        vector_store.add_document(doc_id_1, content)
        vector_store.add_document(doc_id_2, similar_content)

        # Search for documents similar to original
        results = vector_store.search_similar(content, threshold=0.85)

        # Should find both documents (original and near-duplicate)
        doc_ids = [r[0] for r in results]
        assert doc_id_1 in doc_ids
        assert doc_id_2 in doc_ids

    def test_no_false_duplicates(self, vector_store):
        """Test that dissimilar documents are not detected as duplicates."""
        doc_id_1 = "doc_ai"
        doc_id_2 = "doc_python"
        content_ai = (
            "Artificial intelligence is a field of computer science that aims to create "
            "intelligent machines that can perform tasks without human intervention."
        )
        content_python = (
            "Python is a high-level programming language that emphasizes code readability "
            "and has powerful standard libraries for various applications."
        )

        vector_store.add_document(doc_id_1, content_ai)
        vector_store.add_document(doc_id_2, content_python)

        # Search with high threshold (0.85 for duplicates)
        results = vector_store.search_similar(content_ai, threshold=0.85)

        # Should only find the AI document, not Python
        doc_ids = [r[0] for r in results]
        assert doc_id_1 in doc_ids
        assert doc_id_2 not in doc_ids

    def test_duplicate_threshold_edge_case(self, vector_store):
        """Test duplicate detection at threshold boundary."""
        doc_id = "doc_threshold"
        content = "Testing threshold detection for duplicate documents."

        vector_store.add_document(doc_id, content)

        # Search for exact same content
        results = vector_store.search_similar(content, threshold=0.85)

        # Should always find the exact document with very high similarity
        doc_ids = [r[0] for r in results]
        assert doc_id in doc_ids
        # The exact document should be first and have near-perfect similarity
        assert results[0][1] > 0.99
