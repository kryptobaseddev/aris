# WAVE 2 HANDOFF PACKAGE

**Date**: 2025-11-12
**From**: Wave 1 (Foundation Infrastructure)
**To**: Wave 2 (Core Research Components)
**Status**: Conditional Handoff with Documented Limitations

---

## Executive Summary

Wave 1 has delivered a **70% complete foundation** with working configuration management, defined database schema, and implemented Git operations. Wave 2 can proceed with documented workarounds for incomplete components.

### What You're Getting

✅ **Fully Functional**:
- Configuration management system (87% test coverage)
- Secure API key storage via system keyring
- SQLAlchemy database models for all 8 tables
- Git repository management implementation

⚠️ **Functional But Untested**:
- Database operations (0% test coverage)
- Git document operations (0% test coverage)
- DocumentStore abstraction (implementation exists)

❌ **Incomplete/Missing**:
- CLI main entry point (file doesn't exist)
- Repository pattern classes
- Alembic database migrations
- Integration tests
- Most CLI commands

---

## Quick Start for Wave 2

### 1. Set Up Your Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Verify dependencies
pip list | grep -E "(click|rich|pydantic|sqlalchemy|gitpython|keyring)"

# Set PYTHONPATH
export PYTHONPATH=/mnt/projects/aris-tool/src
```

### 2. Initialize Configuration

```python
from aris.core.config import ConfigManager

# Load configuration (creates singleton)
config_manager = ConfigManager.get_instance()
config = config_manager.load()

# Validate configuration
validation = config_manager.validate()
if not validation["valid"]:
    print("Config issues:", validation["errors"])

# Access configuration
print(f"Database path: {config.database_path}")
print(f"Research dir: {config.research_dir}")
```

### 3. Initialize Database

```python
from aris.storage.database import DatabaseManager

# Create database manager
db_manager = DatabaseManager(config.database_path)
db_manager.initialize()  # Creates SQLite database and tables

# Verify tables created
tables = db_manager.list_tables()
print(f"Tables created: {tables}")
```

### 4. Use Git Operations

```python
from aris.storage.git_manager import GitManager
from pathlib import Path

# Initialize Git manager
git_mgr = GitManager(Path(config.research_dir))

# Commit a document
commit_hash = git_mgr.commit_document(
    Path(config.research_dir) / "test.md",
    "Create: Test document",
    author_name="Wave 2 Agent"
)

# Get document history
history = git_mgr.get_document_history(Path(config.research_dir) / "test.md")
```

### 5. Work Around Missing Components

```python
# Don't use repositories (they don't exist)
# Instead, use SQLAlchemy ORM directly:

from aris.storage.models import Topic, Document, Source
from aris.storage.database import get_session

with get_session(db_manager) as session:
    # Create a topic
    topic = Topic(name="AI Research", description="Research on AI systems")
    session.add(topic)
    session.commit()

    # Query topics
    topics = session.query(Topic).filter_by(name="AI Research").all()
```

---

## Available APIs

### Configuration API

**Module**: `aris.core.config`
**Status**: ✅ Fully tested and documented

```python
from aris.core.config import ConfigManager, ConfigProfile

# Get singleton instance
config_manager = ConfigManager.get_instance()

# Load configuration with profile
config = config_manager.load(profile=ConfigProfile.DEVELOPMENT)

# Get API keys
tavily_key = config_manager.get_api_key("tavily")
anthropic_key = config_manager.get_api_key("anthropic")
openai_key = config_manager.get_api_key("openai")
google_key = config_manager.get_api_key("google")

# Set API key
config_manager.set_api_key("provider", "key_value", persist=True)

# Validate configuration
validation = config_manager.validate()
if validation["valid"]:
    print("Configuration is valid")
else:
    print("Errors:", validation["errors"])
    print("Warnings:", validation["warnings"])

# Get configuration summary
summary = config_manager.get_config_summary(mask_secrets=True)

# Access configuration values
config = config_manager.get_config()
print(config.database_path)
print(config.research_dir)
print(config.cache_dir)
print(config.max_hops)
print(config.semantic_similarity_threshold)
```

**Configuration Parameters Available**:
```python
# Paths
config.project_root: Path
config.research_dir: Path
config.database_path: Path
config.cache_dir: Path

# API Keys (via config_manager.get_api_key())
tavily_api_key: str
anthropic_api_key: str
openai_api_key: str
google_api_key: str | None

# LLM Configuration
config.preferred_llm: str  # "gemini_pro_2.0"
config.fallback_llm: str   # "claude_sonnet_4.5"

# Research Parameters
config.max_hops: int                      # 5
config.semantic_similarity_threshold: float  # 0.85
config.confidence_target: float           # 0.70
config.early_stop_confidence: float       # 0.85

# Budgets (USD)
config.default_budget_quick: float    # 0.20
config.default_budget_standard: float # 0.50
config.default_budget_deep: float     # 2.00
config.monthly_budget_limit: float    # 50.00

# Performance
config.cache_ttl_seconds: int         # 3600
config.max_parallel_searches: int     # 5
config.request_timeout_seconds: int   # 30

# Quality
config.min_source_credibility: float              # 0.5
config.require_validation_below_confidence: float # 0.6
```

---

### Database API

**Module**: `aris.storage.database`
**Status**: ⚠️ Implemented but untested

```python
from aris.storage.database import DatabaseManager, get_session
from aris.storage.models import (
    Topic, Document, Source, DocumentSource,
    Relationship, ResearchSession, ResearchHop, Conflict
)

# Initialize database
db_manager = DatabaseManager(Path("~/.aris/aris.db"))
db_manager.initialize()  # Creates all 8 tables

# Get connection (context manager)
with get_session(db_manager) as session:
    # Create entities
    topic = Topic(name="AI", description="Artificial Intelligence")
    session.add(topic)
    session.commit()

    # Query entities
    topics = session.query(Topic).filter_by(name="AI").all()

    # Update entities
    topic.description = "Advanced AI Research"
    session.commit()

    # Delete entities
    session.delete(topic)
    session.commit()
```

**Database Models**:

1. **Topic** (`topics` table):
   - `id`: UUID primary key
   - `name`: Unique topic name (indexed)
   - `description`: Optional description
   - `created_at`, `updated_at`: Timestamps
   - **Relationships**: `documents`, `research_sessions`

2. **Document** (`documents` table):
   - `id`: UUID primary key
   - `topic_id`: Foreign key to topics
   - `title`: Document title
   - `content`: Full document text
   - `content_hash`: SHA-256 hash for deduplication
   - `embedding`: Vector embedding (JSON)
   - `document_type`: Type classification
   - `file_path`: Optional file path
   - `created_at`, `updated_at`: Timestamps
   - **Relationships**: `topic`, `sources` (many-to-many), `relationships`

3. **Source** (`sources` table):
   - `id`: UUID primary key
   - `url`: Source URL (unique, indexed)
   - `title`: Source title
   - `author`: Optional author
   - `published_date`: Optional publication date
   - `credibility_score`: Credibility rating (0-1)
   - `source_type`: Type classification
   - `accessed_at`: When source was accessed
   - **Relationships**: `documents` (many-to-many)

4. **DocumentSource** (`document_sources` table):
   - Many-to-many association between documents and sources
   - `document_id`, `source_id`: Composite primary key
   - `citation_count`: Number of citations
   - `relevance_score`: Relevance rating
   - `added_at`: When association was created

5. **Relationship** (`relationships` table):
   - `id`: UUID primary key
   - `source_document_id`, `target_document_id`: Document references
   - `relationship_type`: Type of relationship
   - `confidence`: Confidence score (0-1)
   - `description`: Optional description
   - `created_at`: Timestamp

6. **ResearchSession** (`research_sessions` table):
   - `id`: UUID primary key
   - `topic_id`: Foreign key to topics
   - `query`: Original research query
   - `status`: Session status enum
   - `confidence_score`: Overall confidence
   - `started_at`, `completed_at`: Timestamps
   - **Relationships**: `topic`, `research_hops`

7. **ResearchHop** (`research_hops` table):
   - `id`: UUID primary key
   - `session_id`: Foreign key to research_sessions
   - `hop_number`: Sequential hop number
   - `query`: Hop query
   - `sources_found`: Number of sources
   - `confidence_score`: Hop confidence
   - `created_at`: Timestamp
   - **Relationships**: `session`

8. **Conflict** (`conflicts` table):
   - `id`: UUID primary key
   - `document_id_1`, `document_id_2`: Conflicting documents
   - `conflict_type`: Type of conflict
   - `severity`: Conflict severity
   - `description`: Conflict description
   - `resolution_status`: Resolution status
   - `detected_at`, `resolved_at`: Timestamps

**Important Notes**:
- ⚠️ **No Repository Classes**: Use ORM directly (see examples above)
- ⚠️ **No Migrations**: Schema created programmatically (no Alembic)
- ⚠️ **Not Tested**: Validate operations work before extensive use
- ⚠️ **Session Management**: Always use `get_session()` context manager

---

### Git API

**Module**: `aris.storage.git_manager`
**Status**: ⚠️ Implemented but untested

```python
from aris.storage.git_manager import GitManager
from pathlib import Path

# Initialize Git manager for repository
git_mgr = GitManager(Path("/path/to/research"))

# Commit a document
commit_hash = git_mgr.commit_document(
    file_path=Path("/path/to/research/doc.md"),
    message="Create: Initial research document",
    author_name="ARIS",
    author_email="aris@local"
)

# Get document history
history = git_mgr.get_document_history(
    file_path=Path("/path/to/research/doc.md"),
    max_commits=10
)

# Each history entry:
# {
#     'commit_hash': str,
#     'author': str,
#     'date': datetime,
#     'message': str,
#     'changes': str  # Diff output
# }

# Get diff between commits
diff = git_mgr.get_diff(
    file_path=Path("/path/to/research/doc.md"),
    commit_hash_a="abc123",
    commit_hash_b="def456"
)

# Get file content at specific commit
content = git_mgr.get_file_at_commit(
    file_path=Path("/path/to/research/doc.md"),
    commit_hash="abc123"
)

# Check if file has uncommitted changes
has_changes = git_mgr.has_uncommitted_changes(
    file_path=Path("/path/to/research/doc.md")
)

# Get repository status
status = git_mgr.get_status()
# Returns dict with:
# {
#     'untracked': List[Path],
#     'modified': List[Path],
#     'staged': List[Path]
# }
```

**DocumentStore High-Level API**:
```python
from aris.storage.document_store import DocumentStore

# Initialize document store (integrates Git + Database)
doc_store = DocumentStore(config)

# Save document (auto-commits to Git)
doc_id = doc_store.save_document(
    title="Research Document",
    content="Document content here...",
    topic_name="AI Research",
    sources=["https://example.com"],
    metadata={"custom": "metadata"}
)

# Load document
document = doc_store.load_document(doc_id)

# Search documents
results = doc_store.search_documents(
    query="AI research",
    topic_name="AI Research",
    limit=10
)

# Get document history
history = doc_store.get_document_history(doc_id)
```

**Important Notes**:
- ⚠️ **Not Tested**: Verify operations before using extensively
- ⚠️ **Git Credentials**: Ensure Git is configured with name/email
- ✅ **Auto-Initialize**: Repository auto-creates if doesn't exist
- ✅ **Error Handling**: Good error messages for Git failures

---

## Working Around Missing Components

### Problem 1: No Repository Classes

**Issue**: `storage/__init__.py` references repositories that don't exist:
```python
from aris.storage.repositories import (
    TopicRepository,
    DocumentRepository,
    # ... etc - ALL MISSING
)
```

**Workaround**: Use SQLAlchemy ORM directly:
```python
# Don't do this (doesn't exist):
# topic_repo = TopicRepository(session)
# topic = topic_repo.get_by_name("AI")

# Do this instead:
from aris.storage.models import Topic
topic = session.query(Topic).filter_by(name="AI").first()

# CRUD operations:
# Create
topic = Topic(name="AI", description="Research")
session.add(topic)
session.commit()

# Read
topic = session.query(Topic).filter_by(id=topic_id).first()
topics = session.query(Topic).all()

# Update
topic.description = "Updated description"
session.commit()

# Delete
session.delete(topic)
session.commit()
```

### Problem 2: No Alembic Migrations

**Issue**: Schema changes can't be version controlled

**Workaround**: Use programmatic initialization:
```python
# Database schema is created programmatically:
db_manager.initialize()  # Creates all tables

# For schema changes during Wave 2:
# 1. Modify models in src/aris/storage/models.py
# 2. Drop and recreate database (development only):
db_manager.drop_all_tables()
db_manager.initialize()

# 3. For production, you'll need Alembic (add later)
```

### Problem 3: No CLI Entry Point

**Issue**: `aris` command doesn't work

**Workaround**: Use Python APIs directly:
```python
# Don't try to use CLI:
# os.system("aris init --name test")  # Doesn't work

# Use Python APIs instead:
from aris.core.config import ConfigManager
config_manager = ConfigManager.get_instance()
config = config_manager.load()
```

### Problem 4: No Integration Tests

**Issue**: Can't verify components work together

**Workaround**: Test as you integrate:
```python
# Add validation checks in your code:
def initialize_system():
    """Initialize ARIS system with validation."""
    # 1. Load config
    config_manager = ConfigManager.get_instance()
    config = config_manager.load()

    # 2. Validate config
    validation = config_manager.validate()
    assert validation["valid"], f"Config invalid: {validation['errors']}"

    # 3. Initialize database
    db_manager = DatabaseManager(config.database_path)
    db_manager.initialize()

    # 4. Verify tables exist
    tables = db_manager.list_tables()
    expected = {"topics", "documents", "sources", "document_sources",
                "relationships", "research_sessions", "research_hops", "conflicts"}
    assert set(tables) == expected, f"Missing tables: {expected - set(tables)}"

    # 5. Initialize Git
    git_mgr = GitManager(Path(config.research_dir))
    assert git_mgr.repo is not None, "Git initialization failed"

    return config, db_manager, git_mgr
```

---

## Integration Patterns

### Pattern 1: Research Session with Full Stack

```python
from aris.core.config import ConfigManager
from aris.storage.database import DatabaseManager, get_session
from aris.storage.models import Topic, ResearchSession, ResearchHop
from aris.storage.document_store import DocumentStore
from pathlib import Path

# 1. Initialize components
config = ConfigManager.get_instance().get_config()
db_manager = DatabaseManager(config.database_path)
db_manager.initialize()
doc_store = DocumentStore(config)

# 2. Create research session
with get_session(db_manager) as session:
    # Create topic
    topic = Topic(name="AI Safety", description="Research on AI safety")
    session.add(topic)
    session.flush()  # Get topic.id

    # Create research session
    research_session = ResearchSession(
        topic_id=topic.id,
        query="How can we ensure AI systems are safe?",
        status="in_progress"
    )
    session.add(research_session)
    session.flush()

    # Create research hop
    hop = ResearchHop(
        session_id=research_session.id,
        hop_number=1,
        query="AI safety research papers",
        sources_found=5,
        confidence_score=0.75
    )
    session.add(hop)
    session.commit()

    # Save document with Git versioning
    doc_id = doc_store.save_document(
        title="AI Safety Research Summary",
        content="Summary of research findings...",
        topic_name="AI Safety",
        sources=["https://arxiv.org/paper1", "https://arxiv.org/paper2"]
    )

    print(f"Research session {research_session.id} created")
    print(f"Document {doc_id} saved and committed to Git")
```

### Pattern 2: Document Deduplication

```python
from aris.storage.models import Document
from aris.storage.database import get_session
import hashlib

def check_duplicate(session, content: str, threshold: float = 0.85):
    """Check if document is duplicate using content hash."""
    # Calculate content hash
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Check for exact match
    existing = session.query(Document).filter_by(content_hash=content_hash).first()
    if existing:
        return existing.id, 1.0  # Exact duplicate

    # For semantic similarity, you'd use embeddings:
    # (Wave 2 will implement this)
    # embedding = get_embedding(content)
    # similar_docs = find_similar_by_embedding(session, embedding, threshold)

    return None, 0.0  # Not duplicate

# Usage
with get_session(db_manager) as session:
    doc_id, similarity = check_duplicate(session, "New content...")
    if similarity > 0.85:
        print(f"Duplicate of document {doc_id} (similarity: {similarity})")
    else:
        # Create new document
        doc = Document(
            title="New Document",
            content="New content...",
            content_hash=hashlib.sha256("New content...".encode()).hexdigest()
        )
        session.add(doc)
        session.commit()
```

### Pattern 3: Source Credibility Tracking

```python
from aris.storage.models import Source, Document, document_sources
from aris.storage.database import get_session

def add_source_to_document(session, document_id: str, url: str, credibility: float):
    """Add source with credibility tracking."""
    # Get or create source
    source = session.query(Source).filter_by(url=url).first()
    if not source:
        source = Source(
            url=url,
            title="Source Title",
            credibility_score=credibility,
            source_type="web"
        )
        session.add(source)
        session.flush()

    # Link document to source
    doc = session.query(Document).filter_by(id=document_id).first()
    if doc and source not in doc.sources:
        doc.sources.append(source)

        # Update association table with relevance
        session.execute(
            document_sources.update().
            where(document_sources.c.document_id == document_id).
            where(document_sources.c.source_id == source.id).
            values(relevance_score=0.9)
        )

    session.commit()

# Usage
with get_session(db_manager) as session:
    add_source_to_document(
        session,
        document_id="doc-123",
        url="https://arxiv.org/paper",
        credibility=0.95
    )
```

---

## Known Issues and Limitations

### Critical Limitations

1. **No CLI Entry Point** (`src/aris/cli/main.py` missing)
   - **Impact**: Cannot execute `aris` command
   - **Workaround**: Use Python APIs directly
   - **Fix Required**: Create main.py with Click command group

2. **No Repository Pattern** (All repository classes missing)
   - **Impact**: Database access is more verbose
   - **Workaround**: Use SQLAlchemy ORM directly
   - **Fix Required**: Implement 7 repository classes

3. **No Database Migrations** (Alembic not set up)
   - **Impact**: Schema changes not version controlled
   - **Workaround**: Programmatic initialization only
   - **Fix Required**: Set up Alembic and create initial migration

### High Priority Issues

4. **Zero Storage Layer Tests** (0% coverage)
   - **Impact**: No confidence in database/Git operations
   - **Risk**: Bugs may exist in untested code
   - **Mitigation**: Test thoroughly as you use components

5. **Integration Test Failures** (2 config tests failing)
   - **Impact**: Edge case bugs in config system
   - **Workaround**: Known issues documented below
   - **Fix Required**: Fix secret masking and env fallback

### Known Bugs

**Config System**:
- Secret masking format: Uses '****' instead of '...' in summary
- Environment fallback: Returns None instead of env value in some cases

**Database System**:
- Untested: All database operations need validation
- No error handling examples: Unknown error scenarios

**Git System**:
- Untested: All Git operations need validation
- Unknown edge cases: Merge conflicts, large files, etc.

---

## Testing Strategy for Wave 2

### Test As You Integrate

1. **Unit Test Your Code** (Don't inherit low coverage):
   ```python
   # tests/unit/test_research_engine.py
   def test_research_engine_initialization():
       """Test that research engine initializes correctly."""
       config = ConfigManager.get_instance().get_config()
       engine = ResearchEngine(config)
       assert engine.config == config
       assert engine.db_manager is not None
   ```

2. **Integration Test Cross-Component Features**:
   ```python
   # tests/integration/test_document_workflow.py
   def test_save_and_retrieve_document():
       """Test full document save/retrieve workflow."""
       # Initialize system
       config = ConfigManager.get_instance().get_config()
       doc_store = DocumentStore(config)

       # Save document
       doc_id = doc_store.save_document(
           title="Test Doc",
           content="Test content",
           topic_name="Test"
       )

       # Retrieve document
       doc = doc_store.load_document(doc_id)
       assert doc.title == "Test Doc"

       # Verify Git commit
       git_mgr = GitManager(Path(config.research_dir))
       history = git_mgr.get_document_history(Path(doc.file_path))
       assert len(history) > 0
   ```

3. **Validate Wave 1 Components** Before Using:
   ```python
   def test_wave1_components():
       """Validate Wave 1 components work before relying on them."""
       # Test config
       config = ConfigManager.get_instance().get_config()
       validation = ConfigManager.get_instance().validate()
       assert validation["valid"]

       # Test database
       db_manager = DatabaseManager(config.database_path)
       db_manager.initialize()
       tables = db_manager.list_tables()
       assert "topics" in tables

       # Test Git
       git_mgr = GitManager(Path(config.research_dir))
       assert git_mgr.repo is not None
   ```

### Recommended Test Structure

```
tests/
├── unit/
│   ├── test_config.py          # ✅ Exists (Wave 1)
│   ├── test_research_engine.py # TODO: Wave 2
│   ├── test_search_client.py   # TODO: Wave 2
│   └── test_validators.py      # TODO: Wave 2
├── integration/
│   ├── test_document_workflow.py  # TODO: Wave 2
│   ├── test_research_workflow.py  # TODO: Wave 2
│   └── test_wave1_integration.py  # TODO: Validate Wave 1
└── e2e/
    └── test_full_research_cycle.py  # TODO: Wave 2
```

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer                         │
│  ⚠️ Incomplete: Only config commands exist          │
│  ❌ Missing: main.py, init, status, show, etc.     │
└─────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│              Research Logic Layer                    │
│  👉 Wave 2 will implement this                      │
│  - Research engines                                  │
│  - Search clients                                    │
│  - Validation logic                                  │
└─────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│               Storage Layer                          │
│  ✅ DocumentStore: High-level document API          │
│  ⚠️ Database: Models defined, no repos              │
│  ⚠️ Git: Implementation exists, untested            │
└─────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│              Configuration Layer                     │
│  ✅ ConfigManager: Fully tested (87% coverage)      │
│  ✅ SecureKeyManager: Working (69% coverage)        │
│  ✅ API Key Management: Keyring integration         │
└─────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (Wave 2)
    ▼
Research Engine (Wave 2)
    ▼
┌───────────────┬─────────────────┐
▼               ▼                 ▼
Search Clients  Validators      Deduplication
(Wave 2)        (Wave 2)        (Wave 2)
                                     ▼
                                DocumentStore
                                (Wave 1 - ready)
                                     ▼
                        ┌────────────┴────────────┐
                        ▼                         ▼
                   Database                    Git Repo
              (Wave 1 - use ORM)          (Wave 1 - test first)
```

### Module Dependencies

```
Wave 2 modules will depend on:

aris.core.config (✅ Ready)
    └── ConfigManager
    └── SecureKeyManager

aris.storage.database (⚠️ Use with caution)
    └── DatabaseManager
    └── get_session
    └── models.* (use directly, no repos)

aris.storage.git_manager (⚠️ Validate first)
    └── GitManager

aris.storage.document_store (⚠️ Test thoroughly)
    └── DocumentStore

aris.models.* (✅ Data models ready)
    └── ArisConfig
    └── Document
    └── ResearchSession
    └── etc.
```

---

## Code Examples for Common Tasks

### Example 1: Initialize ARIS System

```python
"""Initialize ARIS system for Wave 2 development."""

from pathlib import Path
from aris.core.config import ConfigManager
from aris.storage.database import DatabaseManager
from aris.storage.git_manager import GitManager
from aris.storage.document_store import DocumentStore

def initialize_aris():
    """Initialize all ARIS components."""
    print("Initializing ARIS system...")

    # 1. Load configuration
    print("  Loading configuration...")
    config_manager = ConfigManager.get_instance()
    config = config_manager.load()

    # 2. Validate configuration
    print("  Validating configuration...")
    validation = config_manager.validate()
    if not validation["valid"]:
        print(f"  ❌ Configuration errors: {validation['errors']}")
        return None
    print("  ✅ Configuration valid")

    # 3. Ensure directories exist
    config.project_root.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✅ Directories created")

    # 4. Initialize database
    print("  Initializing database...")
    db_manager = DatabaseManager(config.database_path)
    db_manager.initialize()
    tables = db_manager.list_tables()
    print(f"  ✅ Database initialized with {len(tables)} tables")

    # 5. Initialize Git
    print("  Initializing Git repository...")
    git_mgr = GitManager(Path(config.research_dir))
    print(f"  ✅ Git repository ready")

    # 6. Initialize document store
    print("  Initializing document store...")
    doc_store = DocumentStore(config)
    print(f"  ✅ Document store ready")

    print("✅ ARIS system initialized successfully")

    return {
        'config': config,
        'config_manager': config_manager,
        'db_manager': db_manager,
        'git_manager': git_mgr,
        'document_store': doc_store
    }

if __name__ == "__main__":
    components = initialize_aris()
    if components:
        print("\nComponents available:")
        for name, component in components.items():
            print(f"  - {name}: {type(component).__name__}")
```

### Example 2: Create Research Topic

```python
"""Create a new research topic with metadata."""

from aris.storage.database import get_session
from aris.storage.models import Topic
from datetime import datetime

def create_research_topic(db_manager, name: str, description: str):
    """Create a new research topic."""
    with get_session(db_manager) as session:
        # Check if topic exists
        existing = session.query(Topic).filter_by(name=name).first()
        if existing:
            print(f"Topic '{name}' already exists")
            return existing.id

        # Create new topic
        topic = Topic(
            name=name,
            description=description,
            created_at=datetime.utcnow()
        )
        session.add(topic)
        session.commit()

        print(f"✅ Created topic '{name}' with ID: {topic.id}")
        return topic.id

# Usage
if __name__ == "__main__":
    from aris.core.config import ConfigManager
    from aris.storage.database import DatabaseManager

    config = ConfigManager.get_instance().get_config()
    db_manager = DatabaseManager(config.database_path)

    topic_id = create_research_topic(
        db_manager,
        name="AI Safety",
        description="Research on ensuring AI systems are safe and beneficial"
    )
```

### Example 3: Save Document with Sources

```python
"""Save a research document with sources and metadata."""

from aris.storage.document_store import DocumentStore
from aris.core.config import ConfigManager

def save_research_document(
    doc_store: DocumentStore,
    title: str,
    content: str,
    topic_name: str,
    sources: list[str],
    metadata: dict
):
    """Save a research document with full tracking."""
    print(f"Saving document: {title}")

    # Save document (auto-commits to Git)
    doc_id = doc_store.save_document(
        title=title,
        content=content,
        topic_name=topic_name,
        sources=sources,
        metadata=metadata
    )

    print(f"✅ Document saved with ID: {doc_id}")
    print(f"   - Topic: {topic_name}")
    print(f"   - Sources: {len(sources)}")
    print(f"   - Git: Committed")

    return doc_id

# Usage
if __name__ == "__main__":
    config = ConfigManager.get_instance().get_config()
    doc_store = DocumentStore(config)

    doc_id = save_research_document(
        doc_store,
        title="AI Safety Research Summary",
        content="This document summarizes recent research on AI safety...",
        topic_name="AI Safety",
        sources=[
            "https://arxiv.org/abs/1234.5678",
            "https://example.com/ai-safety-paper"
        ],
        metadata={
            "author": "ARIS Wave 2",
            "confidence": 0.85,
            "research_session_id": "session-123"
        }
    )
```

---

## Technical Debt to Track

### Critical (Address Early in Wave 2)

1. **Create CLI Entry Point** (2 hours)
   - File: `src/aris/cli/main.py`
   - Requirements: Click command group, integrate config commands
   - Priority: HIGH - needed for CLI testing

2. **Implement Repository Classes** (4-6 hours)
   - Files: `src/aris/storage/repositories.py`
   - Requirements: 7 repository classes with CRUD operations
   - Priority: HIGH - better database abstraction

3. **Set Up Alembic Migrations** (2-3 hours)
   - Directory: `alembic/`
   - Requirements: Initialize Alembic, create initial migration
   - Priority: HIGH - schema version control

### High Priority (Address Mid-Wave 2)

4. **Add Storage Layer Tests** (6-8 hours)
   - Files: `tests/unit/test_database.py`, `tests/unit/test_git_manager.py`
   - Requirements: 80%+ coverage for storage layer
   - Priority: MEDIUM - validation needed

5. **Fix Config Integration Tests** (2 hours)
   - Fix: Secret masking format, env fallback
   - Priority: MEDIUM - known bugs

### Medium Priority (Can Wait)

6. **Implement Database CLI Commands** (3-4 hours)
   - File: `src/aris/cli/db_commands.py`
   - Commands: `aris db init`, `aris db status`, `aris db reset`

7. **Implement Git CLI Commands** (2-3 hours)
   - File: `src/aris/cli/git_commands.py`
   - Commands: `aris git status`, `aris git log`

---

## Success Criteria for Wave 2

### Must Achieve

1. **Core Research Functionality**:
   - ✅ Research engine implementation
   - ✅ Search client integration (Tavily)
   - ✅ Document deduplication working
   - ✅ Source validation implemented

2. **Integration with Wave 1**:
   - ✅ Uses ConfigManager for all settings
   - ✅ Stores documents in database
   - ✅ Commits documents to Git
   - ✅ No broken integrations

3. **Testing**:
   - ✅ Unit tests for research logic (80%+ coverage)
   - ✅ Integration tests for workflows
   - ✅ Validation tests for Wave 1 components

### Should Achieve

4. **Technical Debt Resolution**:
   - ✅ CLI entry point created
   - ✅ Basic CLI commands working
   - ✅ Repository pattern implemented

5. **Documentation**:
   - ✅ Wave 2 component documentation
   - ✅ Integration guide updated
   - ✅ Known issues tracked

### Nice to Have

6. **Enhanced Features**:
   - Alembic migrations set up
   - Full CLI interface
   - Comprehensive test suite
   - Performance optimization

---

## Support and Questions

### Where to Find Information

**Wave 1 Documentation**:
- `/mnt/projects/aris-tool/claudedocs/WAVE1-VALIDATION-REPORT.md` (This validation)
- `/mnt/projects/aris-tool/claudedocs/WAVE1-AGENT1-COMPLETE.md` (Config system details)
- `/mnt/projects/aris-tool/claudedocs/AGENT1-HANDOFF-CONFIGURATION.md` (Config API reference)

**Code Reference**:
- Configuration: `src/aris/core/config.py`, `src/aris/core/secrets.py`
- Database: `src/aris/storage/database.py`, `src/aris/storage/models.py`
- Git: `src/aris/storage/git_manager.py`, `src/aris/storage/document_store.py`
- Tests: `tests/unit/test_config.py` (examples of good test patterns)

**Configuration**:
- Template: `.env.example` (complete list of all config parameters)
- Setup: Follow instructions in `.env.example`

### Common Questions

**Q: Why don't repository classes exist?**
A: Agent 2 defined models but didn't implement repositories. Use SQLAlchemy ORM directly.

**Q: Can I use the CLI?**
A: No, main entry point is missing. Use Python APIs directly for now.

**Q: Is the database tested?**
A: No, 0% test coverage. Validate operations before extensive use.

**Q: Should I implement missing Wave 1 components?**
A: Only if they block Wave 2 work. Track as technical debt and implement minimal solutions.

**Q: How do I handle schema changes?**
A: Modify models.py and recreate database (dev only). Alembic setup is future work.

---

## Approval and Sign-Off

**Wave 1 Status**: ⚠️ CONDITIONAL APPROVAL
**Wave 2 Readiness**: ✅ APPROVED TO PROCEED
**Date**: 2025-11-12

**Approved By**: Quality Engineer (Wave 1, Agent 5)

**Approval Conditions**:
1. Wave 2 agents must use Python APIs (not CLI)
2. Database operations must be validated before extensive use
3. Technical debt must be tracked and addressed incrementally
4. Integration tests must be added as components are integrated

**Risk Level**: MEDIUM
- Config system: LOW RISK (well tested)
- Database system: MEDIUM RISK (untested but simple)
- Git system: MEDIUM RISK (untested but straightforward)
- CLI system: HIGH RISK (incomplete, use Python APIs instead)

**Recommendation**: Proceed with Wave 2 cautiously, test thoroughly, document issues as discovered.

---

**End of Wave 2 Handoff Package**
