"""High-level document storage and retrieval for ARIS.

Provides unified API for document operations combining:
- Git version control
- Database metadata
- File system operations
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aris.core.document_merger import DocumentMerger, MergeStrategy
from aris.models.config import ArisConfig
from aris.models.document import Document, DocumentMetadata
from aris.storage.database import DatabaseManager
from aris.storage.git_manager import GitManager

logger = logging.getLogger(__name__)


class DocumentStoreError(Exception):
    """Document store operation errors."""
    pass


class DocumentStore:
    """High-level document storage API.
    
    Combines Git, database, and filesystem operations for seamless
    document management with automatic versioning and metadata tracking.
    
    Example:
        store = DocumentStore(config)
        doc = store.create_document("New Research", "# Content", ["AI", "ML"])
        loaded = store.load_document(doc.file_path)
    """
    
    def __init__(self, config: ArisConfig):
        """Initialize document store.

        Args:
            config: ARIS configuration
        """
        from aris.core.document_merger import DocumentMerger

        self.config = config
        self.research_dir = Path(config.research_dir)
        self.db = DatabaseManager(Path(config.database_path))
        self.git = GitManager(self.research_dir)
        self.merger = DocumentMerger()
        
    def create_document(
        self,
        title: str,
        content: str,
        topics: Optional[list[str]] = None,
        confidence: float = 0.0
    ) -> Document:
        """Create new research document.
        
        Args:
            title: Document title
            content: Markdown content
            topics: List of topic tags
            confidence: Research confidence score (0.0-1.0)
            
        Returns:
            Created Document instance
        """
        # Generate document ID from title
        doc_id = self._generate_doc_id(title)
        
        # Create file path: research/<topic>/<title>.md
        primary_topic = topics[0] if topics else "general"
        safe_topic = self._sanitize_filename(primary_topic)
        safe_title = self._sanitize_filename(title)
        
        file_path = self.research_dir / safe_topic / f"{safe_title}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        now = datetime.now()
        metadata = DocumentMetadata(
            title=title,
            topics=topics or [],
            confidence=confidence,
            created_at=now,
            updated_at=now,
            file_path=str(file_path.relative_to(self.research_dir))
        )
        
        # Create document
        document = Document(
            content=content,
            metadata=metadata
        )
        
        # Write to file
        file_path.write_text(document.to_markdown())
        
        # Store metadata in database
        self.db.store_document_metadata(
            doc_id=doc_id,
            file_path=file_path,
            title=title,
            confidence=confidence,
            topics=topics
        )
        
        # Commit to Git
        self.git.commit_document(
            file_path,
            f"Create: {title}"
        )
        
        logger.info(f"Created document: {title} ({doc_id})")
        return document

    # Backward compatibility alias
    save_document = create_document

    def load_document(self, file_path: Path) -> Document:
        """Load document from file system.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Loaded Document instance
            
        Raises:
            DocumentStoreError: If document doesn't exist or is invalid
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise DocumentStoreError(f"Document not found: {file_path}")
        
        try:
            content = file_path.read_text()
            document = Document.from_markdown(content)
            return document
        except Exception as e:
            raise DocumentStoreError(f"Failed to load document: {e}")
    
    def update_document(
        self,
        document_or_path,
        new_content: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> Document:
        """Update existing document.

        Can be called in two ways:
        1. update_document(file_path, new_content) - Direct content update
        2. update_document(document) - Update already-modified document object

        Args:
            document_or_path: Path to document file or Document object
            new_content: Updated markdown content (optional)
            commit_message: Optional Git commit message

        Returns:
            Updated Document instance
        """
        # Handle both Path and Document inputs
        if isinstance(document_or_path, Document):
            document = document_or_path
            file_path = document.file_path
        else:
            file_path = Path(document_or_path)
            document = self.load_document(file_path)

            # Update content if provided
            if new_content is not None:
                document.content = new_content

        # Update timestamp
        document.metadata.updated_at = datetime.now()

        # Write to file
        file_path.write_text(document.to_markdown())

        # Update database
        doc_id = self._generate_doc_id(document.metadata.title)
        self.db.store_document_metadata(
            doc_id=doc_id,
            file_path=file_path,
            title=document.metadata.title,
            confidence=document.metadata.confidence,
            topics=document.metadata.topics,
        )

        # Commit to Git
        msg = commit_message or f"Update: {document.metadata.title}"
        self.git.commit_document(file_path, msg)

        logger.info(f"Updated document: {document.metadata.title}")
        return document

    def merge_document(
        self,
        file_path: Path,
        new_content: str,
        new_metadata: Optional[DocumentMetadata] = None,
        strategy: str = "integrate",
        commit_message: Optional[str] = None,
    ) -> tuple[Document, dict]:
        """Merge new content into existing document using merge strategy.

        Intelligently merges new research findings into existing document.
        Detects and logs conflicts. Returns both merged document and merge report.

        Args:
            file_path: Path to existing document file
            new_content: New content to merge
            new_metadata: Optional new metadata to merge
            strategy: Merge strategy ("append", "integrate", "replace")
            commit_message: Optional Git commit message

        Returns:
            Tuple of (merged Document, merge report dict)

        Raises:
            DocumentStoreError: If document doesn't exist or merge fails
        """
        file_path = Path(file_path)

        # Load existing document
        try:
            existing_doc = self.load_document(file_path)
        except DocumentStoreError as e:
            raise DocumentStoreError(f"Failed to load document for merge: {e}")

        # Import at runtime to avoid circular dependency
        from aris.core.document_merger import MergeStrategy

        # Convert strategy string to enum
        try:
            merge_strategy = MergeStrategy(strategy)
        except ValueError:
            raise DocumentStoreError(
                f"Invalid merge strategy: {strategy}. "
                f"Must be one of: {', '.join(s.value for s in MergeStrategy)}"
            )

        # Parse new metadata if provided
        parsed_new_metadata = None
        if new_metadata:
            parsed_new_metadata = new_metadata

        try:
            # Perform merge
            merged_doc = self.merger.merge_documents(
                existing=existing_doc,
                new_content=new_content,
                new_metadata=parsed_new_metadata,
                strategy=merge_strategy,
            )

            # Get merge report before writing
            merge_report = self.merger.get_merge_report()
            merge_report["strategy"] = strategy
            merge_report["document_title"] = merged_doc.metadata.title

            # Write merged document to file
            file_path.write_text(merged_doc.to_markdown())

            # Update database
            doc_id = self._generate_doc_id(merged_doc.metadata.title)
            self.db.store_document_metadata(
                doc_id=doc_id,
                file_path=file_path,
                title=merged_doc.metadata.title,
                confidence=merged_doc.metadata.confidence,
                topics=merged_doc.metadata.topics,
            )

            # Commit to Git
            msg = commit_message or f"Merge: {merged_doc.metadata.title}"
            self.git.commit_document(file_path, msg)

            logger.info(
                f"Merged document: {merged_doc.metadata.title} "
                f"({merge_report['conflicts_detected']} conflicts detected)"
            )

            return merged_doc, merge_report

        except Exception as e:
            raise DocumentStoreError(f"Document merge failed: {e}") from e

    def check_for_similar_document(
        self,
        title: str,
        topics: Optional[list[str]] = None,
    ) -> Optional[Path]:
        """Check if a similar document already exists.

        Simple check: looks for documents with overlapping topics.
        In Wave 3, this will use semantic similarity.

        Args:
            title: Proposed document title
            topics: List of topics for document

        Returns:
            Path to similar document if found, None otherwise
        """
        if not topics:
            return None

        topic_dirs = []
        for topic in topics:
            safe_topic = self._sanitize_filename(topic)
            topic_dir = self.research_dir / safe_topic
            if topic_dir.exists():
                topic_dirs.append(topic_dir)

        # Search for existing documents in matching topic directories
        for topic_dir in topic_dirs:
            for doc_file in topic_dir.glob("*.md"):
                return doc_file  # Return first match for now

        return None
    
    def _generate_doc_id(self, title: str) -> str:
        """Generate unique document ID from title.
        
        Args:
            title: Document title
            
        Returns:
            SHA-256 hash of title (first 12 characters)
        """
        return hashlib.sha256(title.encode()).hexdigest()[:12]
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use in filename.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized filename-safe string
        """
        # Replace spaces and special characters
        safe = name.lower()
        safe = safe.replace(" ", "-")
        safe = "".join(c for c in safe if c.isalnum() or c in "-_")
        return safe[:50]  # Limit length
