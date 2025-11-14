"""Tests for Serena client session persistence and memory management."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from aris.mcp.serena_client import MemoryEntry, SerenaClient, SessionContext


class TestMemoryEntry:
    """Tests for MemoryEntry model."""

    def test_memory_entry_creation(self) -> None:
        """Test creating a memory entry."""
        entry = MemoryEntry(
            name="test_memory",
            content="Test content"
        )
        assert entry.name == "test_memory"
        assert entry.content == "Test content"
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)

    def test_memory_entry_model_dump(self) -> None:
        """Test serializing memory entry."""
        entry = MemoryEntry(
            name="test_memory",
            content="Test content"
        )
        data = entry.model_dump()
        assert data["name"] == "test_memory"
        assert data["content"] == "Test content"


class TestSessionContext:
    """Tests for SessionContext model."""

    def test_session_context_creation(self) -> None:
        """Test creating a session context."""
        context = SessionContext(
            session_id="test_session",
            query="What is X?",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            hops_executed=2,
            max_hops=5,
            documents_found=3,
            research_depth="standard",
            status="complete"
        )
        assert context.session_id == "test_session"
        assert context.query == "What is X?"
        assert context.hops_executed == 2

    def test_session_context_serialization(self) -> None:
        """Test serializing and deserializing session context."""
        now = datetime.utcnow()
        context = SessionContext(
            session_id="test_session",
            query="What is X?",
            created_at=now,
            last_updated=now,
            hops_executed=2,
            max_hops=5,
            documents_found=3,
            research_depth="standard",
            status="complete"
        )
        json_str = context.model_dump_json()
        restored = SessionContext.model_validate_json(json_str)
        assert restored.session_id == context.session_id
        assert restored.query == context.query


class TestSerenaClient:
    """Tests for SerenaClient memory management."""

    @pytest.fixture
    def temp_memory_dir(self) -> Path:
        """Create temporary memory directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def client(self, temp_memory_dir: Path) -> SerenaClient:
        """Create SerenaClient with temporary directory."""
        return SerenaClient(memory_dir=temp_memory_dir)

    def test_client_initialization(self, client: SerenaClient) -> None:
        """Test client initialization."""
        assert client.memory_dir.exists()
        assert isinstance(client._memory_cache, dict)

    def test_write_memory(self, client: SerenaClient) -> None:
        """Test writing memory entry."""
        client.write_memory("test_key", "test_content")
        assert "test_key" in client._memory_cache
        assert client._memory_cache["test_key"].content == "test_content"

    def test_write_memory_persistence(self, client: SerenaClient, temp_memory_dir: Path) -> None:
        """Test memory is persisted to disk."""
        client.write_memory("test_key", "test_content")
        memory_file = temp_memory_dir / "test_key.json"
        assert memory_file.exists()

        with open(memory_file) as f:
            data = json.load(f)
            assert data["content"] == "test_content"

    def test_write_memory_update(self, client: SerenaClient) -> None:
        """Test updating existing memory entry."""
        client.write_memory("test_key", "first_content")
        first_entry = client._memory_cache["test_key"]

        client.write_memory("test_key", "second_content")
        second_entry = client._memory_cache["test_key"]

        assert second_entry.content == "second_content"
        assert second_entry.created_at == first_entry.created_at
        assert second_entry.updated_at >= first_entry.updated_at

    def test_write_memory_invalid_name(self, client: SerenaClient) -> None:
        """Test writing memory with invalid name."""
        with pytest.raises(ValueError):
            client.write_memory("", "content")

        with pytest.raises(ValueError):
            client.write_memory("test/invalid", "content")

    def test_read_memory(self, client: SerenaClient) -> None:
        """Test reading memory entry."""
        client.write_memory("test_key", "test_content")
        content = client.read_memory("test_key")
        assert content == "test_content"

    def test_read_memory_not_found(self, client: SerenaClient) -> None:
        """Test reading non-existent memory."""
        with pytest.raises(KeyError):
            client.read_memory("nonexistent")

    def test_list_memories(self, client: SerenaClient) -> None:
        """Test listing all memories."""
        client.write_memory("memory1", "content1")
        client.write_memory("memory2", "content2")
        client.write_memory("memory3", "content3")

        memories = client.list_memories()
        assert len(memories) == 3
        assert "memory1" in memories
        assert "memory2" in memories
        assert "memory3" in memories

    def test_delete_memory(self, client: SerenaClient) -> None:
        """Test deleting memory entry."""
        client.write_memory("test_key", "content")
        assert client.memory_exists("test_key")

        client.delete_memory("test_key")
        assert not client.memory_exists("test_key")

    def test_delete_memory_not_found(self, client: SerenaClient) -> None:
        """Test deleting non-existent memory."""
        with pytest.raises(KeyError):
            client.delete_memory("nonexistent")

    def test_memory_exists(self, client: SerenaClient) -> None:
        """Test checking if memory exists."""
        assert not client.memory_exists("test_key")
        client.write_memory("test_key", "content")
        assert client.memory_exists("test_key")

    def test_save_session_context(self, client: SerenaClient) -> None:
        """Test saving session context."""
        context = SessionContext(
            session_id="test_session",
            query="Test query",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            hops_executed=1,
            max_hops=5,
            documents_found=1,
            research_depth="quick",
            status="complete"
        )
        client.save_session_context(context)

        assert client.memory_exists("session_test_session")

    def test_save_session_context_invalid(self, client: SerenaClient) -> None:
        """Test saving invalid session context."""
        context = SessionContext(
            session_id="",  # Invalid
            query="Test query",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            hops_executed=1,
            max_hops=5,
            documents_found=1,
            research_depth="quick",
            status="complete"
        )
        with pytest.raises(ValueError):
            client.save_session_context(context)

    def test_load_session_context(self, client: SerenaClient) -> None:
        """Test loading session context."""
        context = SessionContext(
            session_id="test_session",
            query="Test query",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            hops_executed=1,
            max_hops=5,
            documents_found=1,
            research_depth="quick",
            status="complete"
        )
        client.save_session_context(context)
        loaded = client.load_session_context("test_session")

        assert loaded is not None
        assert loaded.session_id == "test_session"
        assert loaded.query == "Test query"

    def test_load_session_context_not_found(self, client: SerenaClient) -> None:
        """Test loading non-existent session."""
        loaded = client.load_session_context("nonexistent")
        assert loaded is None

    def test_list_sessions(self, client: SerenaClient) -> None:
        """Test listing all sessions."""
        for i in range(3):
            context = SessionContext(
                session_id=str(i),  # Use simple session IDs
                query="Test query",
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                hops_executed=1,
                max_hops=5,
                documents_found=1,
                research_depth="quick",
                status="complete"
            )
            client.save_session_context(context)

        sessions = client.list_sessions()
        assert len(sessions) == 3
        # list_sessions returns IDs without "session_" prefix
        assert "0" in sessions
        assert "1" in sessions
        assert "2" in sessions

    def test_save_document_index(self, client: SerenaClient) -> None:
        """Test saving document index."""
        documents = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
        ]
        client.save_document_index(documents)
        assert client.memory_exists("document_index")

    def test_load_document_index(self, client: SerenaClient) -> None:
        """Test loading document index."""
        documents = [
            {"id": "doc1", "title": "Document 1"},
            {"id": "doc2", "title": "Document 2"},
        ]
        client.save_document_index(documents)
        loaded = client.load_document_index()

        assert len(loaded) == 2
        assert loaded[0]["id"] == "doc1"

    def test_load_document_index_not_found(self, client: SerenaClient) -> None:
        """Test loading non-existent document index."""
        loaded = client.load_document_index()
        assert loaded == []

    def test_save_research_patterns(self, client: SerenaClient) -> None:
        """Test saving research patterns."""
        patterns: dict[str, Any] = {
            "pattern1": {"description": "First pattern"},
            "pattern2": {"description": "Second pattern"},
        }
        client.save_research_patterns(patterns)
        assert client.memory_exists("research_patterns")

    def test_load_research_patterns(self, client: SerenaClient) -> None:
        """Test loading research patterns."""
        patterns: dict[str, Any] = {
            "pattern1": {"description": "First pattern"},
            "pattern2": {"description": "Second pattern"},
        }
        client.save_research_patterns(patterns)
        loaded = client.load_research_patterns()

        assert len(loaded) == 2
        assert loaded["pattern1"]["description"] == "First pattern"

    def test_load_research_patterns_not_found(self, client: SerenaClient) -> None:
        """Test loading non-existent research patterns."""
        loaded = client.load_research_patterns()
        assert loaded == {}

    def test_save_knowledge_base(self, client: SerenaClient) -> None:
        """Test saving knowledge base."""
        knowledge: dict[str, Any] = {
            "topic1": {"content": "Knowledge 1"},
            "topic2": {"content": "Knowledge 2"},
        }
        client.save_knowledge_base(knowledge)
        assert client.memory_exists("knowledge_base")

    def test_load_knowledge_base(self, client: SerenaClient) -> None:
        """Test loading knowledge base."""
        knowledge: dict[str, Any] = {
            "topic1": {"content": "Knowledge 1"},
            "topic2": {"content": "Knowledge 2"},
        }
        client.save_knowledge_base(knowledge)
        loaded = client.load_knowledge_base()

        assert len(loaded) == 2
        assert loaded["topic1"]["content"] == "Knowledge 1"

    def test_load_knowledge_base_not_found(self, client: SerenaClient) -> None:
        """Test loading non-existent knowledge base."""
        loaded = client.load_knowledge_base()
        assert loaded == {}

    def test_clear_session_memory(self, client: SerenaClient) -> None:
        """Test clearing all sessions."""
        for i in range(3):
            context = SessionContext(
                session_id=str(i),  # Use simple IDs, not "session_0" which gets double-prefixed
                query="Test query",
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                hops_executed=1,
                max_hops=5,
                documents_found=1,
                research_depth="quick",
                status="complete"
            )
            client.save_session_context(context)

        # Save patterns to ensure they're not deleted
        client.save_research_patterns({"pattern": "value"})

        client.clear_session_memory()

        sessions = client.list_sessions()
        assert len(sessions) == 0

        # Pattern should still exist
        assert client.memory_exists("research_patterns")

    def test_get_memory_stats(self, client: SerenaClient) -> None:
        """Test getting memory statistics."""
        client.write_memory("test1", "content1")
        client.write_memory("test2", "content2")

        stats = client.get_memory_stats()
        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
        assert "memory_dir" in stats

    def test_load_memory_cache_on_init(self, temp_memory_dir: Path) -> None:
        """Test loading cached memory on initialization."""
        client1 = SerenaClient(memory_dir=temp_memory_dir)
        client1.write_memory("test_key", "test_content")

        client2 = SerenaClient(memory_dir=temp_memory_dir)
        assert client2.memory_exists("test_key")
        assert client2.read_memory("test_key") == "test_content"

    def test_memory_persistence_round_trip(self, client: SerenaClient) -> None:
        """Test complete round-trip memory persistence."""
        original_data = {
            "nested": {
                "value": 42,
                "items": [1, 2, 3]
            }
        }
        client.write_memory("complex_data", json.dumps(original_data))
        loaded_json = client.read_memory("complex_data")
        loaded_data = json.loads(loaded_json)

        assert loaded_data == original_data


class TestSerenaClientIntegration:
    """Integration tests for SerenaClient."""

    @pytest.fixture
    def temp_memory_dir(self) -> Path:
        """Create temporary memory directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def client(self, temp_memory_dir: Path) -> SerenaClient:
        """Create SerenaClient with temporary directory."""
        return SerenaClient(memory_dir=temp_memory_dir)

    def test_full_research_session_workflow(self, client: SerenaClient) -> None:
        """Test complete research session workflow."""
        # Create and save a session
        now = datetime.utcnow()
        context = SessionContext(
            session_id="research_001",
            query="Deep learning applications",
            created_at=now,
            last_updated=now,
            hops_executed=3,
            max_hops=5,
            documents_found=15,
            research_depth="deep",
            status="complete",
            findings_summary="Found 15 relevant documents on deep learning",
            execution_time_seconds=45.5,
            documents=[
                {"id": "doc1", "title": "ML Basics"},
                {"id": "doc2", "title": "Neural Networks"}
            ],
            sources=[
                {"url": "https://example.com/1", "title": "Source 1"}
            ]
        )
        client.save_session_context(context)

        # Save document index
        client.save_document_index([
            {"id": "doc1", "title": "ML Basics"},
            {"id": "doc2", "title": "Neural Networks"}
        ])

        # Save patterns learned
        client.save_research_patterns({
            "research_001": {
                "effective_keywords": ["deep learning", "neural networks"],
                "best_sources": ["arxiv.org", "github.com"]
            }
        })

        # Load everything back
        loaded_context = client.load_session_context("research_001")
        loaded_docs = client.load_document_index()
        loaded_patterns = client.load_research_patterns()

        assert loaded_context is not None
        assert loaded_context.findings_summary == "Found 15 relevant documents on deep learning"
        assert len(loaded_docs) == 2
        assert "research_001" in loaded_patterns

    def test_multiple_client_instances_share_memory(self, temp_memory_dir: Path) -> None:
        """Test that multiple client instances share memory."""
        client1 = SerenaClient(memory_dir=temp_memory_dir)
        client2 = SerenaClient(memory_dir=temp_memory_dir)

        client1.write_memory("shared_key", "shared_value")

        # Client2 should see it immediately through disk
        client2._load_memory_cache()
        assert client2.read_memory("shared_key") == "shared_value"
