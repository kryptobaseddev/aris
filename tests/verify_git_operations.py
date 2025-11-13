#!/usr/bin/env python3
"""Quick verification script for Git operations (Agent 3)."""

import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aris.storage.git_manager import GitManager
from aris.models.document import Document, DocumentMetadata


def test_git_operations():
    """Verify Git operations are functional."""
    print("🧪 Testing Git Operations (Agent 3)")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        try:
            # Test 1: Initialize Git repository
            print("\n✓ Test 1: Initialize repository")
            git_mgr = GitManager(repo_path)
            assert (repo_path / ".git").exists(), "Git repo not initialized"
            print("  ✅ Git repository initialized")

            # Test 2: Commit document
            print("\n✓ Test 2: Commit document")
            doc_path = repo_path / "test.md"
            doc_path.write_text("# Test Document\n\nContent here.")
            commit_hash = git_mgr.commit_document(doc_path, "Create: Test document")
            assert commit_hash is not None, "Commit failed"
            assert len(commit_hash) == 40, "Invalid commit hash"
            print(f"  ✅ Document committed: {commit_hash[:7]}")

            # Test 3: Get history
            print("\n✓ Test 3: Get commit history")
            history = git_mgr.get_document_history(doc_path)
            assert len(history) >= 1, "No history found"
            assert "Create" in history[0]["message"], "Wrong commit message"
            print(f"  ✅ History retrieved: {len(history)} commit(s)")

            # Test 4: Modify and commit again
            print("\n✓ Test 4: Modify and commit")
            doc_path.write_text("# Test Document\n\nModified content.")
            commit_hash2 = git_mgr.commit_document(doc_path, "Update: Modified document")
            assert commit_hash2 != commit_hash, "Commits should be different"
            print(f"  ✅ Document updated: {commit_hash2[:7]}")

            # Test 5: Get diff
            print("\n✓ Test 5: Generate diff")
            diff = git_mgr.get_diff(doc_path, commit_hash, commit_hash2)
            assert diff is not None, "Diff generation failed"
            assert "-Content here" in diff or "+Modified content" in diff, "Diff content incorrect"
            print("  ✅ Diff generated successfully")

            # Test 6: Restore document
            print("\n✓ Test 6: Restore previous version")
            git_mgr.restore_document(doc_path, commit_hash, create_backup=False)
            content = doc_path.read_text()
            assert "Content here" in content, "Restore failed"
            assert "Modified content" not in content, "Restore didn't revert changes"
            print("  ✅ Document restored to previous version")

            # Test 7: Repository status
            print("\n✓ Test 7: Check repository status")
            status = git_mgr.get_status()
            assert isinstance(status, dict), "Status not returned as dict"
            assert "untracked" in status, "Status missing keys"
            print("  ✅ Repository status retrieved")

            print("\n" + "=" * 50)
            print("✅ All Git operations tests passed!")
            print("\n📝 Agent 3 Git Operations: VERIFIED")
            return True

        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            return False
        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_git_operations()
    sys.exit(0 if success else 1)
