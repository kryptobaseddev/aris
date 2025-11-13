"""Unit tests for database management."""

import pytest
from pathlib import Path
import tempfile
import shutil

from aris.storage.database import DatabaseManager
from aris.storage.models import Topic, Document, Source


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DatabaseManager instance."""
        return DatabaseManager(temp_db_path)

    def test_initialization(self, db_manager):
        """Test database manager initialization."""
        assert db_manager.database_path.parent.exists()
        assert db_manager.engine is not None

    def test_create_tables(self, db_manager, temp_db_path):
        """Test table creation."""
        db_manager.create_all_tables()
        assert temp_db_path.exists()

        # Get table stats to verify tables were created
        stats = db_manager.get_table_stats()
        expected_tables = {
            "topics",
            "documents",
            "sources",
            "document_sources",
            "relationships",
            "research_sessions",
            "research_hops",
            "conflicts"
        }
        assert set(stats.keys()) == expected_tables
        assert all(count == 0 for count in stats.values())

    def test_session_scope(self, db_manager):
        """Test session scope context manager."""
        db_manager.initialize_database()

        with db_manager.session_scope() as session:
            topic = Topic(name="Test Topic", description="Test description")
            session.add(topic)

        # Verify topic was committed
        with db_manager.session_scope() as session:
            topics = session.query(Topic).all()
            assert len(topics) == 1
            assert topics[0].name == "Test Topic"

    def test_session_scope_rollback(self, db_manager):
        """Test session scope rollback on error."""
        db_manager.initialize_database()

        try:
            with db_manager.session_scope() as session:
                topic = Topic(name="Test Topic")
                session.add(topic)
                raise Exception("Test error")
        except Exception:
            pass

        # Verify topic was rolled back
        with db_manager.session_scope() as session:
            topics = session.query(Topic).all()
            assert len(topics) == 0

    def test_backup_database(self, db_manager, temp_db_path):
        """Test database backup."""
        db_manager.initialize_database()

        # Add some data
        with db_manager.session_scope() as session:
            topic = Topic(name="Test Topic")
            session.add(topic)

        # Create backup
        backup_path = temp_db_path.parent / "backup.db"
        db_manager.backup_database(backup_path)

        assert backup_path.exists()
        assert backup_path.stat().st_size > 0

    def test_get_table_stats(self, db_manager):
        """Test table statistics."""
        db_manager.initialize_database()

        # Add test data
        with db_manager.session_scope() as session:
            topic = Topic(name="Topic 1")
            session.add(topic)

        stats = db_manager.get_table_stats()
        assert stats["topics"] == 1
        assert stats["documents"] == 0
