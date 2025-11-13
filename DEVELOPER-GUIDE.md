# ARIS Developer Guide

**Version**: 1.0
**Date**: 2025-11-12
**Audience**: Contributors and Maintainers

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Testing Strategy](#testing-strategy)
6. [Code Standards](#code-standards)
7. [Key Components](#key-components)
8. [Extending ARIS](#extending-aris)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### High-Level Design

ARIS uses a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────┐
│         CLI Layer (Click)           │  User interface
├─────────────────────────────────────┤
│     Core Logic Layer                │  Business logic
│  - ResearchOrchestrator             │
│  - DeduplicationGate                │
│  - DocumentMerger                   │
│  - ReasoningEngine                  │
├─────────────────────────────────────┤
│     Storage Layer                   │  Persistence
│  - DocumentStore                    │
│  - DatabaseManager                  │
│  - GitManager                       │
│  - VectorStore                      │
├─────────────────────────────────────┤
│     MCP Integration Layer           │  External services
│  - TavilyClient                     │
│  - SequentialClient                 │
│  - SerenaClient                     │
└─────────────────────────────────────┘
```

### Design Principles

1. **Deduplication-First**: Primary goal is preventing document proliferation
2. **Local-First**: All data stored locally (privacy & security)
3. **Git as Truth**: Version control is authoritative source
4. **Multi-Model Validation**: Consensus-based quality assurance
5. **Cost-Conscious**: Track and optimize API costs
6. **Fail-Safe**: Graceful degradation when external services fail

---

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Poetry (dependency management)
- Git
- System keyring support

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd aris-tool

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Install pre-commit hooks (if configured)
pre-commit install

# Verify installation
python -m pytest tests/unit/

# Run ARIS
aris --help
```

### Environment Configuration

Create `.env` file:
```bash
# Required
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# Optional
OPENAI_API_KEY=your_key_here
ARIS_LOG_LEVEL=DEBUG
ARIS_DB_PATH=~/.aris/aris.db
```

---

## Project Structure

```
aris-tool/
├── src/aris/              # Main package
│   ├── cli/               # CLI commands (Click)
│   │   ├── main.py        # Entry point
│   │   ├── research_commands.py
│   │   ├── config_commands.py
│   │   └── ...
│   ├── core/              # Core business logic
│   │   ├── config.py      # Configuration management
│   │   ├── secrets.py     # Secure API key storage
│   │   ├── research_orchestrator.py  # Main research coordinator
│   │   ├── deduplication_gate.py     # Similarity detection
│   │   ├── document_merger.py        # Intelligent merging
│   │   ├── reasoning_engine.py       # Multi-model validation
│   │   └── ...
│   ├── storage/           # Persistence layer
│   │   ├── database.py    # SQLAlchemy database
│   │   ├── models.py      # ORM models
│   │   ├── document_store.py  # Document CRUD
│   │   ├── git_manager.py     # Git operations
│   │   ├── vector_store.py    # Semantic search
│   │   └── ...
│   ├── mcp/               # MCP client integrations
│   │   ├── tavily_client.py   # Web search
│   │   ├── sequential_client.py  # Reasoning
│   │   ├── serena_client.py      # Project memory
│   │   └── ...
│   ├── models/            # Pydantic data models
│   │   ├── document.py    # Document schemas
│   │   ├── research.py    # Research models
│   │   └── ...
│   └── utils/             # Utilities
│       ├── output.py      # Rich formatting
│       └── ...
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── docs/                  # Requirements & specs
├── claudedocs/            # Architecture docs
├── pyproject.toml         # Poetry config
└── README.md
```

---

## Development Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Critical production fixes

### Making Changes

1. **Create Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Develop**
   - Write code following standards (see Code Standards section)
   - Add tests for new functionality
   - Update documentation

3. **Test**
   ```bash
   # Run unit tests
   pytest tests/unit/

   # Run integration tests
   pytest tests/integration/

   # Run specific test file
   pytest tests/unit/test_deduplication_gate.py

   # Run with coverage
   pytest --cov=src/aris --cov-report=html
   ```

4. **Code Quality**
   ```bash
   # Format code (if Black is configured)
   black src/ tests/

   # Lint (if Ruff is configured)
   ruff check src/ tests/

   # Type check (if mypy is configured)
   mypy src/
   ```

5. **Commit**
   ```bash
   git add .
   git commit -m "feat: Add new feature with tests"
   ```

   Use [conventional commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Test additions
   - `refactor:` Code restructuring
   - `perf:` Performance improvement
   - `chore:` Maintenance

6. **Push & Pull Request**
   ```bash
   git push origin feature/new-feature
   ```
   Then create PR on GitHub/GitLab.

---

## Testing Strategy

### Test Levels

#### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Mock external dependencies
- Fast execution (<1s each)
- High coverage (aim for >80%)

**Example**:
```python
# tests/unit/test_deduplication_gate.py
def test_similarity_calculation():
    gate = DeduplicationGate(...)
    score = gate._calculate_similarity(doc1, doc2)
    assert 0.0 <= score <= 1.0
```

#### Integration Tests (`tests/integration/`)
- Test component interactions
- Use real database (test instance)
- May use mocked MCP clients
- Moderate execution time

**Example**:
```python
# tests/integration/test_document_store.py
def test_create_and_retrieve_document(db_session):
    store = DocumentStore(db_session)
    doc = store.create_document(...)
    retrieved = store.get_document(doc.id)
    assert retrieved.content == doc.content
```

#### End-to-End Tests (`tests/e2e/`)
- Test complete workflows
- Use real or mocked external services
- Slower execution
- Verify user-facing functionality

**Example**:
```python
# tests/e2e/test_complete_workflow.py
def test_research_workflow_with_deduplication():
    # Run first research
    result1 = run_research("topic A")
    assert result1.action == "CREATE"

    # Run similar research
    result2 = run_research("topic A (similar)")
    assert result2.action == "UPDATE"
```

### Running Tests

```bash
# All tests
pytest

# Specific test type
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Specific test file
pytest tests/unit/test_deduplication_gate.py

# Specific test function
pytest tests/unit/test_deduplication_gate.py::test_similarity_calculation

# With coverage
pytest --cov=src/aris --cov-report=html
# View report: open htmlcov/index.html

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Writing Tests

**Test Structure**:
```python
import pytest
from aris.core.deduplication_gate import DeduplicationGate

class TestDeduplicationGate:
    """Test suite for DeduplicationGate component."""

    @pytest.fixture
    def gate(self):
        """Create gate instance for testing."""
        return DeduplicationGate(
            update_threshold=0.85,
            merge_threshold=0.70
        )

    def test_create_decision_for_low_similarity(self, gate):
        """Should return CREATE when similarity is low."""
        # Arrange
        doc1 = create_test_document(topic="AI")
        doc2 = create_test_document(topic="Databases")

        # Act
        result = gate.check_before_write(doc1, [doc2])

        # Assert
        assert result.action == DeduplicationAction.CREATE
        assert result.confidence > 0.9
```

**Best Practices**:
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- One assertion per test (when possible)
- Use fixtures for common setup
- Mock external dependencies
- Test edge cases and error conditions

---

## Code Standards

### Python Style

Follow [PEP 8](https://pep8.org/) with these specifics:
- Line length: 100 characters
- Indentation: 4 spaces
- Imports: Grouped and sorted
- Type hints: Required for all functions
- Docstrings: Google style for public APIs

### Type Hints

```python
from typing import List, Dict, Optional

def calculate_similarity(
    doc1: Document,
    doc2: Document,
    threshold: float = 0.85
) -> float:
    """Calculate semantic similarity between documents.

    Args:
        doc1: First document
        doc2: Second document
        threshold: Minimum similarity threshold

    Returns:
        Similarity score between 0.0 and 1.0

    Raises:
        ValueError: If threshold is not in [0, 1]
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
class DeduplicationGate:
    """Determines whether to create new document or update existing.

    The gate analyzes semantic similarity using multiple criteria:
    - Topic overlap (40% weight)
    - Content similarity (40% weight)
    - Question overlap (20% weight)

    Attributes:
        update_threshold: Similarity score for UPDATE decision (default 0.85)
        merge_threshold: Similarity score for MERGE decision (default 0.70)

    Example:
        >>> gate = DeduplicationGate()
        >>> result = gate.check_before_write(document, existing_documents)
        >>> if result.action == DeduplicationAction.UPDATE:
        ...     # Update existing document
    """
```

### Error Handling

```python
# Custom exceptions
class ARISError(Exception):
    """Base exception for ARIS errors."""

class DeduplicationError(ARISError):
    """Error in deduplication logic."""

# Usage
def check_before_write(self, ...):
    try:
        # Logic here
        pass
    except DatabaseError as e:
        logger.error(f"Database error during deduplication: {e}")
        raise DeduplicationError(f"Failed to check for duplicates: {e}") from e
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_document(doc: Document) -> None:
    logger.debug(f"Processing document: {doc.id}")
    try:
        # Process
        logger.info(f"Document {doc.id} processed successfully")
    except Exception as e:
        logger.error(f"Failed to process document {doc.id}: {e}")
        raise
```

Log levels:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General information (normal operation)
- `WARNING`: Something unexpected but handled
- `ERROR`: Error that prevented operation
- `CRITICAL`: System-level failure

---

## Key Components

### 1. Research Orchestrator

**Location**: `src/aris/core/research_orchestrator.py`

**Purpose**: Coordinates the entire research workflow

**Key Methods**:
- `execute_research(query)`: Main entry point
- `_gather_information()`: Collect data via MCP clients
- `_validate_findings()`: Multi-model validation
- `_save_research_document()`: Save with deduplication

**Extending**:
```python
class CustomOrchestrator(ResearchOrchestrator):
    def _gather_information(self, query: str) -> ResearchData:
        # Custom information gathering
        data = super()._gather_information(query)
        # Add custom processing
        return data
```

---

### 2. Deduplication Gate

**Location**: `src/aris/core/deduplication_gate.py`

**Purpose**: Detect document similarity and decide action

**Key Methods**:
- `check_before_write()`: Main deduplication check
- `_calculate_similarity()`: Compute similarity score
- `_find_similar_documents()`: Search for matches

**Algorithm**:
```python
similarity = (
    0.4 * topic_overlap +
    0.4 * content_similarity +
    0.2 * question_overlap
)

if similarity >= 0.85:
    action = UPDATE
elif similarity >= 0.70:
    action = MERGE
else:
    action = CREATE
```

**Customizing Thresholds**:
```python
gate = DeduplicationGate(
    update_threshold=0.90,  # More strict
    merge_threshold=0.75    # Less aggressive
)
```

---

### 3. Document Merger

**Location**: `src/aris/core/document_merger.py`

**Purpose**: Intelligently consolidate documents

**Merge Strategies**:
- `APPEND`: Add new content at end
- `INTEGRATE`: Merge section by section (default)
- `REPLACE`: Overwrite existing content

**Key Methods**:
- `merge_documents()`: Main merge function
- `detect_conflicts()`: Find inconsistencies
- `resolve_conflict()`: Handle conflicts
- `get_merge_report()`: Generate report

**Conflict Types**:
- `METADATA`: Confidence/purpose divergence
- `CONTENT`: Contradictory claims
- `STRUCTURAL`: Topic/structure mismatch
- `CONFIDENCE`: Quality degradation

---

### 4. Vector Store

**Location**: `src/aris/storage/vector_store.py`

**Purpose**: Semantic similarity search

**Key Methods**:
- `add_document()`: Index document
- `search_similar()`: Find similar documents
- `update_embedding()`: Refresh embeddings

**Technology**: Uses sentence transformers for embeddings

---

### 5. MCP Clients

#### Tavily Client (`src/aris/mcp/tavily_client.py`)
- Web search integration
- Source extraction
- Cost tracking

#### Sequential Client (`src/aris/mcp/sequential_client.py`)
- Multi-step reasoning
- Hypothesis validation
- Structured analysis

#### Serena Client (`src/aris/mcp/serena_client.py`)
- Project memory
- Session persistence
- Context retrieval

---

## Extending ARIS

### Adding New CLI Command

1. **Create Command File**:
   ```python
   # src/aris/cli/my_commands.py
   import click

   @click.group()
   def my_group():
       """My custom commands."""
       pass

   @my_group.command()
   @click.argument("input")
   def my_command(input: str):
       """Do something custom."""
       # Implementation
       click.echo(f"Processing: {input}")
   ```

2. **Register in Main**:
   ```python
   # src/aris/cli/main.py
   from .my_commands import my_group

   cli.add_command(my_group, name="my")
   ```

3. **Test**:
   ```bash
   aris my my-command "test input"
   ```

---

### Adding New Merge Strategy

1. **Add to Enum**:
   ```python
   # src/aris/core/document_merger.py
   class MergeStrategy(Enum):
       APPEND = "append"
       INTEGRATE = "integrate"
       REPLACE = "replace"
       CUSTOM = "custom"  # New strategy
   ```

2. **Implement Logic**:
   ```python
   def _merge_custom(self, existing: str, new: str) -> str:
       """Custom merge strategy implementation."""
       # Your logic here
       return merged_content

   def merge_documents(self, ...):
       if strategy == MergeStrategy.CUSTOM:
           merged_content = self._merge_custom(existing_content, new_content)
       # ...
   ```

3. **Test**:
   ```python
   # tests/unit/test_document_merger.py
   def test_custom_merge_strategy():
       merger = DocumentMerger()
       result = merger.merge_documents(
           existing, new_content, new_metadata,
           strategy=MergeStrategy.CUSTOM
       )
       # Assertions
   ```

---

### Adding New MCP Client

1. **Create Client Class**:
   ```python
   # src/aris/mcp/new_client.py
   from .base_client import BaseMCPClient

   class NewClient(BaseMCPClient):
       """Client for new MCP service."""

       def __init__(self, api_key: str):
           super().__init__(api_key)
           self.service_url = "https://api.newservice.com"

       async def query(self, request: str) -> dict:
           """Query the new service."""
           # Implementation
           pass
   ```

2. **Integrate in Orchestrator**:
   ```python
   # src/aris/core/research_orchestrator.py
   from aris.mcp.new_client import NewClient

   class ResearchOrchestrator:
       def __init__(self, config: ArisConfig):
           # ...
           self.new_client = NewClient(config.new_api_key)
   ```

3. **Add Configuration**:
   ```python
   # src/aris/models/config.py
   class ArisConfig(BaseSettings):
       # ...
       new_api_key: str = Field(default="", env="NEW_API_KEY")
   ```

---

## Troubleshooting

### Common Development Issues

#### Issue: Tests Fail with "Database locked"
**Solution**: Ensure test database is separate:
```python
@pytest.fixture
def test_db():
    """Create isolated test database."""
    db_path = "/tmp/test_aris.db"
    yield db_path
    os.remove(db_path)
```

#### Issue: Import Errors
**Solution**: Ensure package is installed in editable mode:
```bash
poetry install
# or
pip install -e .
```

#### Issue: Type Checking Fails
**Solution**: Update type stubs:
```bash
pip install types-requests types-pyyaml
mypy src/
```

#### Issue: Coverage Not Measured
**Solution**: Install pytest-cov:
```bash
poetry add --dev pytest-cov
pytest --cov=src/aris
```

---

### Debugging

#### Enable Debug Logging
```bash
export ARIS_LOG_LEVEL=DEBUG
aris research "topic" --verbose
```

#### Use Python Debugger
```python
import pdb; pdb.set_trace()  # Breakpoint
```

#### Test Specific Scenario
```python
# Create minimal test case
def test_specific_bug():
    # Reproduce bug
    # Add assertions
    pass
```

---

## Contributing

### Pull Request Checklist
- [ ] Code follows project style
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] Reviewed by at least one other developer

### Code Review Guidelines
- Check for logic errors
- Verify test coverage
- Ensure documentation is clear
- Look for performance issues
- Verify error handling
- Check for security issues

---

## Resources

### Internal Documentation
- `docs/MVP-Requirements-Specification.md` - Requirements
- `docs/ARIS-Architecture-Blueprint.md` - Architecture
- `claudedocs/` - Technical specifications

### External Resources
- [Click Documentation](https://click.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)

---

## Next Steps

1. **Set up your development environment**
2. **Run the test suite** to verify setup
3. **Explore the codebase** starting with `ResearchOrchestrator`
4. **Pick a task** from the issue tracker
5. **Make your first contribution**

For questions, reach out to the team or check the documentation.

---

**End of Developer Guide**
