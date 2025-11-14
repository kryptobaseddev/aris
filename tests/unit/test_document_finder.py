"""Unit tests for DocumentFinder."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from aris.core.document_finder import DocumentFinder, DocumentFinderError
from aris.models.config import ArisConfig
from aris.models.document import Document, DocumentMetadata, DocumentStatus


@pytest.fixture
def mock_config() -> ArisConfig:
    """Create mock ARIS config."""
    return ArisConfig(
        research_dir="./test_research",
        database_path="./test.db",
        tavily_api_key="test_key",
        sequential_mcp_path="npx",
    )


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create mock VectorStore."""
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    store.add_document = MagicMock()
    store.delete_document = MagicMock()
    store.get_collection_stats = MagicMock(return_value={"total_documents": 0})
    store.persist = MagicMock()
    return store


@pytest.fixture
def sample_document() -> Document:
    """Create sample Document for testing."""
    metadata = DocumentMetadata(
        title="Test Document",
        purpose="Testing document finder",
        topics=["test", "ai"],
        status=DocumentStatus.PUBLISHED,
        confidence=0.85,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return Document(
        metadata=metadata,
        content="This is test content about AI and machine learning.",
        file_path=Path("./research/test/test.md"),
    )


@pytest.fixture
def document_finder(
    mock_config: ArisConfig, mock_vector_store: MagicMock
) -> DocumentFinder:
    """Create DocumentFinder with mocked dependencies."""
    with patch(
        "aris.core.document_finder.DatabaseManager"
    ), patch(
        "aris.core.document_finder.DocumentStore"
    ):
        finder = DocumentFinder(mock_config, vector_store=mock_vector_store)
        return finder


class TestDocumentFinderInitialization:
    """Test DocumentFinder initialization."""

    def test_init_with_provided_vector_store(
        self, mock_config: ArisConfig, mock_vector_store: MagicMock
    ) -> None:
        """Test initialization with provided vector store."""
        with patch(
            "aris.core.document_finder.DatabaseManager"
        ), patch(
            "aris.core.document_finder.DocumentStore"
        ):
            finder = DocumentFinder(mock_config, vector_store=mock_vector_store)
            assert finder.vector_store is mock_vector_store
            assert finder.config is mock_config

    def test_init_without_vector_store(self, mock_config: ArisConfig) -> None:
        """Test initialization creates new vector store if not provided."""
        with patch(
            "aris.core.document_finder.DatabaseManager"
        ), patch(
            "aris.core.document_finder.DocumentStore"
        ), patch(
            "aris.core.document_finder.VectorStore"
        ) as mock_vs_class:
            finder = DocumentFinder(mock_config)
            mock_vs_class.assert_called_once()


class TestFindSimilarDocuments:
    """Test find_similar_documents method."""

    def test_find_similar_documents_with_results(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test finding similar documents returns results."""
        # Mock vector store search results
        mock_results = [("doc1", 0.92, {"title": "Related Doc"})]
        mock_vector_store.search_similar.return_value = mock_results

        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock database document
            db_doc = MagicMock()
            db_doc.id = "doc1"
            db_doc.file_path = str(Path("./research/test/doc.md"))
            mock_repo.get_by_id.return_value = db_doc

            # Mock document store load and file existence
            with patch.object(
                document_finder.document_store, "load_document"
            ) as mock_load, patch("pathlib.Path.exists", return_value=True):
                sample_doc = Document(
                    metadata=DocumentMetadata(
                        title="Test",
                        purpose="test",
                        status=DocumentStatus.PUBLISHED,
                    ),
                    content="test content",
                    file_path=Path("./research/test/doc.md"),
                )
                mock_load.return_value = sample_doc

                with patch.object(
                    document_finder.db, "session_scope"
                ) as mock_session:
                    mock_session.return_value.__enter__.return_value = MagicMock()

                    results = document_finder.find_similar_documents(
                        query="test query", threshold=0.85, limit=10
                    )

                    assert len(results) > 0
                    assert results[0][0] == sample_doc
                    assert results[0][1] == 0.92

    def test_find_similar_documents_empty_query_raises_error(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test empty query raises DocumentFinderError."""
        with pytest.raises(DocumentFinderError, match="Query text cannot be empty"):
            document_finder.find_similar_documents(query="")

    def test_find_similar_documents_no_results(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test finding with no results returns empty list."""
        mock_vector_store.search_similar.return_value = []

        results = document_finder.find_similar_documents(
            query="obscure topic", threshold=0.95
        )

        assert results == []

    def test_find_similar_documents_excludes_ids(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test exclude_ids parameter filters results."""
        mock_results = [
            ("doc1", 0.92, {"title": "Doc1"}),
            ("doc2", 0.90, {"title": "Doc2"}),
        ]
        mock_vector_store.search_similar.return_value = mock_results

        with patch(
            "aris.core.document_finder.DocumentRepository"
        ), patch.object(
            document_finder.db, "session_scope"
        ):
            # Should not be called since we exclude all docs
            results = document_finder.find_similar_documents(
                query="test", exclude_ids=["doc1", "doc2"]
            )

            assert len(results) == 0

    def test_find_similar_documents_respects_limit(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test limit parameter is respected."""
        # Return many results
        mock_results = [
            (f"doc{i}", 0.90 - i * 0.01, {"title": f"Doc{i}"})
            for i in range(20)
        ]
        mock_vector_store.search_similar.return_value = mock_results

        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            db_doc = MagicMock()
            db_doc.file_path = str(Path("./research/test/doc.md"))
            mock_repo.get_by_id.return_value = db_doc

            with patch.object(
                document_finder.document_store, "load_document"
            ) as mock_load:
                mock_load.return_value = MagicMock()

                with patch.object(
                    document_finder.db, "session_scope"
                ) as mock_session:
                    mock_session.return_value.__enter__.return_value = MagicMock()

                    results = document_finder.find_similar_documents(
                        query="test", limit=5
                    )

                    assert len(results) <= 5


class TestFindByTopics:
    """Test find_by_topics method."""

    def test_find_by_topics_empty_topics_raises_error(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test empty topics list raises DocumentFinderError."""
        with pytest.raises(DocumentFinderError, match="At least one topic is required"):
            document_finder.find_by_topics(topics=[])

    def test_find_by_topics_with_results(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test finding documents by topics."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock database documents
            doc1 = MagicMock()
            doc1.id = "doc1"
            doc1.confidence = 0.85
            doc1.status = "published"
            doc1.updated_at = datetime.utcnow()

            mock_repo.search_by_title.return_value = [doc1]

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                results = document_finder.find_by_topics(
                    topics=["AI", "ML"], status="published"
                )

                assert len(results) == 1
                assert results[0].id == "doc1"

    def test_find_by_topics_respects_confidence_filter(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test confidence score filtering."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Create documents with various confidence scores
            doc_high = MagicMock()
            doc_high.id = "high"
            doc_high.confidence = 0.90
            doc_high.status = "published"
            doc_high.updated_at = datetime.utcnow()

            doc_low = MagicMock()
            doc_low.id = "low"
            doc_low.confidence = 0.30
            doc_low.status = "published"
            doc_low.updated_at = datetime.utcnow()

            mock_repo.search_by_title.return_value = [doc_high, doc_low]

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                results = document_finder.find_by_topics(
                    topics=["AI"], min_confidence=0.80
                )

                # Only high confidence doc should be returned
                assert len(results) == 1
                assert results[0].id == "high"

    def test_find_by_topics_respects_status_filter(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test status filtering."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            doc1 = MagicMock()
            doc1.id = "doc1"
            doc1.confidence = 0.85
            doc1.status = "draft"
            doc1.updated_at = datetime.utcnow()

            doc2 = MagicMock()
            doc2.id = "doc2"
            doc2.confidence = 0.85
            doc2.status = "published"
            doc2.updated_at = datetime.utcnow()

            mock_repo.search_by_title.return_value = [doc1, doc2]

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                results = document_finder.find_by_topics(
                    topics=["AI"], status="published"
                )

                assert len(results) == 1
                assert results[0].status == "published"

    def test_find_by_topics_sorted_by_recency(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test results are sorted by recency."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            now = datetime.utcnow()
            doc_old = MagicMock()
            doc_old.id = "old"
            doc_old.confidence = 0.85
            doc_old.updated_at = now - timedelta(days=10)

            doc_new = MagicMock()
            doc_new.id = "new"
            doc_new.confidence = 0.85
            doc_new.updated_at = now

            mock_repo.search_by_title.return_value = [doc_old, doc_new]

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                results = document_finder.find_by_topics(topics=["AI"])

                # Newest should be first
                assert results[0].id == "new"
                assert results[1].id == "old"


class TestRankByRelevance:
    """Test rank_by_relevance method."""

    def test_rank_by_relevance_empty_list(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test ranking empty list returns empty."""
        results = document_finder.rank_by_relevance([], "test query")
        assert results == []

    def test_rank_by_relevance_applies_recency_boost(
        self, document_finder: DocumentFinder, sample_document: Document
    ) -> None:
        """Test recency factor boosts recent documents."""
        now = datetime.utcnow()

        # Recent document - create new instance
        recent_doc = Document(
            metadata=DocumentMetadata(
                title="Recent Document",
                purpose="test",
                confidence=0.85,
                updated_at=now,
            ),
            content="Recent content",
            file_path=Path("./research/test/recent.md"),
        )

        # Old document - create new instance
        old_doc = Document(
            metadata=DocumentMetadata(
                title="Old Document",
                purpose="test",
                confidence=0.85,
                updated_at=now - timedelta(days=60),
            ),
            content="Old content",
            file_path=Path("./research/test/old.md"),
        )

        documents = [
            (old_doc, 0.90),
            (recent_doc, 0.89),
        ]

        ranked = document_finder.rank_by_relevance(
            documents, "test", recency_weight=0.2
        )

        # Recent document should rank higher despite lower similarity
        assert ranked[0][0].metadata.updated_at > ranked[1][0].metadata.updated_at

    def test_rank_by_relevance_applies_confidence_boost(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test confidence score affects ranking."""
        high_conf_doc = Document(
            metadata=DocumentMetadata(
                title="High Confidence",
                purpose="test",
                confidence=0.95,
                updated_at=datetime.utcnow(),
            ),
            content="test",
            file_path=Path("./research/test/high.md"),
        )

        low_conf_doc = Document(
            metadata=DocumentMetadata(
                title="Low Confidence",
                purpose="test",
                confidence=0.30,
                updated_at=datetime.utcnow(),
            ),
            content="test",
            file_path=Path("./research/test/low.md"),
        )

        documents = [
            (low_conf_doc, 0.91),
            (high_conf_doc, 0.91),
        ]

        ranked = document_finder.rank_by_relevance(documents, "test")

        # High confidence should rank higher
        assert ranked[0][0].metadata.confidence > ranked[1][0].metadata.confidence

    def test_rank_by_relevance_applies_length_boost(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test content length affects ranking."""
        short_doc = Document(
            metadata=DocumentMetadata(
                title="Short",
                purpose="test",
                confidence=0.80,
                updated_at=datetime.utcnow(),
            ),
            content="short content",
            file_path=Path("./research/test/short.md"),
        )

        long_doc = Document(
            metadata=DocumentMetadata(
                title="Long",
                purpose="test",
                confidence=0.80,
                updated_at=datetime.utcnow(),
            ),
            content="x" * 1000,  # Long content
            file_path=Path("./research/test/long.md"),
        )

        documents = [
            (short_doc, 0.85),  # Slightly lower similarity
            (long_doc, 0.85),   # Same similarity
        ]

        ranked = document_finder.rank_by_relevance(documents, "test")

        # Long document should rank higher due to length boost
        assert len(ranked[0][0].content) > len(ranked[1][0].content)
        assert len(ranked[0][0].content) == 1000  # Verify it's the long doc


class TestGetRelatedDocuments:
    """Test get_related_documents method."""

    def test_get_related_documents_not_found(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test error raised when document not found."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                with pytest.raises(
                    DocumentFinderError, match="Document not found"
                ):
                    document_finder.get_related_documents("nonexistent")

    def test_get_related_documents_from_relationships(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test getting related documents from relationship table."""
        with patch(
            "aris.core.document_finder.DocumentRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()

            # Source document with outgoing relationships
            source = MagicMock()
            source.id = "source"
            source.file_path = None

            related1 = MagicMock()
            related1.id = "related1"

            rel = MagicMock()
            rel.target_document = related1

            source.outgoing_relationships = [rel]
            source.incoming_relationships = []

            mock_repo.get_by_id.return_value = source
            mock_repo_class.return_value = mock_repo

            with patch.object(
                document_finder.db, "session_scope"
            ) as mock_session:
                mock_session.return_value.__enter__.return_value = MagicMock()

                results = document_finder.get_related_documents("source")

                assert len(results) > 0


class TestIndexDocument:
    """Test index_document method."""

    def test_index_document_success(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test successful document indexing."""
        document_finder.index_document(
            doc_id="doc1", content="Test content"
        )

        mock_vector_store.add_document.assert_called_once()
        call_args = mock_vector_store.add_document.call_args
        assert call_args[1]["doc_id"] == "doc1"
        assert call_args[1]["content"] == "Test content"

    def test_index_document_empty_doc_id_raises_error(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test empty doc_id raises DocumentFinderError."""
        with pytest.raises(DocumentFinderError):
            document_finder.index_document(doc_id="", content="content")


class TestDeindexDocument:
    """Test deindex_document method."""

    def test_deindex_document_success(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test successful document removal."""
        document_finder.deindex_document(doc_id="doc1")

        mock_vector_store.delete_document.assert_called_once_with("doc1")

    def test_deindex_document_empty_doc_id_raises_error(
        self, document_finder: DocumentFinder
    ) -> None:
        """Test empty doc_id raises DocumentFinderError."""
        with pytest.raises(DocumentFinderError):
            document_finder.deindex_document(doc_id="")


class TestGetSearchStats:
    """Test get_search_stats method."""

    def test_get_search_stats_success(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test retrieving search statistics."""
        mock_vector_store.get_collection_stats.return_value = {
            "total_documents": 42
        }

        stats = document_finder.get_search_stats()

        assert stats["total_documents"] == 42


class TestContextManager:
    """Test context manager functionality."""

    def test_enter_and_exit(
        self, document_finder: DocumentFinder, mock_vector_store: MagicMock
    ) -> None:
        """Test context manager enter and exit."""
        with document_finder:
            assert document_finder is not None

        # Persist should be called on exit
        mock_vector_store.persist.assert_called_once()
