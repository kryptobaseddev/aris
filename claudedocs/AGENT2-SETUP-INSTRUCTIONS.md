# Agent 2 Setup Instructions - Database Schema

**Previous Agent**: Agent 1 (Configuration System) - ✅ COMPLETE
**Your Task**: Implement SQLite database schema and ORM layer
**Next Agent**: Agent 3 (CLI Foundation)

---

## Quick Start

### What Agent 1 Completed

✅ **Configuration System**
- `ConfigManager` singleton for global config access
- `SecureKeyManager` for API key storage in system keyring
- `.env.example` template with all ARIS_ variables
- CLI commands for config management
- Complete unit tests (30+ tests passing)

### What You Can Use Immediately

```python
from aris.core.config import ConfigManager

# Get configuration
config_manager = ConfigManager.get_instance()
config = config_manager.load()

# Access database path
db_path = config.database_path  # Path.cwd() / ".aris" / "metadata.db"

# Ensure directories exist
config.ensure_directories()  # Creates .aris directory

# Access other settings
research_dir = config.research_dir
cache_dir = config.cache_dir
similarity_threshold = config.semantic_similarity_threshold
```

---

## Your Atomic Task

**Implement complete SQLite database schema and ORM layer for ARIS**

### Requirements

1. **Create 8 Core Tables**
   - `topics` - Research entities
   - `claims` - Atomic facts with confidence scores
   - `sources` - Source provenance tracking
   - `claim_sources` - Many-to-many relationship
   - `conflicts` - Contradiction tracking
   - `tasks` - DAG task queue (future use)
   - `validation_logs` - Multi-model consensus tracking
   - `document_versions` - Git-like version history

2. **SQLAlchemy Models**
   - Create `src/aris/storage/models.py`
   - All models as SQLAlchemy ORM classes
   - Proper relationships and foreign keys
   - Indexes for performance

3. **Alembic Migrations**
   - Initialize Alembic in project
   - Create initial migration
   - Migration script tested

4. **Database Manager**
   - Create `src/aris/storage/database.py`
   - Engine creation with config integration
   - Session factory
   - Transaction management helpers

5. **CRUD Operations**
   - Create `src/aris/storage/repositories/`
   - Repository pattern for each entity type
   - Basic CRUD operations

6. **Unit Tests**
   - Create `tests/unit/test_database.py`
   - Test all models and relationships
   - Test CRUD operations
   - Test migrations

---

## Database Schema Reference

### Table: topics

Research topics/entities. One topic = one research document.

```sql
CREATE TABLE topics (
    id TEXT PRIMARY KEY,              -- UUID
    title TEXT NOT NULL,              -- Document title
    embedding BLOB,                   -- Vector embedding (pickled numpy array)
    state TEXT NOT NULL,              -- "draft", "active", "archived"
    confidence REAL NOT NULL,         -- 0.0-1.0
    document_path TEXT NOT NULL,      -- Relative path to markdown file
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_topics_state (state),
    INDEX idx_topics_confidence (confidence),
    INDEX idx_topics_updated_at (updated_at)
);
```

### Table: claims

Atomic facts extracted from research. Each claim validated by consensus.

```sql
CREATE TABLE claims (
    id TEXT PRIMARY KEY,              -- UUID
    topic_id TEXT NOT NULL,           -- Foreign key to topics
    content TEXT NOT NULL,            -- The actual claim text
    confidence REAL NOT NULL,         -- Consensus confidence 0.0-1.0
    validation_status TEXT NOT NULL,  -- "pending", "validated", "rejected"
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_claims_topic (topic_id),
    INDEX idx_claims_confidence (confidence),
    INDEX idx_claims_validation_status (validation_status)
);
```

### Table: sources

Source provenance for claims. Authority scoring for credibility.

```sql
CREATE TABLE sources (
    id TEXT PRIMARY KEY,              -- UUID
    url TEXT NOT NULL UNIQUE,         -- Source URL
    authority_score REAL NOT NULL,    -- 0.0-1.0 credibility score
    content_hash TEXT NOT NULL,       -- SHA256 of content
    source_type TEXT NOT NULL,        -- "academic", "news", "blog", etc.
    title TEXT,                       -- Source title
    author TEXT,                      -- Source author
    published_date TIMESTAMP,         -- When source published
    accessed_at TIMESTAMP NOT NULL,   -- When we accessed it
    created_at TIMESTAMP NOT NULL,

    -- Indexes
    INDEX idx_sources_url (url),
    INDEX idx_sources_authority (authority_score),
    INDEX idx_sources_type (source_type)
);
```

### Table: claim_sources

Many-to-many relationship between claims and sources.

```sql
CREATE TABLE claim_sources (
    id TEXT PRIMARY KEY,              -- UUID
    claim_id TEXT NOT NULL,           -- Foreign key to claims
    source_id TEXT NOT NULL,          -- Foreign key to sources
    relevance_score REAL NOT NULL,    -- How relevant source is to claim
    quote TEXT,                       -- Exact quote from source
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,

    UNIQUE (claim_id, source_id),

    -- Indexes
    INDEX idx_claim_sources_claim (claim_id),
    INDEX idx_claim_sources_source (source_id)
);
```

### Table: conflicts

Track contradictions between claims.

```sql
CREATE TABLE conflicts (
    id TEXT PRIMARY KEY,              -- UUID
    claim_a_id TEXT NOT NULL,         -- First conflicting claim
    claim_b_id TEXT NOT NULL,         -- Second conflicting claim
    conflict_type TEXT NOT NULL,      -- "direct_contradiction", "partial_overlap"
    severity REAL NOT NULL,           -- 0.0-1.0
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution TEXT,                  -- How conflict was resolved
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,

    FOREIGN KEY (claim_a_id) REFERENCES claims(id) ON DELETE CASCADE,
    FOREIGN KEY (claim_b_id) REFERENCES claims(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_conflicts_resolved (resolved),
    INDEX idx_conflicts_severity (severity)
);
```

### Table: validation_logs

Multi-model consensus validation tracking.

```sql
CREATE TABLE validation_logs (
    id TEXT PRIMARY KEY,              -- UUID
    claim_id TEXT NOT NULL,           -- Foreign key to claims
    model_name TEXT NOT NULL,         -- "claude-4.5", "gpt-5", etc.
    agrees BOOLEAN NOT NULL,          -- Model agrees with claim?
    confidence REAL NOT NULL,         -- Model's confidence 0.0-1.0
    reasoning TEXT,                   -- Model's reasoning
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_validation_logs_claim (claim_id),
    INDEX idx_validation_logs_model (model_name)
);
```

### Table: document_versions

Git-like version history for documents.

```sql
CREATE TABLE document_versions (
    id TEXT PRIMARY KEY,              -- UUID
    topic_id TEXT NOT NULL,           -- Foreign key to topics
    version INTEGER NOT NULL,         -- Version number
    content_hash TEXT NOT NULL,       -- SHA256 of content
    diff TEXT,                        -- Unified diff from previous version
    commit_message TEXT,              -- Description of changes
    created_at TIMESTAMP NOT NULL,

    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,

    UNIQUE (topic_id, version),

    -- Indexes
    INDEX idx_document_versions_topic (topic_id),
    INDEX idx_document_versions_created (created_at)
);
```

### Table: tasks

DAG task queue for parallel execution (future use).

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,              -- UUID
    topic_id TEXT,                    -- Optional: related topic
    agent_type TEXT NOT NULL,         -- "researcher", "validator", etc.
    task_spec TEXT NOT NULL,          -- JSON task specification
    status TEXT NOT NULL,             -- "pending", "running", "completed", "failed"
    dependencies TEXT,                -- JSON array of task IDs
    result TEXT,                      -- JSON result
    error TEXT,                       -- Error message if failed
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_agent_type (agent_type),
    INDEX idx_tasks_topic (topic_id)
);
```

---

## Implementation Checklist

### Phase 1: Setup (30 minutes)
- [ ] Create `src/aris/storage/__init__.py`
- [ ] Create `src/aris/storage/models.py`
- [ ] Create `src/aris/storage/database.py`
- [ ] Initialize Alembic: `alembic init alembic`
- [ ] Configure Alembic to use config.database_path

### Phase 2: Models (1 hour)
- [ ] Create SQLAlchemy Base
- [ ] Implement Topic model
- [ ] Implement Claim model
- [ ] Implement Source model
- [ ] Implement ClaimSource model
- [ ] Implement Conflict model
- [ ] Implement ValidationLog model
- [ ] Implement DocumentVersion model
- [ ] Implement Task model
- [ ] Add relationships between models

### Phase 3: Database Manager (45 minutes)
- [ ] Implement get_engine() function
- [ ] Implement get_session() context manager
- [ ] Implement create_all_tables() function
- [ ] Implement drop_all_tables() function (testing only)
- [ ] Add transaction helpers

### Phase 4: Migrations (30 minutes)
- [ ] Create initial Alembic migration
- [ ] Test upgrade
- [ ] Test downgrade
- [ ] Document migration commands

### Phase 5: Repositories (1 hour)
- [ ] Create `src/aris/storage/repositories/__init__.py`
- [ ] Create TopicRepository with CRUD
- [ ] Create ClaimRepository with CRUD
- [ ] Create SourceRepository with CRUD
- [ ] Create repository factory

### Phase 6: Testing (1 hour)
- [ ] Create `tests/unit/test_database.py`
- [ ] Test model creation
- [ ] Test relationships
- [ ] Test CRUD operations
- [ ] Test migrations
- [ ] Run all tests and verify passing

### Phase 7: Documentation (30 minutes)
- [ ] Document database schema
- [ ] Create handoff for Agent 3
- [ ] Update configuration integration notes

---

## Code Templates

### Database Manager Template

```python
# src/aris/storage/database.py

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aris.core.config import ConfigManager
from aris.storage.models import Base


def get_engine():
    """Get SQLAlchemy engine using config database path."""
    config = ConfigManager.get_instance().get_config()
    db_path = config.database_path

    # Ensure directory exists
    config.ensure_directories()

    # Create engine
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,  # Set True for SQL logging
        connect_args={"check_same_thread": False}  # SQLite specific
    )
    return engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup.

    Example:
        with get_session() as session:
            topic = session.query(Topic).first()
    """
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def drop_all_tables() -> None:
    """Drop all database tables (testing only)."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
```

### Model Template

```python
# src/aris/storage/models.py

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    LargeBinary, String, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Topic(Base):
    """Research topic/entity."""

    __tablename__ = "topics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    embedding = Column(LargeBinary, nullable=True)  # Pickled numpy array
    state = Column(String, nullable=False, default="draft")
    confidence = Column(Float, nullable=False, default=0.0)
    document_path = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    claims = relationship("Claim", back_populates="topic", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, title={self.title}, confidence={self.confidence})>"


# Add remaining models...
```

### Repository Template

```python
# src/aris/storage/repositories/topic_repository.py

from typing import List, Optional

from sqlalchemy.orm import Session

from aris.storage.models import Topic


class TopicRepository:
    """Repository for Topic entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, title: str, document_path: str) -> Topic:
        """Create new topic."""
        topic = Topic(title=title, document_path=document_path)
        self.session.add(topic)
        self.session.flush()
        return topic

    def get_by_id(self, topic_id: str) -> Optional[Topic]:
        """Get topic by ID."""
        return self.session.query(Topic).filter(Topic.id == topic_id).first()

    def get_all(self) -> List[Topic]:
        """Get all topics."""
        return self.session.query(Topic).all()

    def update(self, topic: Topic) -> Topic:
        """Update topic."""
        self.session.flush()
        return topic

    def delete(self, topic: Topic) -> None:
        """Delete topic."""
        self.session.delete(topic)
        self.session.flush()
```

---

## Validation Requirements

Before marking complete:

1. **All tables created successfully**
   ```python
   from aris.storage.database import create_all_tables
   create_all_tables()
   # No errors
   ```

2. **Can create and query all models**
   ```python
   from aris.storage.database import get_session
   from aris.storage.models import Topic

   with get_session() as session:
       topic = Topic(title="Test", document_path="test.md")
       session.add(topic)
       session.commit()

       retrieved = session.query(Topic).first()
       assert retrieved.title == "Test"
   ```

3. **Relationships work**
   ```python
   # Topic → Claims relationship
   topic.claims  # Should return list of claims
   claim.topic   # Should return parent topic
   ```

4. **Migrations work**
   ```bash
   alembic upgrade head   # Should succeed
   alembic downgrade base # Should succeed
   alembic upgrade head   # Should succeed again
   ```

5. **All tests pass**
   ```bash
   pytest tests/unit/test_database.py -v
   # All tests passing
   ```

---

## Handoff Requirements

Your output must include:

1. **All implemented files with complete code**
   - `src/aris/storage/models.py`
   - `src/aris/storage/database.py`
   - `src/aris/storage/repositories/` (all repositories)
   - `tests/unit/test_database.py`
   - Alembic migration files

2. **Database schema documentation**
   - Complete schema with all tables
   - Relationship documentation
   - Index strategy

3. **Setup instructions for Agent 3**
   - How to use database manager
   - How to create sessions
   - How to use repositories

4. **Validation evidence**
   - All tables created
   - All tests passing
   - Migrations working
   - Integration with config verified

---

## Resources

- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **Configuration Access**: See `AGENT1-HANDOFF-CONFIGURATION.md`
- **Original Architecture**: See `claudedocs/ARIS-Architecture-Blueprint.md` (section 4.2)

---

**Ready to Start**: All prerequisites from Agent 1 are complete.
**Estimated Time**: 4-5 hours for complete implementation.
**Next Agent**: Agent 3 (CLI Foundation) will use your database layer.

Good luck! 🚀
