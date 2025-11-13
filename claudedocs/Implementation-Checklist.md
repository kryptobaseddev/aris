# ARIS Implementation Checklist

Generated: 2025-11-12
Blueprint Version: 1.0.0

---

## Quick Reference: Module Dependencies

**Dependency Tree** (Build in this order):

```
Level 1 (No dependencies):
├── models/* (data structures)
├── utils/* (utilities)
└── config.yaml

Level 2 (Depends on Level 1):
├── core/state_manager.py
└── integrations/mcp_client.py

Level 3 (Depends on Level 2):
├── core/consensus.py
├── knowledge/vector_store.py
├── knowledge/graph_db.py
└── output/renderer.py

Level 4 (Depends on Level 3):
├── agents/base.py
├── integrations/*_client.py (specific clients)
└── integrations/a2a_protocol.py

Level 5 (Depends on Level 4):
├── agents/coordinator.py
├── agents/researcher.py
├── agents/validator.py
├── agents/synthesizer.py
├── agents/challenger.py
└── agents/archivist.py

Level 6 (Depends on Level 5):
├── core/task_queue.py
└── core/orchestrator.py

Level 7 (Depends on Level 6):
└── cli.py
```

---

## Phase 1: Core Foundation

### Setup (Week 1, Day 1-2)

- [ ] **Project initialization**
  ```bash
  poetry init
  poetry add click rich pydantic asyncio aiosqlite sqlalchemy alembic
  poetry add --group dev pytest pytest-asyncio black ruff mypy
  ```

- [ ] **Directory structure**
  ```bash
  mkdir -p aris/{core,agents,integrations,knowledge,output,models,utils}
  mkdir -p tests/{unit,integration,fixtures}
  mkdir -p migrations/versions
  mkdir -p data/{cache,logs}
  mkdir -p docs/examples
  touch aris/__init__.py  # Create all __init__.py files
  ```

- [ ] **Configuration files**
  - [ ] `pyproject.toml` with dependencies
  - [ ] `config.yaml` with defaults
  - [ ] `.env.example` for API keys
  - [ ] `.gitignore` (exclude data/, .env)

### Data Models (Week 1, Day 3-5)

**Priority Order**: Build these first as everything depends on them

- [ ] **aris/models/topic.py**
  ```python
  from pydantic import BaseModel, Field
  from uuid import UUID, uuid4
  from datetime import datetime
  from enum import Enum

  class TopicState(str, Enum):
      DRAFT = "draft"
      RESEARCHING = "researching"
      VALIDATING = "validating"
      SYNTHESIZING = "synthesizing"
      REVIEWED = "reviewed"
      PUBLISHED = "published"

  class Topic(BaseModel):
      id: UUID = Field(default_factory=uuid4)
      title: str
      query_embedding: Optional[List[float]] = None
      created_at: datetime = Field(default_factory=datetime.utcnow)
      updated_at: datetime = Field(default_factory=datetime.utcnow)
      state: TopicState = TopicState.DRAFT
      confidence: float = Field(ge=0.0, le=1.0, default=0.0)
      version: int = 1
      document_path: str
      metadata: Dict[str, Any] = Field(default_factory=dict)
  ```

- [ ] **aris/models/claim.py**
  - [ ] `Claim` model with validation
  - [ ] `ClaimType` enum
  - [ ] Confidence bounds (0.0-1.0)

- [ ] **aris/models/source.py**
  - [ ] `Source` model
  - [ ] `SourceType` enum
  - [ ] Authority scoring field

- [ ] **aris/models/task.py**
  - [ ] `Task` model
  - [ ] `TaskStatus` enum
  - [ ] `TaskDependency` model

- [ ] **aris/models/message.py**
  - [ ] `A2AMessage` model
  - [ ] Serialization methods (to_json, from_json)

### State Manager (Week 2, Day 1-3)

- [ ] **aris/core/state_manager.py**
  - [ ] SQLAlchemy ORM models
  - [ ] Database initialization
  - [ ] CRUD operations for all entities
  - [ ] Transaction context manager
  - [ ] Checkpoint/restore methods

- [ ] **Alembic migrations**
  ```bash
  poetry run alembic init migrations
  poetry run alembic revision --autogenerate -m "initial_schema"
  poetry run alembic upgrade head
  ```

- [ ] **Tests**: `tests/unit/test_state_manager.py`
  - [ ] Test topic CRUD
  - [ ] Test transaction rollback
  - [ ] Test cascade deletes

### Basic CLI (Week 2, Day 4-5)

- [ ] **aris/cli.py**
  ```python
  import click
  from rich.console import Console

  @click.group()
  def cli():
      """ARIS - Autonomous Research Intelligence System"""
      pass

  @cli.command()
  @click.option('--name', required=True)
  def init(name: str):
      """Initialize new research project"""
      # Create database, config
      pass

  @cli.command()
  def status():
      """Show system status"""
      # Display topics, tasks, stats
      pass
  ```

- [ ] **Commands to implement**:
  - [ ] `aris init --name <project>`
  - [ ] `aris status`
  - [ ] `aris config set <key> <value>`
  - [ ] `aris config get <key>`

- [ ] **Rich output formatting**
  - [ ] Tables for status display
  - [ ] Progress bars
  - [ ] Syntax highlighting

**Phase 1 Validation**:
```bash
poetry run aris init --name test-project
poetry run aris status
# Should show empty project with database initialized
```

---

## Phase 2: Single-Agent Pipeline

### Coordinator Agent (Week 3, Day 1-2)

- [ ] **aris/agents/base.py**
  ```python
  class BaseAgent(ABC):
      def __init__(self, state_manager: StateManager):
          self.state_manager = state_manager
          self.logger = logging.getLogger(self.__class__.__name__)

      @abstractmethod
      async def execute_task(self, task: Task) -> TaskResult:
          pass
  ```

- [ ] **aris/agents/coordinator.py**
  - [ ] Query parsing logic
  - [ ] Semantic deduplication (vector search)
  - [ ] Query decomposition (via LLM)
  - [ ] Mode selection (CREATE vs UPDATE)

- [ ] **Tests**: `tests/unit/test_coordinator.py`
  - [ ] Test query decomposition
  - [ ] Test semantic similarity matching

### Researcher Agent (Week 3, Day 3-5)

- [ ] **aris/integrations/tavily_client.py**
  - [ ] Tavily API wrapper
  - [ ] Error handling
  - [ ] Rate limiting

- [ ] **aris/agents/researcher.py**
  - [ ] Execute web searches
  - [ ] Extract findings
  - [ ] Store sources in database
  - [ ] Authority scoring

- [ ] **Tests**: `tests/integration/test_researcher.py`
  - [ ] Mock Tavily responses
  - [ ] Test source extraction

### Validator Agent (Week 4, Day 1-2)

- [ ] **aris/agents/validator.py** (single-model version)
  - [ ] Claim extraction from text
  - [ ] Basic validation (one model)
  - [ ] Store validation logs

- [ ] **Tests**: `tests/unit/test_validator.py`
  - [ ] Test claim extraction
  - [ ] Test validation logic

### Synthesizer Agent (Week 4, Day 3-4)

- [ ] **aris/agents/synthesizer.py**
  - [ ] Markdown generation from claims
  - [ ] Document structure creation
  - [ ] Version storage

- [ ] **aris/output/renderer.py**
  - [ ] Markdown templates
  - [ ] Citation formatting

- [ ] **Tests**: `tests/unit/test_synthesizer.py`
  - [ ] Test document generation
  - [ ] Test citation inclusion

### End-to-End Integration (Week 4, Day 5)

- [ ] **Basic orchestrator** (simplified)
  ```python
  async def execute_research(query: str):
      # 1. Coordinator
      plan = await coordinator.decompose_query(query)

      # 2. Researcher
      findings = await researcher.research(plan.sub_queries[0])

      # 3. Validator
      claims = await validator.validate(findings)

      # 4. Synthesizer
      doc = await synthesizer.generate_document(claims)

      return doc
  ```

- [ ] **CLI command**:
  - [ ] `aris research <query>`

**Phase 2 Validation**:
```bash
poetry run aris research "What is PowerSync?"
# Should create document with validated claims
```

---

## Phase 3: Multi-Model Consensus

### Consensus Validator (Week 5, Day 1-3)

- [ ] **aris/core/consensus.py**
  - [ ] Multi-provider support (Anthropic, OpenAI, Google)
  - [ ] Parallel validation calls
  - [ ] Consensus scoring
  - [ ] Disagreement handling

- [ ] **Provider clients**:
  - [ ] Anthropic client (async)
  - [ ] OpenAI client (async)
  - [ ] Google client (async)

- [ ] **Caching**:
  - [ ] In-memory cache (LRU)
  - [ ] Cache key: (claim_hash, sources_hash)

- [ ] **Tests**: `tests/unit/test_consensus.py`
  - [ ] Test with mocked models
  - [ ] Test consensus calculation
  - [ ] Test disagreement scenarios

### Validation Pipeline (Week 5, Day 4-5)

- [ ] **Update validator agent**
  - [ ] Replace single-model with consensus
  - [ ] Store validation logs per model
  - [ ] Threshold-based approval

- [ ] **Confidence thresholds**:
  - [ ] Configure in config.yaml
  - [ ] Flag low-confidence claims

### Conflict Detection (Week 6, Day 1-2)

- [ ] **aris/agents/validator.py** (enhanced)
  - [ ] Contradiction detection logic
  - [ ] Conflict severity scoring
  - [ ] Conflict record creation

- [ ] **Tests**: `tests/unit/test_conflict_detection.py`

### Human Review Workflow (Week 6, Day 3-4)

- [ ] **CLI commands**:
  - [ ] `aris conflicts list`
  - [ ] `aris conflicts resolve <id> --resolution <text>`
  - [ ] `aris conflicts show <id>`

- [ ] **Review interface**:
  - [ ] Show conflicting claims side-by-side
  - [ ] Show source evidence
  - [ ] Accept/reject/modify options

**Phase 3 Validation**:
```bash
poetry run aris research "controversial topic"
# Should detect conflicts and flag for review
poetry run aris conflicts list
# Should show detected conflicts
```

---

## Phase 4: Task Queue & Parallelism

### Task Queue Implementation (Week 7, Day 1-3)

- [ ] **aris/core/task_queue.py**
  - [ ] Task submission API
  - [ ] Dependency resolution (topological sort)
  - [ ] Task execution loop
  - [ ] Parallel task executor (asyncio.gather)
  - [ ] Retry logic with exponential backoff

- [ ] **Database queries**:
  - [ ] Get tasks by status
  - [ ] Get ready tasks (dependencies met)
  - [ ] Update task status atomically

- [ ] **Tests**: `tests/unit/test_task_queue.py`
  - [ ] Test DAG creation
  - [ ] Test topological sort
  - [ ] Test parallel execution
  - [ ] Test retry logic

### Orchestrator Integration (Week 7, Day 4-5)

- [ ] **aris/core/orchestrator.py**
  - [ ] Task graph creation from research plan
  - [ ] Submit tasks to queue
  - [ ] Monitor task completion
  - [ ] Aggregate results

- [ ] **Update agents**:
  - [ ] Make agents task-aware
  - [ ] Report progress to orchestrator

### Progress Streaming (Week 8, Day 1-2)

- [ ] **Real-time updates**:
  - [ ] WebSocket server (optional)
  - [ ] File-based progress log
  - [ ] CLI streaming output

- [ ] **Progress format**:
  - [ ] Timestamp
  - [ ] Agent name
  - [ ] Status message
  - [ ] Progress percentage

- [ ] **CLI enhancement**:
  - [ ] `aris research --stream` for real-time output
  - [ ] Progress bars with Rich

### Error Handling (Week 8, Day 3-4)

- [ ] **Circuit breaker**:
  - [ ] Track failure rates
  - [ ] Open circuit after threshold
  - [ ] Half-open recovery

- [ ] **Graceful degradation**:
  - [ ] Fallback strategies per agent
  - [ ] Continue with partial results

- [ ] **Tests**: `tests/integration/test_error_handling.py`

**Phase 4 Validation**:
```bash
poetry run aris research "complex multi-faceted question" --stream
# Should show parallel task execution
# Should handle failures gracefully
```

---

## Phase 5: Document Management

### Semantic Deduplication (Week 9, Day 1-2)

- [ ] **aris/knowledge/vector_store.py**
  - [ ] ChromaDB integration
  - [ ] Embedding generation (OpenAI)
  - [ ] Similarity search
  - [ ] Add/update/delete operations

- [ ] **Coordinator enhancement**:
  - [ ] Check vector store before creating topic
  - [ ] Return existing if similarity > 0.85

- [ ] **Tests**: `tests/unit/test_vector_store.py`

### Document Versioning (Week 9, Day 3-4)

- [ ] **Version storage**:
  - [ ] Store full content in database
  - [ ] Store diff from previous version
  - [ ] Metadata (created_by, commit_message)

- [ ] **aris/output/differ.py**:
  - [ ] Generate unified diffs
  - [ ] HTML diff with highlighting

- [ ] **CLI commands**:
  - [ ] `aris diff <doc> --version A:B`
  - [ ] `aris history <doc>`

### Section Mapping (Week 9, Day 5)

- [ ] **Synthesizer enhancement**:
  - [ ] Parse existing document structure
  - [ ] Semantic matching of claims to sections
  - [ ] Preserve unchanged content

- [ ] **Tests**: `tests/unit/test_section_mapping.py`

### Document Update Logic (Week 10, Day 1-3)

- [ ] **Update algorithm**:
  ```python
  async def update_document(topic, new_claims):
      existing_doc = load_document(topic.document_path)
      sections = parse_sections(existing_doc)

      for claim in new_claims:
          section = map_claim_to_section(claim, sections)
          section.add_claim(claim)

      new_content = render_sections(sections)
      diff = generate_diff(existing_doc, new_content)

      save_version(topic, new_content, diff)
      write_file(topic.document_path, new_content)
  ```

- [ ] **Preserve existing content**:
  - [ ] Non-factual sections (intro, conclusion)
  - [ ] User-added notes
  - [ ] Manual edits

- [ ] **Tests**: `tests/integration/test_document_update.py`

**Phase 5 Validation**:
```bash
poetry run aris research "question about X"
# Creates document
poetry run aris research "follow-up question about X"
# Updates same document, not create new
poetry run aris diff research/x.md --version 1:2
# Shows what changed
```

---

## Phase 6: Knowledge Graph

### Neo4j Integration (Week 11, Day 1-2)

- [ ] **aris/knowledge/graph_db.py**
  - [ ] Neo4j driver setup
  - [ ] Node creation (Topic, Claim, Source)
  - [ ] Relationship creation (CONTAINS, SUPPORTED_BY, etc.)
  - [ ] Cypher query methods

- [ ] **Schema definition**:
  - [ ] Node labels and properties
  - [ ] Relationship types
  - [ ] Indexes for performance

### Topic Relationships (Week 11, Day 3-4)

- [ ] **Relationship detection**:
  - [ ] Semantic similarity between topics
  - [ ] Shared claims/sources
  - [ ] Citation analysis

- [ ] **Graph queries**:
  - [ ] Find related topics
  - [ ] Shortest path between topics
  - [ ] Centrality metrics

### Claim Contradictions (Week 11, Day 5)

- [ ] **Contradiction graph**:
  - [ ] CONTRADICTS relationship
  - [ ] Severity weights
  - [ ] Resolution tracking

- [ ] **Conflict resolution UI**:
  - [ ] Show graph visualization (ASCII art or export)

### Vector Embeddings (Week 12, Day 1-2)

- [ ] **Full ChromaDB integration**:
  - [ ] Collection for topics
  - [ ] Collection for claims
  - [ ] Collection for documents

- [ ] **Embedding strategy**:
  - [ ] Generate on creation
  - [ ] Update on modification
  - [ ] Cache embeddings

### Semantic Search (Week 12, Day 3-4)

- [ ] **CLI command**:
  - [ ] `aris search <query>` - Find similar topics
  - [ ] `aris related <topic>` - Find related topics

- [ ] **Search ranking**:
  - [ ] Combine vector similarity
  - [ ] Graph connectivity
  - [ ] Recency

**Phase 6 Validation**:
```bash
poetry run aris search "offline architecture"
# Should find related topics
poetry run aris related <topic_id>
# Should show knowledge graph connections
```

---

## Phase 7: MCP Integration

### Generic MCP Client (Week 13, Day 1-2)

- [ ] **aris/integrations/mcp_client.py**
  - [ ] Connection management
  - [ ] Tool invocation
  - [ ] Error handling
  - [ ] Circuit breaker per server

- [ ] **Configuration**:
  - [ ] MCP server URLs in config.yaml
  - [ ] Health check on startup

### Context7 Integration (Week 13, Day 3)

- [ ] **aris/integrations/context7_client.py**
  - [ ] Library documentation search
  - [ ] Code example retrieval
  - [ ] Version-specific queries

- [ ] **Researcher agent enhancement**:
  - [ ] Add Context7 to search strategies
  - [ ] Prioritize for technical queries

### Sequential MCP (Week 13, Day 4)

- [ ] **aris/integrations/sequential_client.py**
  - [ ] Multi-step reasoning invocation
  - [ ] Use for complex analysis tasks

- [ ] **Validator agent enhancement**:
  - [ ] Use Sequential for claim reasoning

### Playwright MCP (Week 13, Day 5)

- [ ] **aris/integrations/playwright_client.py**
  - [ ] Web scraping via Playwright
  - [ ] JavaScript rendering
  - [ ] Screenshot capture

- [ ] **Researcher agent enhancement**:
  - [ ] Fallback to Playwright for complex pages

### Circuit Breakers (Week 14, Day 1-2)

- [ ] **Per-server circuit breakers**:
  - [ ] Track failure rates
  - [ ] Automatic fallback
  - [ ] Recovery logic

- [ ] **Monitoring**:
  - [ ] Log circuit state changes
  - [ ] Alert on prolonged open circuits

### Fallback Strategies (Week 14, Day 3-4)

- [ ] **Define fallbacks**:
  ```yaml
  tavily:
    fallback: native_web_search
  context7:
    fallback: tavily_documentation_search
  sequential:
    fallback: native_reasoning
  ```

- [ ] **Test all fallback paths**

**Phase 7 Validation**:
```bash
# Test with MCP servers running
poetry run aris research "technical documentation query"
# Should use Context7

# Test with MCP servers down
# Should fallback gracefully
```

---

## Phase 8: Advanced Agents

### Challenger Agent (Week 15, Day 1-2)

- [ ] **aris/agents/challenger.py**
  - [ ] Logical gap detection
  - [ ] Bias identification
  - [ ] Counter-argument generation
  - [ ] Missing perspective finder

- [ ] **Integration into workflow**:
  - [ ] Run after validation
  - [ ] Generate recommendations

### Archivist Agent (Week 15, Day 3-4)

- [ ] **aris/agents/archivist.py**
  - [ ] Document indexing
  - [ ] Knowledge graph updates
  - [ ] Deduplication
  - [ ] Taxonomy generation

- [ ] **CLI commands**:
  - [ ] `aris index rebuild`
  - [ ] `aris taxonomy show`

### A2A Protocol (Week 15, Day 5)

- [ ] **aris/integrations/a2a_protocol.py**
  - [ ] Message format (from blueprint)
  - [ ] Serialization/deserialization
  - [ ] Trace ID propagation

### Message Bus (Week 16, Day 1-2)

- [ ] **In-process message bus**:
  - [ ] Publish/subscribe pattern
  - [ ] Topic-based routing
  - [ ] Async message delivery

- [ ] **Agent coordination**:
  - [ ] Agents subscribe to their topics
  - [ ] Orchestrator publishes tasks

### Full Multi-Agent Workflow (Week 16, Day 3-4)

- [ ] **Integrate all agents**:
  - [ ] Coordinator → Researcher (parallel)
  - [ ] Researcher → Validator
  - [ ] Validator → Challenger (parallel)
  - [ ] Validator → Synthesizer
  - [ ] Synthesizer → Archivist

- [ ] **Tests**: `tests/integration/test_full_workflow.py`

**Phase 8 Validation**:
```bash
poetry run aris research "complex question" --verbose
# Should show all agent interactions
# Should include challenger recommendations
```

---

## Phase 9: Production Hardening

### PostgreSQL Migration (Week 17, Day 1-2)

- [ ] **Migration script**: `scripts/migrate_to_postgres.py`
  - [ ] Export from SQLite
  - [ ] Import to PostgreSQL
  - [ ] Verify data integrity

- [ ] **Configuration**:
  - [ ] Support both SQLite and PostgreSQL
  - [ ] Auto-detect based on config

- [ ] **pgvector extension**:
  - [ ] Install extension
  - [ ] Migrate embeddings

### Error Handling Comprehensive (Week 17, Day 3-4)

- [ ] **Error categories**:
  - [ ] Transient (retry)
  - [ ] Permanent (fail)
  - [ ] Degraded (fallback)

- [ ] **Error responses**:
  - [ ] Structured error messages
  - [ ] Recovery suggestions
  - [ ] Error codes

- [ ] **Tests**: Error injection tests

### Monitoring (Week 17, Day 5)

- [ ] **Structured logging**:
  - [ ] JSON format
  - [ ] Trace IDs
  - [ ] Context propagation

- [ ] **Metrics collection**:
  - [ ] Task durations
  - [ ] API call latencies
  - [ ] Error rates

- [ ] **Optional integrations**:
  - [ ] Sentry for errors
  - [ ] Prometheus for metrics

### Performance Optimization (Week 18, Day 1-2)

- [ ] **Database**:
  - [ ] Index optimization
  - [ ] Query profiling
  - [ ] Connection pooling

- [ ] **Caching**:
  - [ ] Validation result cache
  - [ ] Embedding cache
  - [ ] MCP response cache

- [ ] **Benchmarks**: `scripts/benchmark.py`

### Security Audit (Week 18, Day 3-4)

- [ ] **API key management**:
  - [ ] Use keyring library
  - [ ] Never log keys
  - [ ] Rotation support

- [ ] **Input sanitization**:
  - [ ] SQL injection prevention
  - [ ] XSS prevention (if web UI)
  - [ ] Rate limiting

- [ ] **Dependencies**:
  - [ ] Run `poetry audit`
  - [ ] Update vulnerable packages

**Phase 9 Validation**:
```bash
# Run full test suite
poetry run pytest --cov=aris

# Run benchmarks
poetry run python scripts/benchmark.py

# Security scan
poetry run bandit -r aris/
```

---

## Phase 10: Documentation & Release

### User Documentation (Week 19, Day 1-2)

- [ ] **README.md**:
  - [ ] Project description
  - [ ] Installation instructions
  - [ ] Quick start guide
  - [ ] Examples

- [ ] **docs/user_guide.md**:
  - [ ] Detailed usage
  - [ ] CLI reference
  - [ ] Configuration options
  - [ ] Troubleshooting

### API Documentation (Week 19, Day 3-4)

- [ ] **docs/api_reference.md**:
  - [ ] All public APIs
  - [ ] Code examples
  - [ ] Type signatures

- [ ] **Docstrings**:
  - [ ] All public functions
  - [ ] Google style format

### Example Workflows (Week 19, Day 5)

- [ ] **docs/examples/**:
  - [ ] Basic research workflow
  - [ ] Multi-topic research
  - [ ] Conflict resolution
  - [ ] Custom agent development

### Installation Testing (Week 20, Day 1-2)

- [ ] **Fresh environment testing**:
  ```bash
  # Test on clean system
  git clone <repo>
  poetry install
  poetry run aris init --name test
  poetry run aris research "test query"
  ```

- [ ] **Docker image**:
  - [ ] Build Dockerfile
  - [ ] Test container deployment

### Release Preparation (Week 20, Day 3-4)

- [ ] **Version tagging**:
  - [ ] Update version in pyproject.toml
  - [ ] Create git tag v1.0.0

- [ ] **Changelog**:
  - [ ] Document all features
  - [ ] Known limitations
  - [ ] Migration notes

- [ ] **PyPI publishing**:
  - [ ] Build package: `poetry build`
  - [ ] Test on TestPyPI
  - [ ] Publish: `poetry publish`

**Phase 10 Validation**:
```bash
# External user installation
pip install aris-tool
aris init --name my-research
aris research "test question"
# Should work out-of-box
```

---

## Critical Path Items

These must be completed before moving to next phase:

**Phase 1 → 2**: Database schema finalized, basic CLI working
**Phase 2 → 3**: Single-agent workflow end-to-end functional
**Phase 3 → 4**: Multi-model consensus working correctly
**Phase 4 → 5**: Task queue with parallelism stable
**Phase 5 → 6**: Document update (not create) guaranteed
**Phase 6 → 7**: Knowledge graph queries functional
**Phase 7 → 8**: MCP integrations with fallbacks working
**Phase 8 → 9**: All agents coordinating correctly
**Phase 9 → 10**: Production-ready quality, no critical bugs

---

## Testing Requirements

### Unit Test Coverage Targets

- [ ] `core/*`: 90%+
- [ ] `agents/*`: 85%+
- [ ] `integrations/*`: 70%+ (mocked externals)
- [ ] `knowledge/*`: 85%+
- [ ] `utils/*`: 95%+

### Integration Tests

- [ ] Full research workflow (mocked APIs)
- [ ] Database transaction rollback
- [ ] Task DAG execution
- [ ] Multi-model consensus
- [ ] Document update vs create

### End-to-End Tests (Optional)

- [ ] Real API calls (requires keys)
- [ ] Full workflow with real data
- [ ] Performance benchmarks

---

## Risk Mitigation

### High-Risk Areas

1. **Multi-model consensus cost**:
   - Mitigation: Cache aggressively, use cheaper models first

2. **Database migrations**:
   - Mitigation: Test SQLite → PostgreSQL path thoroughly

3. **Task queue deadlocks**:
   - Mitigation: Extensive DAG testing, cycle detection

4. **Document update correctness**:
   - Mitigation: Comprehensive integration tests

5. **MCP server unavailability**:
   - Mitigation: Circuit breakers, fallback strategies

---

## Daily Progress Checklist

Use this template for daily tracking:

```markdown
## Date: YYYY-MM-DD
**Phase**: X | **Week**: Y | **Day**: Z

### Goals for Today
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

### Completed
- [x] Task A
- [x] Task B

### Blockers
- Blocker description (resolution: ...)

### Tests Passing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual smoke test

### Notes
- Any important decisions or learnings
```

---

## Success Criteria Summary

Before declaring phase complete, verify:

**Phase 1**:
- ✅ Database initializes
- ✅ CLI runs without errors
- ✅ Basic commands work

**Phase 2**:
- ✅ End-to-end research workflow functional
- ✅ Document created with claims
- ✅ Sources stored in database

**Phase 3**:
- ✅ Consensus validation working
- ✅ Low-confidence claims flagged
- ✅ Conflicts detected

**Phase 4**:
- ✅ Parallel tasks execute correctly
- ✅ Dependencies resolved properly
- ✅ Errors handled gracefully

**Phase 5**:
- ✅ Never creates duplicate documents
- ✅ Updates preserve existing content
- ✅ Diff generation works

**Phase 6**:
- ✅ Knowledge graph queries functional
- ✅ Semantic search returns relevant results
- ✅ Related topics discoverable

**Phase 7**:
- ✅ All MCP servers integrated
- ✅ Fallbacks work when servers down
- ✅ Circuit breakers functional

**Phase 8**:
- ✅ All agents coordinate correctly
- ✅ A2A messages flowing
- ✅ Full workflow with all agents

**Phase 9**:
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Security audit passed

**Phase 10**:
- ✅ Documentation complete
- ✅ External users can install
- ✅ v1.0.0 released

---

## Next Actions

**Immediate** (Start today):
1. Initialize Poetry project
2. Create directory structure
3. Write data models (Topic, Claim, Source, Task)
4. Set up pytest configuration

**This Week**:
- Complete Phase 1 (Core Foundation)
- Begin Phase 2 (Single-Agent Pipeline)

**This Month**:
- Complete Phases 1-4
- Have basic functional research system

---

## Maintenance Schedule

**Weekly**:
- Dependency updates (poetry update)
- Run security audit (poetry audit)

**Monthly**:
- Performance benchmarks
- Database optimization
- Log analysis

**Quarterly**:
- Major dependency upgrades
- Feature roadmap review
- User feedback analysis
