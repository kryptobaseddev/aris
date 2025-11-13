"""Git repository management for ARIS research documents.

Provides version control operations:
- Initialize/open Git repositories
- Automatic commits on document changes
- Document history retrieval
- Diff and comparison capabilities
- Conflict detection and resolution
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.objects.commit import Commit

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Errors during Git operations."""
    pass


class GitManager:
    """Manages Git repository operations for research documents.

    Handles all Git interactions including:
    - Repository initialization
    - Document commits with structured messages
    - History tracking
    - Diff generation
    - Conflict detection

    Example:
        git_mgr = GitManager(Path("./research"))
        commit_hash = git_mgr.commit_document(
            Path("research/topic/doc.md"),
            "Create: New research document"
        )
        history = git_mgr.get_document_history(Path("research/topic/doc.md"))
    """

    def __init__(self, repo_path: Path):
        """Initialize GitManager for repository.

        Args:
            repo_path: Path to Git repository (will be created if doesn't exist)
        """
        self.repo_path = repo_path.resolve()
        self.repo = self._init_or_open_repo()

    def _init_or_open_repo(self) -> Repo:
        """Initialize new or open existing Git repository.

        Returns:
            GitPython Repo object

        Raises:
            GitOperationError: If repository initialization fails
        """
        try:
            # Try opening existing repo
            repo = Repo(self.repo_path)
            logger.info(f"Opened existing Git repository at {self.repo_path}")
            return repo
        except InvalidGitRepositoryError:
            # Initialize new repo
            try:
                self.repo_path.mkdir(parents=True, exist_ok=True)
                repo = Repo.init(self.repo_path)

                # Create initial .gitignore
                gitignore_path = self.repo_path / ".gitignore"
                if not gitignore_path.exists():
                    gitignore_path.write_text(
                        "# ARIS cache and temp files\n"
                        ".DS_Store\n"
                        "*.tmp\n"
                        ".aris/cache/\n"
                        "__pycache__/\n"
                    )
                    repo.index.add([".gitignore"])
                    repo.index.commit("Initial commit: ARIS research repository")

                logger.info(f"Initialized new Git repository at {self.repo_path}")
                return repo
            except Exception as e:
                raise GitOperationError(
                    f"Failed to initialize Git repository: {e}"
                ) from e

    def commit_document(
        self,
        file_path: Path,
        message: str,
        author_name: str = "ARIS",
        author_email: str = "aris@local"
    ) -> str:
        """Stage and commit a document with structured message.

        Args:
            file_path: Path to document file (relative to repo or absolute)
            message: Commit message
            author_name: Author name for commit
            author_email: Author email for commit

        Returns:
            Commit hash (SHA)

        Raises:
            GitOperationError: If commit fails
        """
        try:
            # Convert to relative path if absolute
            if file_path.is_absolute():
                try:
                    relative_path = file_path.relative_to(self.repo_path)
                except ValueError:
                    raise GitOperationError(
                        f"File {file_path} is outside repository {self.repo_path}"
                    )
            else:
                relative_path = file_path

            # Ensure file exists
            full_path = self.repo_path / relative_path
            if not full_path.exists():
                raise GitOperationError(f"File does not exist: {full_path}")

            # Stage the file
            self.repo.index.add([str(relative_path)])

            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD") and self.repo.head.is_valid():
                logger.info(f"No changes to commit for {relative_path}")
                return self.repo.head.commit.hexsha

            # Create commit with custom author
            from git import Actor
            author = Actor(author_name, author_email)
            commit = self.repo.index.commit(message, author=author, committer=author)

            logger.info(
                f"Committed {relative_path} with message: {message[:50]}..."
            )
            return commit.hexsha

        except GitCommandError as e:
            raise GitOperationError(f"Git commit failed: {e}") from e
        except Exception as e:
            raise GitOperationError(
                f"Unexpected error during commit: {e}"
            ) from e

    def get_document_history(
        self,
        file_path: Path,
        max_count: Optional[int] = None
    ) -> List[Dict]:
        """Get commit history for a specific document.

        Args:
            file_path: Path to document (relative to repo or absolute)
            max_count: Maximum number of commits to return (None = all)

        Returns:
            List of commit dictionaries with keys:
                - hash: Commit SHA
                - message: Commit message
                - author: Author name
                - email: Author email
                - date: Commit datetime
                - files_changed: Number of files in commit

        Raises:
            GitOperationError: If history retrieval fails
        """
        try:
            # Convert to relative path
            if file_path.is_absolute():
                try:
                    relative_path = file_path.relative_to(self.repo_path)
                except ValueError:
                    raise GitOperationError(
                        f"File {file_path} is outside repository"
                    )
            else:
                relative_path = file_path

            # Get commits that modified this file
            commits = list(
                self.repo.iter_commits(
                    paths=str(relative_path),
                    max_count=max_count
                )
            )

            history = []
            for commit in commits:
                history.append({
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "email": commit.author.email,
                    "date": datetime.fromtimestamp(commit.committed_date),
                    "files_changed": len(commit.stats.files),
                })

            return history

        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve history for {file_path}: {e}"
            ) from e

    def get_diff(
        self,
        file_path: Path,
        commit1: Optional[str] = None,
        commit2: Optional[str] = None
    ) -> str:
        """Get diff for document between two commits.

        Args:
            file_path: Path to document
            commit1: First commit hash (None = previous commit)
            commit2: Second commit hash (None = current working tree)

        Returns:
            Unified diff string

        Raises:
            GitOperationError: If diff generation fails
        """
        try:
            # Convert to relative path
            if file_path.is_absolute():
                try:
                    relative_path = file_path.relative_to(self.repo_path)
                except ValueError:
                    raise GitOperationError(
                        f"File {file_path} is outside repository"
                    )
            else:
                relative_path = file_path

            # Get commits
            if commit2 is None:
                # Compare with working tree
                if commit1 is None:
                    # Compare HEAD with working tree
                    diff = self.repo.git.diff("HEAD", "--", str(relative_path))
                else:
                    # Compare specific commit with working tree
                    diff = self.repo.git.diff(commit1, "--", str(relative_path))
            else:
                # Compare two commits
                if commit1 is None:
                    # Compare previous commit with specified commit
                    diff = self.repo.git.diff(
                        f"{commit2}~1", commit2, "--", str(relative_path)
                    )
                else:
                    # Compare two specified commits
                    diff = self.repo.git.diff(
                        commit1, commit2, "--", str(relative_path)
                    )

            return diff

        except Exception as e:
            raise GitOperationError(
                f"Failed to generate diff for {file_path}: {e}"
            ) from e

    def get_file_at_commit(self, file_path: Path, commit_hash: str) -> str:
        """Get file content at specific commit.

        Args:
            file_path: Path to document
            commit_hash: Commit hash to retrieve

        Returns:
            File content as string

        Raises:
            GitOperationError: If file retrieval fails
        """
        try:
            # Convert to relative path
            if file_path.is_absolute():
                try:
                    relative_path = file_path.relative_to(self.repo_path)
                except ValueError:
                    raise GitOperationError(
                        f"File {file_path} is outside repository"
                    )
            else:
                relative_path = file_path

            # Get file content at commit
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / str(relative_path)

            return blob.data_stream.read().decode('utf-8')

        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve {file_path} at {commit_hash}: {e}"
            ) from e

    def restore_document(
        self,
        file_path: Path,
        commit_hash: str,
        create_backup: bool = True
    ) -> Path:
        """Restore document to specific commit version.

        Args:
            file_path: Path to document
            commit_hash: Commit hash to restore from
            create_backup: If True, create .bak file before restoring

        Returns:
            Path to backup file (if created), otherwise original path

        Raises:
            GitOperationError: If restore fails
        """
        try:
            # Convert to relative path
            if file_path.is_absolute():
                full_path = file_path
                try:
                    relative_path = file_path.relative_to(self.repo_path)
                except ValueError:
                    raise GitOperationError(
                        f"File {file_path} is outside repository"
                    )
            else:
                relative_path = file_path
                full_path = self.repo_path / relative_path

            # Create backup if requested
            backup_path = full_path
            if create_backup and full_path.exists():
                backup_path = full_path.with_suffix(
                    full_path.suffix + ".bak"
                )
                backup_path.write_text(full_path.read_text())
                logger.info(f"Created backup at {backup_path}")

            # Restore file from commit
            content = self.get_file_at_commit(file_path, commit_hash)
            full_path.write_text(content)

            logger.info(
                f"Restored {file_path} from commit {commit_hash[:7]}"
            )
            return backup_path if create_backup else full_path

        except Exception as e:
            raise GitOperationError(
                f"Failed to restore {file_path}: {e}"
            ) from e

    def get_status(self) -> Dict[str, List[str]]:
        """Get repository status.

        Returns:
            Dictionary with keys:
                - untracked: List of untracked files
                - modified: List of modified files
                - staged: List of staged files
        """
        try:
            status = {
                "untracked": self.repo.untracked_files,
                "modified": [item.a_path for item in self.repo.index.diff(None)],
                "staged": [item.a_path for item in self.repo.index.diff("HEAD")]
            }
            return status
        except Exception as e:
            logger.warning(f"Failed to get repo status: {e}")
            return {"untracked": [], "modified": [], "staged": []}

    def has_uncommitted_changes(self, file_path: Optional[Path] = None) -> bool:
        """Check if repository or specific file has uncommitted changes.

        Args:
            file_path: Optional specific file to check

        Returns:
            True if there are uncommitted changes
        """
        try:
            if file_path:
                # Convert to relative path
                if file_path.is_absolute():
                    relative_path = file_path.relative_to(self.repo_path)
                else:
                    relative_path = file_path

                # Check if file is modified or untracked
                status = self.get_status()
                rel_path_str = str(relative_path)
                return (
                    rel_path_str in status["modified"] or
                    rel_path_str in status["staged"] or
                    rel_path_str in status["untracked"]
                )
            else:
                # Check entire repo
                return self.repo.is_dirty(untracked_files=True)
        except Exception as e:
            logger.warning(f"Failed to check uncommitted changes: {e}")
            return False
