"""Document data models for ARIS research artifacts."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentStatus(str, Enum):
    """Document lifecycle states."""

    DRAFT = "draft"
    RESEARCHING = "researching"
    VALIDATING = "validating"
    REVIEWED = "reviewed"
    DEPRECATED = "deprecated"


class DocumentMetadata(BaseModel):
    """Structured metadata for research documents (YAML frontmatter)."""

    # Identification
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=3, max_length=200)

    # Content classification
    purpose: str = Field(..., description="What problem does this doc solve?")
    topics: list[str] = Field(default_factory=list, description="What subjects are covered?")
    questions_answered: list[str] = Field(default_factory=list, alias="answers")

    # Lifecycle
    status: DocumentStatus = DocumentStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: Optional[datetime] = None

    # Quality metrics
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_count: int = Field(default=0, ge=0)

    # Relationships
    related_docs: list[str] = Field(default_factory=list, description="Related document paths")
    supersedes: Optional[str] = Field(None, description="Document this supersedes")
    superseded_by: Optional[str] = Field(None, description="Document that supersedes this")

    @field_validator("topics", "questions_answered", mode="before")
    @classmethod
    def ensure_list(cls, v: list[str] | str) -> list[str]:
        """Ensure fields are lists even if single string provided."""
        if isinstance(v, str):
            return [v]
        return v


class Document(BaseModel):
    """Complete research document with metadata and content."""

    metadata: DocumentMetadata
    content: str = Field(..., description="Markdown document content")
    file_path: Path = Field(..., description="Absolute path to document file")

    # Vector embedding (stored separately, referenced here)
    embedding_id: Optional[str] = None

    @property
    def relative_path(self) -> str:
        """Get path relative to research directory."""
        return str(self.file_path.relative_to(Path.cwd() / "research"))

    @property
    def topics_str(self) -> str:
        """Comma-separated topics for display."""
        return ", ".join(self.metadata.topics)

    def to_markdown(self) -> str:
        """Serialize document to markdown with YAML frontmatter."""
        import yaml

        # Convert metadata to dict, exclude defaults
        metadata_dict = self.metadata.model_dump(
            exclude={"id", "created_at", "updated_at"},
            exclude_none=True
        )

        frontmatter = yaml.dump(metadata_dict, default_flow_style=False, sort_keys=False)

        return f"""---
{frontmatter}---

{self.content}
"""

    @classmethod
    def from_markdown(cls, file_path: Path, content: str) -> "Document":
        """Parse markdown file with YAML frontmatter into Document."""
        import yaml

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Document missing YAML frontmatter")

        # Parse YAML frontmatter
        metadata_dict = yaml.safe_load(parts[1])
        metadata = DocumentMetadata(**metadata_dict)

        # Extract content (after second ---)
        doc_content = parts[2].strip()

        return cls(
            metadata=metadata,
            content=doc_content,
            file_path=file_path
        )

    def update_content(self, new_content: str, merge_strategy: str = "append") -> None:
        """Update document content with merge strategy.

        Args:
            new_content: New content to add/merge
            merge_strategy: "append" | "replace" | "integrate"
        """
        if merge_strategy == "replace":
            self.content = new_content
        elif merge_strategy == "append":
            self.content = f"{self.content}\n\n---\n\n{new_content}"
        elif merge_strategy == "integrate":
            # TODO: Implement intelligent content integration
            self.content = f"{self.content}\n\n{new_content}"
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")

        self.metadata.updated_at = datetime.utcnow()
