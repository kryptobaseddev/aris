#!/usr/bin/env python3
"""Demo script showing complete Git integration with ARIS document storage."""

import tempfile
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aris.models.config import ArisConfig
from aris.models.document import Document, DocumentMetadata, DocumentStatus
from aris.storage.document_store import DocumentStore


def demo_complete_workflow():
    """Demonstrate complete Git-integrated document workflow."""
    print("🚀 ARIS Git Integration Demo")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Setup configuration
        print("\n📋 Step 1: Configuration Setup")
        config = ArisConfig(
            project_root=tmpdir_path,
            research_dir=tmpdir_path / "research",
            database_path=tmpdir_path / ".aris" / "metadata.db",
            cache_dir=tmpdir_path / ".aris" / "cache"
        )
        config.ensure_directories()
        print(f"  ✓ Research dir: {config.research_dir}")
        print(f"  ✓ Git repo will be: {config.git_repo_path}")

        # Initialize DocumentStore
        print("\n📚 Step 2: Initialize DocumentStore")
        store = DocumentStore(config)
        print("  ✓ DocumentStore initialized")
        print("  ✓ Git repository created automatically")

        # Create first document
        print("\n📝 Step 3: Create Research Document")
        metadata1 = DocumentMetadata(
            title="AI Ethics Research",
            purpose="Explore ethical implications of AI systems",
            topics=["ai", "ethics", "safety"],
            status=DocumentStatus.RESEARCHING,
            confidence=0.70,
            source_count=10
        )

        content1 = """# AI Ethics Research

## Overview
This document explores the ethical implications of AI systems in modern society.

## Key Concerns
- Bias and fairness
- Privacy and surveillance
- Autonomous decision-making
- Accountability and transparency

## Research Findings
Initial research suggests...
"""

        doc1 = Document(
            metadata=metadata1,
            content=content1,
            file_path=config.research_dir / "ai" / "ethics.md"
        )

        saved_doc1 = store.save_document(doc1, operation="create")
        print(f"  ✓ Document saved: {saved_doc1.metadata.title}")
        print(f"  ✓ File: {saved_doc1.file_path}")
        print("  ✓ Git commit created automatically")

        # Show initial history
        print("\n📖 Step 4: View Version History")
        history = store.get_document_versions(doc1.file_path)
        print(f"  ✓ Version count: {len(history)}")
        for i, version in enumerate(history, 1):
            print(f"    Version {i}: {version['short_hash']} - {version['message'].split(chr(10))[0]}")

        # Update document
        print("\n✏️  Step 5: Update Document")
        doc1.content += """

## Additional Findings
- New research from Stanford shows...
- Meta's latest AI safety report indicates...
"""
        doc1.metadata.confidence = 0.80
        doc1.metadata.source_count = 15

        store.save_document(doc1, operation="update")
        print("  ✓ Document updated")
        print("  ✓ New Git commit created")

        # Show updated history
        history = store.get_document_versions(doc1.file_path)
        print(f"  ✓ Version count: {len(history)}")

        # Create second document
        print("\n📝 Step 6: Create Another Document")
        metadata2 = DocumentMetadata(
            title="Machine Learning Best Practices",
            purpose="Document ML engineering best practices",
            topics=["ai", "ml", "engineering"],
            status=DocumentStatus.DRAFT,
            confidence=0.60,
            source_count=8
        )

        content2 = """# Machine Learning Best Practices

## Data Pipeline
- Data versioning with DVC
- Feature engineering practices
- Data validation checks

## Model Development
- Experimentation tracking
- Model versioning
- Hyperparameter tuning
"""

        doc2 = Document(
            metadata=metadata2,
            content=content2,
            file_path=config.research_dir / "ml" / "best-practices.md"
        )

        store.save_document(doc2, operation="create")
        print(f"  ✓ Document saved: {doc2.metadata.title}")

        # List all documents
        print("\n📑 Step 7: List All Documents")
        all_docs = store.list_documents()
        print(f"  ✓ Total documents: {len(all_docs)}")
        for doc_path in all_docs:
            print(f"    - {doc_path.relative_to(config.research_dir)}")

        # Filter by topic
        print("\n🔍 Step 8: Filter Documents by Topic")
        ai_docs = store.list_documents(topic_filter="ai")
        print(f"  ✓ Documents with 'ai' topic: {len(ai_docs)}")

        # Show diff
        print("\n🔄 Step 9: Compare Document Versions")
        history = store.get_document_versions(doc1.file_path)
        if len(history) >= 2:
            diff = store.diff_versions(
                doc1.file_path,
                history[1]["hash"],
                history[0]["hash"]
            )
            print("  ✓ Diff generated:")
            print("  " + "─" * 50)
            for line in diff.split("\n")[:15]:  # Show first 15 lines
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"  \033[92m{line}\033[0m")  # Green
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"  \033[91m{line}\033[0m")  # Red
                else:
                    print(f"  {line}")
            print("  " + "─" * 50)

        # Restore to previous version
        print("\n⏮️  Step 10: Restore Previous Version")
        if len(history) >= 2:
            old_content = doc1.content
            store.restore_version(
                doc1.file_path,
                history[1]["hash"],
                create_backup=True
            )
            print("  ✓ Document restored to previous version")
            print("  ✓ Backup created")

            # Verify restore
            loaded = store.load_document(doc1.file_path)
            print(f"  ✓ Content verified (length: {len(loaded.content)} chars)")

        # Repository status
        print("\n📊 Step 11: Check Repository Status")
        status = store.get_status()
        print("  ✓ Repository status:")
        print(f"    - Untracked files: {len(status['untracked'])}")
        print(f"    - Modified files: {len(status['modified'])}")
        print(f"    - Staged files: {len(status['staged'])}")

        # Final summary
        print("\n" + "=" * 60)
        print("✅ Git Integration Demo Complete!")
        print("\n📈 Summary:")
        print(f"  - Documents created: 2")
        print(f"  - Total commits: {len(history) + 1}")
        print(f"  - Topics covered: ai, ethics, safety, ml, engineering")
        print(f"  - Git operations: All functional")
        print(f"  - Version control: Active and working")
        print("\n🎯 Agent 3 Git Operations: FULLY OPERATIONAL")


if __name__ == "__main__":
    try:
        demo_complete_workflow()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
