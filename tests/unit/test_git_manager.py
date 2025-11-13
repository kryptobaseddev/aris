"""Unit tests for GitManager."""

import tempfile
from pathlib import Path
import pytest

from aris.storage.git_manager import GitManager, GitOperationError


@pytest.fixture
def temp_repo():
    """Create temporary Git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        yield repo_path


@pytest.fixture
def git_manager(temp_repo):
    """Create GitManager instance with temporary repo."""
    return GitManager(temp_repo)


class TestGitManagerInitialization:
    """Test GitManager initialization and repository setup."""

    def test_init_creates_new_repo(self, temp_repo):
        """Test that GitManager initializes new repository."""
        git_mgr = GitManager(temp_repo)

        assert git_mgr.repo_path == temp_repo.resolve()
        assert git_mgr.repo is not None
        assert (temp_repo / ".git").exists()

    def test_init_opens_existing_repo(self, git_manager, temp_repo):
        """Test that GitManager opens existing repository."""
        # Create another instance with same path
        git_mgr2 = GitManager(temp_repo)

        assert git_mgr2.repo_path == temp_repo.resolve()
        assert git_mgr2.repo is not None

    def test_init_creates_gitignore(self, temp_repo):
        """Test that initialization creates .gitignore."""
        GitManager(temp_repo)

        gitignore_path = temp_repo / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert ".DS_Store" in content
        assert "__pycache__/" in content


class TestDocumentCommit:
    """Test document commit operations."""

    def test_commit_new_document(self, git_manager, temp_repo):
        """Test committing a new document."""
        # Create test document
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Test Document")

        # Commit document
        commit_hash = git_manager.commit_document(
            doc_path,
            "Create: Test document"
        )

        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 hash length

    def test_commit_with_relative_path(self, git_manager, temp_repo):
        """Test committing document with relative path."""
        # Create test document
        doc_path = temp_repo / "docs" / "test.md"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Test Document")

        # Commit with relative path
        relative_path = Path("docs/test.md")
        commit_hash = git_manager.commit_document(
            relative_path,
            "Create: Test document"
        )

        assert commit_hash is not None

    def test_commit_modified_document(self, git_manager, temp_repo):
        """Test committing modifications to existing document."""
        # Create and commit initial version
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Version 1")
        hash1 = git_manager.commit_document(doc_path, "Initial version")

        # Modify and commit again
        doc_path.write_text("# Version 2")
        hash2 = git_manager.commit_document(doc_path, "Updated version")

        assert hash1 != hash2

    def test_commit_no_changes_returns_same_hash(self, git_manager, temp_repo):
        """Test committing without changes returns same commit hash."""
        # Create and commit document
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Test")
        hash1 = git_manager.commit_document(doc_path, "Initial")

        # Commit again without changes
        hash2 = git_manager.commit_document(doc_path, "No changes")

        assert hash1 == hash2

    def test_commit_nonexistent_file_raises_error(self, git_manager, temp_repo):
        """Test committing nonexistent file raises error."""
        with pytest.raises(GitOperationError, match="does not exist"):
            git_manager.commit_document(
                temp_repo / "nonexistent.md",
                "Should fail"
            )

    def test_commit_outside_repo_raises_error(self, git_manager):
        """Test committing file outside repository raises error."""
        with pytest.raises(GitOperationError, match="outside repository"):
            git_manager.commit_document(
                Path("/tmp/outside.md"),
                "Should fail"
            )


class TestDocumentHistory:
    """Test document history retrieval."""

    def test_get_history_single_commit(self, git_manager, temp_repo):
        """Test retrieving history for document with single commit."""
        # Create and commit document
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Test")
        git_manager.commit_document(doc_path, "Initial commit")

        # Get history
        history = git_manager.get_document_history(doc_path)

        assert len(history) == 1
        assert "hash" in history[0]
        assert "message" in history[0]
        assert "Initial commit" in history[0]["message"]

    def test_get_history_multiple_commits(self, git_manager, temp_repo):
        """Test retrieving history for document with multiple commits."""
        doc_path = temp_repo / "test.md"

        # Create multiple versions
        doc_path.write_text("# Version 1")
        git_manager.commit_document(doc_path, "Version 1")

        doc_path.write_text("# Version 2")
        git_manager.commit_document(doc_path, "Version 2")

        doc_path.write_text("# Version 3")
        git_manager.commit_document(doc_path, "Version 3")

        # Get history
        history = git_manager.get_document_history(doc_path)

        assert len(history) == 3
        assert "Version 3" in history[0]["message"]  # Most recent first
        assert "Version 1" in history[2]["message"]

    def test_get_history_with_max_count(self, git_manager, temp_repo):
        """Test retrieving limited history."""
        doc_path = temp_repo / "test.md"

        # Create 5 versions
        for i in range(1, 6):
            doc_path.write_text(f"# Version {i}")
            git_manager.commit_document(doc_path, f"Version {i}")

        # Get only 3 most recent
        history = git_manager.get_document_history(doc_path, max_count=3)

        assert len(history) == 3
        assert "Version 5" in history[0]["message"]

    def test_get_history_includes_metadata(self, git_manager, temp_repo):
        """Test that history includes all expected metadata."""
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Test")
        git_manager.commit_document(
            doc_path,
            "Test commit",
            author_name="Test Author",
            author_email="test@example.com"
        )

        history = git_manager.get_document_history(doc_path)

        assert len(history) == 1
        commit = history[0]

        assert "hash" in commit
        assert "short_hash" in commit
        assert "message" in commit
        assert "author" in commit
        assert "email" in commit
        assert "date" in commit
        assert commit["author"] == "Test Author"
        assert commit["email"] == "test@example.com"


class TestDiffOperations:
    """Test diff generation."""

    def test_diff_between_commits(self, git_manager, temp_repo):
        """Test generating diff between two commits."""
        doc_path = temp_repo / "test.md"

        # Create two versions
        doc_path.write_text("# Version 1\nOriginal content")
        hash1 = git_manager.commit_document(doc_path, "Version 1")

        doc_path.write_text("# Version 2\nModified content")
        hash2 = git_manager.commit_document(doc_path, "Version 2")

        # Get diff
        diff = git_manager.get_diff(doc_path, hash1, hash2)

        assert diff is not None
        assert "-Original content" in diff or "-Version 1" in diff
        assert "+Modified content" in diff or "+Version 2" in diff

    def test_diff_with_working_tree(self, git_manager, temp_repo):
        """Test diff between commit and working tree."""
        doc_path = temp_repo / "test.md"

        # Commit initial version
        doc_path.write_text("# Committed")
        git_manager.commit_document(doc_path, "Initial")

        # Modify without committing
        doc_path.write_text("# Modified")

        # Get diff with working tree
        diff = git_manager.get_diff(doc_path)

        assert diff is not None
        assert "-Committed" in diff
        assert "+Modified" in diff


class TestFileRestore:
    """Test document restoration."""

    def test_restore_to_previous_version(self, git_manager, temp_repo):
        """Test restoring document to previous version."""
        doc_path = temp_repo / "test.md"

        # Create version 1
        doc_path.write_text("# Version 1")
        hash1 = git_manager.commit_document(doc_path, "Version 1")

        # Create version 2
        doc_path.write_text("# Version 2")
        git_manager.commit_document(doc_path, "Version 2")

        # Restore to version 1
        git_manager.restore_document(doc_path, hash1, create_backup=False)

        # Verify content
        content = doc_path.read_text()
        assert "Version 1" in content

    def test_restore_creates_backup(self, git_manager, temp_repo):
        """Test that restore creates backup file."""
        doc_path = temp_repo / "test.md"

        # Create two versions
        doc_path.write_text("# Version 1")
        hash1 = git_manager.commit_document(doc_path, "Version 1")

        doc_path.write_text("# Version 2")
        git_manager.commit_document(doc_path, "Version 2")

        # Restore with backup
        backup_path = git_manager.restore_document(
            doc_path, hash1, create_backup=True
        )

        # Verify backup exists
        assert backup_path.exists()
        assert "Version 2" in backup_path.read_text()

    def test_get_file_at_commit(self, git_manager, temp_repo):
        """Test retrieving file content at specific commit."""
        doc_path = temp_repo / "test.md"

        # Create version
        doc_path.write_text("# Original Content")
        commit_hash = git_manager.commit_document(doc_path, "Initial")

        # Modify file
        doc_path.write_text("# Modified Content")

        # Get content at commit
        content = git_manager.get_file_at_commit(doc_path, commit_hash)

        assert "Original Content" in content
        assert "Modified Content" not in content


class TestRepositoryStatus:
    """Test repository status operations."""

    def test_get_status_clean_repo(self, git_manager, temp_repo):
        """Test status of clean repository."""
        status = git_manager.get_status()

        assert isinstance(status, dict)
        assert "untracked" in status
        assert "modified" in status
        assert "staged" in status
        assert len(status["untracked"]) == 0
        assert len(status["modified"]) == 0

    def test_get_status_with_untracked(self, git_manager, temp_repo):
        """Test status with untracked files."""
        # Create untracked file
        (temp_repo / "new.md").write_text("# New")

        status = git_manager.get_status()

        assert "new.md" in status["untracked"]

    def test_get_status_with_modified(self, git_manager, temp_repo):
        """Test status with modified files."""
        # Create and commit file
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Original")
        git_manager.commit_document(doc_path, "Initial")

        # Modify file
        doc_path.write_text("# Modified")

        status = git_manager.get_status()

        assert "test.md" in status["modified"]

    def test_has_uncommitted_changes(self, git_manager, temp_repo):
        """Test checking for uncommitted changes."""
        # Clean repo
        assert not git_manager.has_uncommitted_changes()

        # Create untracked file
        (temp_repo / "new.md").write_text("# New")
        assert git_manager.has_uncommitted_changes()

    def test_has_uncommitted_changes_specific_file(self, git_manager, temp_repo):
        """Test checking uncommitted changes for specific file."""
        doc_path = temp_repo / "test.md"
        doc_path.write_text("# Test")
        git_manager.commit_document(doc_path, "Initial")

        # No changes
        assert not git_manager.has_uncommitted_changes(doc_path)

        # Modify file
        doc_path.write_text("# Modified")
        assert git_manager.has_uncommitted_changes(doc_path)
