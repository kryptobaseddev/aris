"""Serena MCP client for session context persistence and memory management.

Serena integration enables:
- Cross-session context preservation
- Memory-based document discovery
- Research session state management
- Learning from past research
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryEntry(BaseModel):
    """In-memory representation of a Serena memory file."""

    name: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionContext(BaseModel):
    """Research session context for cross-session persistence."""

    session_id: str
    query: str
    created_at: datetime
    last_updated: datetime
    hops_executed: int
    max_hops: int
    documents_found: int
    research_depth: str
    status: str
    findings_summary: str = ""
    execution_time_seconds: float = 0.0
    documents: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SerenaClient:
    """Serena MCP client for session persistence and memory management.

    Provides cross-session context preservation through memory operations,
    enabling research continuity and learning from past sessions.
    """

    def __init__(self, memory_dir: Optional[Path] = None) -> None:
        """Initialize Serena client.

        Args:
            memory_dir: Directory for session memory files. Defaults to ~/.aris/memory/
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".aris" / "memory"

        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, MemoryEntry] = {}
        self._load_memory_cache()

        logger.debug(f"Serena client initialized with memory_dir: {self.memory_dir}")

    def _load_memory_cache(self) -> None:
        """Load all memory files from disk into cache."""
        if not self.memory_dir.exists():
            return

        for memory_file in self.memory_dir.glob("*.json"):
            try:
                with open(memory_file, "r") as f:
                    data = json.load(f)
                    entry = MemoryEntry(
                        name=memory_file.stem,
                        content=data.get("content", ""),
                        created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
                        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
                    )
                    self._memory_cache[entry.name] = entry
                    logger.debug(f"Loaded memory entry: {entry.name}")
            except (json.JSONDecodeError, OSError, ValueError) as e:
                logger.warning(f"Failed to load memory file {memory_file}: {e}")

    def write_memory(
        self,
        memory_name: str,
        content: str
    ) -> None:
        """Write or update a memory entry.

        Args:
            memory_name: Name of the memory entry
            content: Content to store

        Raises:
            ValueError: If memory_name is empty or contains invalid characters
        """
        if not memory_name or not isinstance(memory_name, str):
            raise ValueError("memory_name must be a non-empty string")

        if "/" in memory_name or "\\" in memory_name:
            raise ValueError("memory_name cannot contain path separators")

        now = datetime.utcnow()
        existing = self._memory_cache.get(memory_name)

        entry = MemoryEntry(
            name=memory_name,
            content=content,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )

        self._memory_cache[memory_name] = entry

        # Persist to disk
        memory_file = self.memory_dir / f"{memory_name}.json"
        try:
            with open(memory_file, "w") as f:
                json.dump({
                    "name": entry.name,
                    "content": entry.content,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                }, f, indent=2)
            logger.debug(f"Wrote memory entry: {memory_name}")
        except OSError as e:
            logger.error(f"Failed to write memory {memory_name}: {e}")
            raise

    def read_memory(self, memory_name: str) -> str:
        """Read a memory entry by name.

        Args:
            memory_name: Name of the memory entry

        Returns:
            Content of the memory entry

        Raises:
            KeyError: If memory entry doesn't exist
        """
        if memory_name not in self._memory_cache:
            raise KeyError(f"Memory entry not found: {memory_name}")

        entry = self._memory_cache[memory_name]
        logger.debug(f"Read memory entry: {memory_name}")
        return entry.content

    def list_memories(self) -> list[str]:
        """List all available memory entries.

        Returns:
            List of memory entry names
        """
        names = sorted(self._memory_cache.keys())
        logger.debug(f"Listed {len(names)} memory entries")
        return names

    def delete_memory(self, memory_name: str) -> None:
        """Delete a memory entry.

        Args:
            memory_name: Name of the memory entry to delete

        Raises:
            KeyError: If memory entry doesn't exist
        """
        if memory_name not in self._memory_cache:
            raise KeyError(f"Memory entry not found: {memory_name}")

        del self._memory_cache[memory_name]

        # Remove from disk
        memory_file = self.memory_dir / f"{memory_name}.json"
        try:
            memory_file.unlink(missing_ok=True)
            logger.debug(f"Deleted memory entry: {memory_name}")
        except OSError as e:
            logger.error(f"Failed to delete memory {memory_name}: {e}")
            raise

    def memory_exists(self, memory_name: str) -> bool:
        """Check if a memory entry exists.

        Args:
            memory_name: Name of the memory entry

        Returns:
            True if memory exists, False otherwise
        """
        return memory_name in self._memory_cache

    def save_session_context(self, context: SessionContext) -> None:
        """Save research session context for cross-session persistence.

        Args:
            context: SessionContext object to save

        Raises:
            ValueError: If context is invalid
        """
        if not context.session_id:
            raise ValueError("Session context must have a session_id")

        memory_name = f"session_{context.session_id}"
        content = context.model_dump_json(indent=2)
        self.write_memory(memory_name, content)
        logger.info(f"Saved session context: {context.session_id}")

    def load_session_context(self, session_id: str) -> Optional[SessionContext]:
        """Load research session context from memory.

        Args:
            session_id: ID of the session to load

        Returns:
            SessionContext object if found, None otherwise
        """
        memory_name = f"session_{session_id}"
        try:
            content = self.read_memory(memory_name)
            context = SessionContext.model_validate_json(content)
            logger.info(f"Loaded session context: {session_id}")
            return context
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load session context {session_id}: {e}")
            return None

    def list_sessions(self) -> list[str]:
        """List all saved research sessions.

        Returns:
            List of session IDs
        """
        session_ids = [
            name.replace("session_", "")
            for name in self.list_memories()
            if name.startswith("session_")
        ]
        return sorted(session_ids)

    def save_document_index(self, documents: list[dict[str, Any]]) -> None:
        """Save document index for cross-session document discovery.

        Args:
            documents: List of document metadata dicts
        """
        content = json.dumps(documents, indent=2, default=str)
        self.write_memory("document_index", content)
        logger.info(f"Saved document index with {len(documents)} documents")

    def load_document_index(self) -> list[dict[str, Any]]:
        """Load document index from memory.

        Returns:
            List of document metadata dicts, empty list if not found
        """
        try:
            content = self.read_memory("document_index")
            documents = json.loads(content)
            logger.info(f"Loaded document index with {len(documents)} documents")
            return documents
        except (KeyError, json.JSONDecodeError) as e:
            logger.debug(f"No document index found: {e}")
            return []

    def save_research_patterns(self, patterns: dict[str, Any]) -> None:
        """Save research patterns learned from past sessions.

        Args:
            patterns: Dictionary of research patterns and insights
        """
        content = json.dumps(patterns, indent=2, default=str)
        self.write_memory("research_patterns", content)
        logger.info(f"Saved research patterns with {len(patterns)} entries")

    def load_research_patterns(self) -> dict[str, Any]:
        """Load research patterns from memory.

        Returns:
            Dictionary of research patterns, empty dict if not found
        """
        try:
            content = self.read_memory("research_patterns")
            patterns = json.loads(content)
            logger.info(f"Loaded research patterns with {len(patterns)} entries")
            return patterns
        except (KeyError, json.JSONDecodeError) as e:
            logger.debug(f"No research patterns found: {e}")
            return {}

    def save_knowledge_base(self, knowledge: dict[str, Any]) -> None:
        """Save knowledge base entries for cross-session learning.

        Args:
            knowledge: Dictionary of knowledge base entries
        """
        content = json.dumps(knowledge, indent=2, default=str)
        self.write_memory("knowledge_base", content)
        logger.info(f"Saved knowledge base with {len(knowledge)} entries")

    def load_knowledge_base(self) -> dict[str, Any]:
        """Load knowledge base from memory.

        Returns:
            Dictionary of knowledge base entries, empty dict if not found
        """
        try:
            content = self.read_memory("knowledge_base")
            knowledge = json.loads(content)
            logger.info(f"Loaded knowledge base with {len(knowledge)} entries")
            return knowledge
        except (KeyError, json.JSONDecodeError) as e:
            logger.debug(f"No knowledge base found: {e}")
            return {}

    def clear_session_memory(self) -> None:
        """Clear all session memory entries while preserving patterns and knowledge.

        Useful for starting fresh while retaining learned patterns.
        """
        session_ids = self.list_sessions()
        cleared = 0

        for session_id in session_ids:
            try:
                self.delete_memory(f"session_{session_id}")
                cleared += 1
            except KeyError:
                pass

        logger.info(f"Cleared {cleared} session memory entries")

    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about current memory usage.

        Returns:
            Dictionary with memory statistics
        """
        memories = self.list_memories()
        sessions = self.list_sessions()

        total_size = 0
        for entry in self._memory_cache.values():
            total_size += len(entry.content.encode("utf-8"))

        return {
            "total_entries": len(memories),
            "session_entries": len(sessions),
            "total_size_bytes": total_size,
            "memory_dir": str(self.memory_dir),
        }
