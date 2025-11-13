# WAVE 1 ISSUES AND TECHNICAL DEBT

**Date**: 2025-11-12
**Status**: Active tracking document
**Last Updated**: Wave 1 completion

---

## Critical Issues (Blocking)

### 🚨 ISSUE-001: Missing CLI Entry Point

**Status**: OPEN - CRITICAL
**Component**: CLI Layer
**Impact**: Application cannot be executed via `aris` command

**Description**:
The `pyproject.toml` file references `aris.cli.main:cli` as the entry point, but the file `src/aris/cli/main.py` does not exist.

**Current State**:
- `pyproject.toml` line 26: `aris = "aris.cli.main:cli"`
- File missing: `src/aris/cli/main.py`
- Only config commands exist: `src/aris/cli/config_commands.py`

**Impact**:
- `aris` command will fail with import error
- Cannot execute any CLI commands
- CLI testing is impossible
- User experience severely degraded

**Workaround**:
Use Python APIs directly:
```python
from aris.core.config import ConfigManager
from aris.storage.database import DatabaseManager
# etc.
```

**Fix Required**:
Create `src/aris/cli/main.py` with:
```python
import click
from aris.cli.config_commands import config_group

@click.group()
@click.version_option(version="0.1.0", prog_name="aris")
def cli():
    """ARIS - Autonomous Research Intelligence System"""
    pass

cli.add_command(config_group)

if __name__ == "__main__":
    cli()
```

**Estimate**: 2 hours (including testing)
**Priority**: P0 - CRITICAL
**Assigned To**: Next available agent or technical debt cleanup

---

### 🚨 ISSUE-002: Missing Repository Implementations

**Status**: OPEN - HIGH PRIORITY
**Component**: Database Layer
**Impact**: Database abstraction layer incomplete

**Description**:
`storage/__init__.py` references 7 repository classes that don't exist:
- TopicRepository
- DocumentRepository
- SourceRepository
- RelationshipRepository
- ResearchSessionRepository
- ResearchHopRepository
- ConflictRepository

**Current State**:
- File: `src/aris/storage/__init__.py` lines 24-32
- Imports reference non-existent module: `aris.storage.repositories`
- Will cause ImportError if anyone tries to use repositories

**Impact**:
- Cannot use repository pattern for database operations
- Must use SQLAlchemy ORM directly (more verbose)
- Less abstraction and code reusability
- Harder to maintain and test

**Workaround**:
Use SQLAlchemy ORM directly:
```python
from aris.storage.models import Topic
from aris.storage.database import get_session

with get_session(db_manager) as session:
    topic = session.query(Topic).filter_by(name="AI").first()
```

**Fix Required**:
Create `src/aris/storage/repositories.py` with repository classes:
```python
class TopicRepository:
    def __init__(self, session):
        self.session = session

    def get_by_id(self, topic_id: str) -> Optional[Topic]:
        return self.session.query(Topic).filter_by(id=topic_id).first()

    def get_by_name(self, name: str) -> Optional[Topic]:
        return self.session.query(Topic).filter_by(name=name).first()

    def create(self, name: str, description: str) -> Topic:
        topic = Topic(name=name, description=description)
        self.session.add(topic)
        self.session.commit()
        return topic

    # ... etc for all CRUD operations
```

**Estimate**: 4-6 hours (all 7 repositories)
**Priority**: P1 - HIGH
**Assigned To**: Next available agent or Wave 2 Agent 1

---

### 🚨 ISSUE-003: No Alembic Migrations

**Status**: OPEN - HIGH PRIORITY
**Component**: Database Layer
**Impact**: Database schema not version controlled

**Description**:
No Alembic migration setup exists. Database schema is created programmatically only, which makes schema evolution difficult.

**Current State**:
- No `alembic/` directory
- No `alembic.ini` file
- No migration files
- Schema created via `DatabaseManager.initialize()`

**Impact**:
- Cannot version control schema changes
- Cannot migrate databases between versions
- Production deployments risky
- Rollbacks impossible

**Workaround**:
For development, recreate database on schema changes:
```python
db_manager.drop_all_tables()
db_manager.initialize()
```

**Fix Required**:
1. Install Alembic: `pip install alembic`
2. Initialize Alembic: `alembic init alembic`
3. Configure `alembic.ini` to use ARIS database
4. Create initial migration from current models
5. Update `DatabaseManager` to use migrations

**Estimate**: 2-3 hours (setup and initial migration)
**Priority**: P1 - HIGH
**Assigned To**: Database expert or Wave 2 Agent 1

---

## High Priority Issues

### ⚠️ ISSUE-004: Zero Storage Layer Test Coverage

**Status**: OPEN - HIGH PRIORITY
**Component**: Storage Layer (Database + Git)
**Impact**: No confidence in storage operations

**Description**:
Storage layer has 0% test coverage:
- `src/aris/storage/database.py`: 0% (78 lines untested)
- `src/aris/storage/git_manager.py`: 0% (140 lines untested)
- `src/aris/storage/models.py`: 0% (139 lines untested)
- `src/aris/storage/document_store.py`: 0% (untested)

**Current State**:
- No `tests/unit/test_database.py`
- No `tests/unit/test_git_manager.py`
- No `tests/unit/test_models.py`
- No `tests/unit/test_document_store.py`

**Impact**:
- Unknown bugs in storage layer
- No validation that operations work
- Risk of data loss or corruption
- Difficult to refactor safely

**Workaround**:
Manual testing and validation:
```python
# Test each operation before extensive use
def validate_storage_layer():
    # Test database
    db_manager = DatabaseManager(path)
    db_manager.initialize()
    tables = db_manager.list_tables()
    assert len(tables) == 8

    # Test Git
    git_mgr = GitManager(path)
    commit = git_mgr.commit_document(...)
    assert commit is not None
```

**Fix Required**:
Create comprehensive test files:
- `tests/unit/test_database.py` (20+ tests)
- `tests/unit/test_git_manager.py` (15+ tests)
- `tests/unit/test_models.py` (10+ tests)
- `tests/unit/test_document_store.py` (15+ tests)

**Estimate**: 6-8 hours (all test files)
**Priority**: P1 - HIGH
**Assigned To**: Quality Engineer or Wave 2 testing phase

---

### ⚠️ ISSUE-005: Config Integration Test Failures

**Status**: OPEN - MEDIUM PRIORITY
**Component**: Configuration System
**Impact**: Edge case bugs in config system

**Description**:
2 integration tests failing in `tests/unit/test_config.py`:
1. `test_end_to_end_configuration_flow`: Secret masking format mismatch
2. `test_keyring_fallback_to_env`: Environment variable loading returns None

**Test Output**:
```
FAILED tests/unit/test_config.py::TestConfigurationIntegration::test_end_to_end_configuration_flow
  AssertionError: assert '...' in '****'

FAILED tests/unit/test_config.py::TestConfigurationIntegration::test_keyring_fallback_to_env
  AssertionError: assert None == 'env_key_123'
```

**Current State**:
- 28 of 30 tests passing (93%)
- 2 integration tests failing
- Core functionality works but edge cases have bugs

**Impact**:
- Secret masking inconsistency (cosmetic)
- Environment fallback may not work properly (functional)
- Config system not fully reliable

**Workaround**:
- Use keyring for API keys (don't rely on env fallback)
- Accept '****' as masking format instead of '...'

**Fix Required**:
1. Fix secret masking in `src/aris/core/config.py`:
   ```python
   # Change masking format to match test expectation
   masked = f"{value[:2]}...{value[-2:]}" if len(value) > 6 else "..."
   ```

2. Fix env fallback in `src/aris/core/config.py`:
   ```python
   # Ensure environment variables are checked when keyring empty
   key = self.key_manager.get(provider)
   if not key:
       key = os.getenv(f"ARIS_{provider.upper()}_API_KEY")
   return key
   ```

**Estimate**: 2 hours (fix and verify tests)
**Priority**: P2 - MEDIUM
**Assigned To**: Config system maintainer

---

## Medium Priority Issues

### 📋 ISSUE-006: Missing Database CLI Commands

**Status**: OPEN - MEDIUM PRIORITY
**Component**: CLI Layer
**Impact**: Cannot manage database via CLI

**Description**:
No database management commands exist. Users cannot initialize, inspect, or manage the database via CLI.

**Missing Commands**:
- `aris db init` - Initialize database schema
- `aris db status` - Show database status and statistics
- `aris db reset` - Reset database (dev only)
- `aris db migrate` - Run migrations (when Alembic setup)
- `aris db backup` - Backup database

**Current State**:
- No `src/aris/cli/db_commands.py`
- Database operations only via Python API

**Impact**:
- Poor user experience
- No database observability
- Difficult for non-programmers to use

**Workaround**:
Use Python API:
```python
from aris.storage.database import DatabaseManager
db = DatabaseManager(path)
db.initialize()
```

Or use SQLite directly:
```bash
sqlite3 ~/.aris/aris.db ".tables"
```

**Fix Required**:
Create `src/aris/cli/db_commands.py`:
```python
@click.group()
def db():
    """Database management commands."""
    pass

@db.command()
def init():
    """Initialize database schema."""
    # Implementation

@db.command()
def status():
    """Show database status."""
    # Implementation
```

**Estimate**: 3-4 hours
**Priority**: P2 - MEDIUM
**Assigned To**: CLI implementation phase

---

### 📋 ISSUE-007: Missing Git CLI Commands

**Status**: OPEN - MEDIUM PRIORITY
**Component**: CLI Layer
**Impact**: Cannot view Git history via CLI

**Description**:
No Git commands exist. Users cannot view document history or Git status via CLI.

**Missing Commands**:
- `aris git status` - Show repository status
- `aris git log [file]` - Show document history
- `aris git diff [file]` - Show document changes
- `aris git show [commit]` - Show commit details

**Current State**:
- No `src/aris/cli/git_commands.py`
- Git operations only via Python API

**Impact**:
- Cannot view document history easily
- No visibility into version control
- Must use git commands directly

**Workaround**:
Use Python API:
```python
from aris.storage.git_manager import GitManager
git = GitManager(path)
history = git.get_document_history(file_path)
```

Or use git directly:
```bash
cd ~/.aris/research
git log
```

**Fix Required**:
Create `src/aris/cli/git_commands.py`:
```python
@click.group()
def git():
    """Git version control commands."""
    pass

@git.command()
def status():
    """Show repository status."""
    # Implementation

@git.command()
@click.argument('file', required=False)
def log(file):
    """Show document history."""
    # Implementation
```

**Estimate**: 2-3 hours
**Priority**: P2 - MEDIUM
**Assigned To**: CLI implementation phase

---

### 📋 ISSUE-008: Missing Core CLI Commands

**Status**: OPEN - MEDIUM PRIORITY
**Component**: CLI Layer
**Impact**: Essential commands don't exist

**Description**:
Core ARIS commands referenced in requirements don't exist:
- `aris init` - Initialize new project/research session
- `aris status` - Show system status
- `aris show [doc]` - Display document
- `aris search [query]` - Search documents (Wave 2)
- `aris research [topic]` - Start research (Wave 2)

**Current State**:
- Only `aris config *` commands exist
- No `src/aris/cli/init_commands.py`
- No `src/aris/cli/status_commands.py`
- No `src/aris/cli/show_commands.py`

**Impact**:
- Cannot use ARIS via CLI
- Must use Python API for everything
- Poor user experience

**Workaround**:
Use Python APIs directly (as documented in handoff package)

**Fix Required**:
Create command modules:
- `src/aris/cli/init_commands.py`
- `src/aris/cli/status_commands.py`
- `src/aris/cli/show_commands.py`

Integrate into main CLI after main.py is created.

**Estimate**: 4-6 hours (all core commands)
**Priority**: P2 - MEDIUM (after main.py exists)
**Assigned To**: CLI implementation phase

---

## Low Priority / Future Enhancements

### 💡 ISSUE-009: No Code Quality Checks Run

**Status**: OPEN - LOW PRIORITY
**Component**: Build/CI
**Impact**: Code quality not validated

**Description**:
Code quality tools configured but not run:
- Black (formatting)
- Ruff (linting)
- MyPy (type checking)
- Bandit (security scanning)

**Fix**: Run as part of CI/CD or pre-commit hooks

**Estimate**: 2 hours (setup)
**Priority**: P3 - LOW

---

### 💡 ISSUE-010: Low Overall Test Coverage

**Status**: OPEN - LOW PRIORITY
**Component**: Testing
**Impact**: 36% overall coverage (target: 80%)

**Description**:
Overall test coverage is 36% (697 of 1,085 lines untested):
- Config layer: 87% ✅
- Storage layer: 0% ❌
- CLI layer: 0% ❌

**Fix**: Add tests incrementally as components are used

**Estimate**: Ongoing
**Priority**: P3 - LOW (address incrementally)

---

### 💡 ISSUE-011: Missing API Key Testing

**Status**: OPEN - LOW PRIORITY
**Component**: Configuration
**Impact**: Cannot validate API keys work

**Description**:
`aris config test-keys` command exists but is placeholder only. Cannot validate that API keys actually work.

**Fix**: Implement in Wave 2 when API clients are available

**Estimate**: 3-4 hours (requires API clients)
**Priority**: P3 - LOW

---

## Issue Metrics

### By Priority
- P0 CRITICAL: 1 issue (CLI entry point)
- P1 HIGH: 4 issues (repos, migrations, tests, config bugs)
- P2 MEDIUM: 4 issues (CLI commands)
- P3 LOW: 3 issues (quality, coverage, testing)

### By Component
- CLI Layer: 5 issues (1 critical, 4 medium)
- Database Layer: 3 issues (2 high, 1 medium)
- Configuration: 1 issue (medium)
- Testing: 2 issues (1 high, 1 low)
- Build/Quality: 1 issue (low)

### Impact Assessment
- **Critical (P0)**: 1 issue - blocks CLI usage
- **High (P1)**: 4 issues - limits functionality
- **Medium (P2)**: 4 issues - degrades UX
- **Low (P3)**: 3 issues - nice to have

---

## Resolution Plan

### Phase 1: Critical Issues (Before Wave 2 starts)

**Target**: 1-2 hours
**Goal**: Unblock Wave 2 development

1. Create minimal `src/aris/cli/main.py` (1 hour)
2. Fix config integration tests (1 hour)

### Phase 2: High Priority (Early Wave 2)

**Target**: 8-12 hours
**Goal**: Improve database layer reliability

1. Implement repository classes (4-6 hours)
2. Set up Alembic migrations (2-3 hours)
3. Add basic storage layer tests (4-6 hours)

### Phase 3: Medium Priority (Mid-Late Wave 2)

**Target**: 8-12 hours
**Goal**: Complete CLI interface

1. Implement database CLI commands (3-4 hours)
2. Implement Git CLI commands (2-3 hours)
3. Implement core CLI commands (4-6 hours)

### Phase 4: Low Priority (Post-Wave 2)

**Target**: Ongoing
**Goal**: Improve quality and coverage

1. Set up code quality checks (2 hours)
2. Improve test coverage incrementally
3. Implement API key testing (3-4 hours)

---

## Tracking and Updates

This document should be updated:
- When issues are resolved (mark CLOSED, add resolution date)
- When new issues are discovered (add new entries)
- When priorities change (update priority levels)
- Weekly during Wave 2 (review and adjust)

**Last Updated**: 2025-11-12 (Wave 1 completion)
**Next Review**: Wave 2 Agent 1 completion

---

## Issue Template

For adding new issues:

```markdown
### 🚨/⚠️/📋/💡 ISSUE-XXX: Title

**Status**: OPEN/IN_PROGRESS/RESOLVED/CLOSED
**Component**: Component name
**Impact**: One-line impact statement

**Description**:
Detailed description of the issue

**Current State**:
What exists now

**Impact**:
What this affects

**Workaround**:
How to work around it

**Fix Required**:
What needs to be done

**Estimate**: X hours
**Priority**: P0-P3
**Assigned To**: Person or phase
```

---

**End of Issues Tracking Document**
