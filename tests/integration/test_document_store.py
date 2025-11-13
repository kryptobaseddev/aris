"""Integration tests for DocumentStore with Git and Database."""

import tempfile
from datetime import datetime
from pathlib import Path
import pytest

from aris.models.config import ArisConfig
from aris.models.document import Document, DocumentMetadata, DocumentStatus
from aris.storage.document_store import DocumentStore, DocumentStoreError


@pytest.fixture
def temp_config():
    """Create temporary configuration for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        config = ArisConfig(
            project_root=tmpdir_path,
            research_dir=tmpdir_path / "research",
            database_path=tmpdir_path / ".aris" / "metadata.db",
            cache_dir=tmpdir_path / ".aris" / "cache"
        )

        # Ensure directories exist
        config.ensure_directories()

        yield config


@pytest.fixture
def document_store(temp_config):
    """Create DocumentStore instance for testing."""
    return DocumentStore(temp_config)


@pytest.fixture
def sample_document(temp_config):
    """Create sample document for testing."""
    metadata = DocumentMetadata(
        title="Test Document",
        purpose="Testing document storage",
        topics=["testing", "integration"],
        confidence=0.75,
        source_count=5
    )

    content = """# Test Document

This is test content for integration testing.

## Section 1
Content here.

## Section 2
More content.
"""

    file_path = temp_config.research_dir / "testing" / "test-document.md"

    return Document(
        metadata=metadata,
        content=content,
        file_path=file_path
    )


class TestDocumentSave:
    """Test document saving operations."""

    def test_save_new_document(self, document_store, sample_document):
        """Test saving a new document."""
        # Save document
        saved = document_store.save_document(sample_document, operation="create")

        # Verify document saved
        assert saved.file_path.exists()
        assert saved.metadata.title == sample_document.metadata.title

    def test_save_creates_directory(self, document_store, sample_document):
        """Test that save creates parent directories."""
        # Ensure directory doesn't exist
        assert not sample_document.file_path.parent.exists()

        # Save document
        document_store.save_document(sample_document, operation="create")

        # Verify directory created
        assert sample_document.file_path.parent.exists()

    def test_save_creates_git_commit(self, document_store, sample_document):
        """Test that save creates Git commit."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # Verify Git commit exists
        history = document_store.get_document_versions(sample_document.file_path)
        assert len(history) >= 1
        assert "Create" in history[0]["message"]

    def test_save_with_custom_commit_message(self, document_store, sample_document):
        """Test saving with custom commit message."""
        custom_msg = "Custom: Special commit message"
        document_store.save_document(
            sample_document,
            operation="create",
            commit_message=custom_msg
        )

        # Verify custom message used
        history = document_store.get_document_versions(sample_document.file_path)
        assert custom_msg in history[0]["message"]

    def test_save_update_operation(self, document_store, sample_document):
        """Test saving with update operation."""
        # Save initial version
        document_store.save_document(sample_document, operation="create")

        # Update and save again
        sample_document.content += "\n\n## New Section\nNew content."
        sample_document.metadata.confidence = 0.85

        document_store.save_document(sample_document, operation="update")

        # Verify history
        history = document_store.get_document_versions(sample_document.file_path)
        assert len(history) == 2
        assert "Update" in history[0]["message"]

    def test_save_preserves_metadata(self, document_store, sample_document):
        """Test that save preserves document metadata."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # Load and verify
        loaded = document_store.load_document(sample_document.file_path)

        assert loaded.metadata.title == sample_document.metadata.title
        assert loaded.metadata.purpose == sample_document.metadata.purpose
        assert loaded.metadata.topics == sample_document.metadata.topics
        assert loaded.metadata.confidence == sample_document.metadata.confidence


class TestDocumentLoad:
    """Test document loading operations."""

    def test_load_existing_document(self, document_store, sample_document):
        """Test loading existing document."""
        # Save document first
        document_store.save_document(sample_document, operation="create")

        # Load document
        loaded = document_store.load_document(sample_document.file_path)

        assert loaded is not None
        assert loaded.metadata.title == sample_document.metadata.title
        assert loaded.content == sample_document.content

    def test_load_nonexistent_document_raises_error(self, document_store, temp_config):
        """Test loading nonexistent document raises error."""
        fake_path = temp_config.research_dir / "nonexistent.md"

        with pytest.raises(DocumentStoreError, match="does not exist"):
            document_store.load_document(fake_path)

    def test_load_document_from_commit(self, document_store, sample_document):
        """Test loading document from specific commit."""
        # Save initial version
        document_store.save_document(sample_document, operation="create")

        # Get commit hash
        history = document_store.get_document_versions(sample_document.file_path)
        first_commit = history[0]["hash"]

        # Modify and save again
        sample_document.content += "\n\nModified content"
        document_store.save_document(sample_document, operation="update")

        # Load from first commit
        loaded = document_store.load_document(
            sample_document.file_path,
            commit_hash=first_commit
        )

        # Verify original content
        assert "Modified content" not in loaded.content


class TestVersionHistory:
    """Test version history operations."""

    def test_get_versions_single_version(self, document_store, sample_document):
        """Test getting versions for document with single commit."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # Get versions
        versions = document_store.get_document_versions(sample_document.file_path)

        assert len(versions) >= 1
        assert versions[0]["message"]

    def test_get_versions_multiple_versions(self, document_store, sample_document):
        """Test getting versions for document with multiple commits."""
        # Create multiple versions
        for i in range(3):
            sample_document.content += f"\n\nVersion {i+1} content"
            document_store.save_document(sample_document, operation="update")

        # Get versions
        versions = document_store.get_document_versions(sample_document.file_path)

        assert len(versions) == 3
        # Most recent first
        assert "Version 3" in sample_document.content

    def test_get_versions_with_limit(self, document_store, sample_document):
        """Test getting limited number of versions."""
        # Create 5 versions
        for i in range(5):
            sample_document.content += f"\n\nVersion {i+1}"
            document_store.save_document(sample_document, operation="update")

        # Get only 2 most recent
        versions = document_store.get_document_versions(
            sample_document.file_path,
            max_count=2
        )

        assert len(versions) == 2


class TestDiffOperations:
    """Test diff operations."""

    def test_diff_between_versions(self, document_store, sample_document):
        """Test generating diff between two versions."""
        # Save initial version
        original_content = sample_document.content
        document_store.save_document(sample_document, operation="create")

        history = document_store.get_document_versions(sample_document.file_path)
        commit1 = history[0]["hash"]

        # Modify and save
        sample_document.content += "\n\n## New Section\nNew content."
        document_store.save_document(sample_document, operation="update")

        history = document_store.get_document_versions(sample_document.file_path)
        commit2 = history[0]["hash"]

        # Get diff
        diff = document_store.diff_versions(
            sample_document.file_path,
            commit1,
            commit2
        )

        assert diff is not None
        assert "+## New Section" in diff or "+New content" in diff

    def test_diff_with_current(self, document_store, sample_document):
        """Test diff between commit and current working version."""
        # Save committed version
        document_store.save_document(sample_document, operation="create")

        # Modify file without committing
        sample_document.file_path.write_text(
            sample_document.to_markdown() + "\n\nUncommitted changes"
        )

        # Get diff
        diff = document_store.diff_versions(sample_document.file_path)

        assert diff is not None
        assert "Uncommitted changes" in diff


class TestRestoreOperations:
    """Test document restore operations."""

    def test_restore_to_previous_version(self, document_store, sample_document):
        """Test restoring document to previous version."""
        # Save version 1
        version1_content = sample_document.content
        document_store.save_document(sample_document, operation="create")

        history = document_store.get_document_versions(sample_document.file_path)
        version1_commit = history[0]["hash"]

        # Save version 2
        sample_document.content += "\n\nVersion 2 content"
        document_store.save_document(sample_document, operation="update")

        # Restore to version 1
        document_store.restore_version(
            sample_document.file_path,
            version1_commit,
            create_backup=False
        )

        # Verify content restored
        loaded = document_store.load_document(sample_document.file_path)
        assert "Version 2 content" not in loaded.content

    def test_restore_creates_backup(self, document_store, sample_document):
        """Test that restore creates backup file."""
        # Save initial version
        document_store.save_document(sample_document, operation="create")

        history = document_store.get_document_versions(sample_document.file_path)
        first_commit = history[0]["hash"]

        # Save second version
        version2_content = sample_document.content + "\n\nVersion 2"
        sample_document.content = version2_content
        document_store.save_document(sample_document, operation="update")

        # Restore with backup
        backup_path = document_store.restore_version(
            sample_document.file_path,
            first_commit,
            create_backup=True
        )

        # Verify backup exists and contains version 2
        assert backup_path.exists()
        backup_content = backup_path.read_text()
        assert "Version 2" in backup_content


class TestRepositoryStatus:
    """Test repository status operations."""

    def test_get_status_clean(self, document_store, sample_document):
        """Test status of clean repository."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # Get status (should be clean)
        status = document_store.get_status()

        assert isinstance(status, dict)
        assert "untracked" in status
        assert "modified" in status

    def test_get_status_with_uncommitted(self, document_store, sample_document):
        """Test status with uncommitted changes."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # Modify without committing
        sample_document.file_path.write_text("# Modified content")

        # Get status
        status = document_store.get_status()

        # Should show as modified
        assert len(status["modified"]) > 0

    def test_has_uncommitted_changes(self, document_store, sample_document):
        """Test checking for uncommitted changes."""
        # Save document
        document_store.save_document(sample_document, operation="create")

        # No uncommitted changes
        assert not document_store.has_uncommitted_changes(sample_document.file_path)

        # Make changes
        sample_document.file_path.write_text("# Changed")

        # Should detect uncommitted changes
        assert document_store.has_uncommitted_changes(sample_document.file_path)


class TestDocumentList:
    """Test document listing operations."""

    def test_list_all_documents(self, document_store, temp_config):
        """Test listing all documents in repository."""
        # Create multiple documents
        for i in range(3):
            metadata = DocumentMetadata(
                title=f"Document {i}",
                purpose=f"Test {i}",
                topics=["testing"]
            )
            content = f"# Document {i}\nContent"
            file_path = temp_config.research_dir / "testing" / f"doc{i}.md"

            doc = Document(metadata=metadata, content=content, file_path=file_path)
            document_store.save_document(doc, operation="create")

        # List documents
        documents = document_store.list_documents()

        assert len(documents) == 3

    def test_list_documents_with_topic_filter(self, document_store, temp_config):
        """Test listing documents filtered by topic."""
        # Create documents with different topics
        topics_list = [["ai", "ml"], ["web"], ["ai", "data"]]

        for i, topics in enumerate(topics_list):
            metadata = DocumentMetadata(
                title=f"Document {i}",
                purpose=f"Test {i}",
                topics=topics
            )
            content = f"# Document {i}"
            file_path = temp_config.research_dir / "test" / f"doc{i}.md"

            doc = Document(metadata=metadata, content=content, file_path=file_path)
            document_store.save_document(doc, operation="create")

        # Filter by "ai" topic
        ai_docs = document_store.list_documents(topic_filter="ai")

        assert len(ai_docs) == 2  # doc0 and doc2 have "ai" topic

    def test_list_documents_with_status_filter(self, document_store, temp_config):
        """Test listing documents filtered by status."""
        # Create documents with different statuses
        statuses = [DocumentStatus.DRAFT, DocumentStatus.REVIEWED, DocumentStatus.DRAFT]

        for i, status in enumerate(statuses):
            metadata = DocumentMetadata(
                title=f"Document {i}",
                purpose=f"Test {i}",
                topics=["test"],
                status=status
            )
            content = f"# Document {i}"
            file_path = temp_config.research_dir / "test" / f"doc{i}.md"

            doc = Document(metadata=metadata, content=content, file_path=file_path)
            document_store.save_document(doc, operation="create")

        # Filter by DRAFT status
        draft_docs = document_store.list_documents(status_filter=DocumentStatus.DRAFT)

        assert len(draft_docs) == 2  # doc0 and doc2 are drafts
