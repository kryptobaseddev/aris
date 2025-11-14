"""Database connection and session management with SQLAlchemy."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from aris.storage.models import Base

logger = logging.getLogger(__name__)


# Global session factory (initialized by DatabaseManager)
_SessionFactory: Optional[sessionmaker] = None


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class DatabaseManager:
    """Manages database connection and session lifecycle with SQLAlchemy.

    Provides:
    - Database initialization and schema management
    - Session factory for ORM operations
    - Transaction management with context managers
    - Database backup and statistics

    Example:
        from aris.core.config import ConfigManager
        from aris.storage.database import DatabaseManager

        config = ConfigManager.get_instance().get_config()
        db_manager = DatabaseManager(config.database_path)
        db_manager.initialize_database()

        with db_manager.session_scope() as session:
            topic = Topic(name="AI Research")
            session.add(topic)
    """

    def __init__(self, database_path: Path, echo: bool = False):
        """Initialize database manager.

        Args:
            database_path: Path to SQLite database file
            echo: Enable SQL query logging for debugging
        """
        self.database_path = database_path
        self.database_url = f"sqlite:///{database_path}"

        # Ensure database directory exists
        database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with SQLite-specific settings
        self.engine = create_engine(
            self.database_url,
            echo=echo,
            connect_args={"check_same_thread": False},  # Allow multi-threaded access
            poolclass=StaticPool,  # Use static pool for SQLite
        )

        # Create session factory
        global _SessionFactory
        _SessionFactory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        logger.info(f"Database manager initialized: {self.database_path}")

    async def initialize(self) -> None:
        """Initialize database and create tables.

        This is a convenience method that wraps create_tables() for
        backward compatibility with tests.
        """
        self.create_all_tables()

    def create_all_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
        logger.info("All database tables created")

    def drop_all_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        Base.metadata.drop_all(self.engine)
        logger.warning("All database tables dropped")

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session instance

        Raises:
            RuntimeError: If DatabaseManager not initialized
        """
        if _SessionFactory is None:
            raise RuntimeError("DatabaseManager not initialized")
        return _SessionFactory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations.

        Yields:
            SQLAlchemy session with automatic commit/rollback

        Example:
            with db_manager.session_scope() as session:
                session.add(topic)
                # Automatically commits on success, rolls back on error
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize_database(self) -> None:
        """Initialize database with schema."""
        logger.info("Initializing database schema...")
        self.create_all_tables()
        logger.info("Database initialization complete")

    def backup_database(self, backup_path: Path) -> None:
        """Create a backup of the database file.

        Args:
            backup_path: Path to backup file

        Raises:
            FileNotFoundError: If database file does not exist
        """
        import shutil

        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.database_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

    def get_table_stats(self) -> dict[str, int]:
        """Get row counts for all tables.

        Returns:
            Dictionary mapping table names to row counts
        """
        stats = {}
        with self.session_scope() as session:
            for table in Base.metadata.sorted_tables:
                count = session.execute(
                    text(f"SELECT COUNT(*) FROM {table.name}")
                ).scalar()
                stats[table.name] = count
        return stats

    def close(self) -> None:
        """Close database connection and dispose of engine."""
        self.engine.dispose()
        logger.info("Database connection closed")


def get_session() -> Session:
    """Get a database session from the global session factory.

    Returns:
        SQLAlchemy session instance

    Raises:
        RuntimeError: If DatabaseManager not initialized

    Example:
        from aris.storage.database import get_session
        from aris.storage.repositories import TopicRepository

        session = get_session()
        try:
            repo = TopicRepository(session)
            topics = repo.get_all()
        finally:
            session.close()
    """
    if _SessionFactory is None:
        raise RuntimeError(
            "DatabaseManager not initialized. "
            "Create a DatabaseManager instance first."
        )
    return _SessionFactory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope using the global session factory.

    Yields:
        SQLAlchemy session with automatic commit/rollback

    Example:
        from aris.storage.database import session_scope
        from aris.storage.models import Topic

        with session_scope() as session:
            topic = Topic(name="AI Research")
            session.add(topic)
            # Automatically commits on success
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
