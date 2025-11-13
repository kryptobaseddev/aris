"""Storage layer for ARIS research documents.

Provides:
- Git version control for research documents
- High-level document storage abstraction
- Automatic versioning and change tracking
- SQLite database for metadata
"""

from aris.storage.database import DatabaseManager
from aris.storage.document_store import DocumentStore
from aris.storage.git_manager import GitManager
from aris.storage.vector_store import VectorStore

__all__ = [
    "DatabaseManager",
    "GitManager",
    "DocumentStore",
    "VectorStore",
]
