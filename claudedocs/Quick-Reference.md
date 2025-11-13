# ARIS Quick Reference Guide

**Last Updated**: 2025-11-12 | **Blueprint Version**: 1.0.0

This document provides rapid access to key system information for developers and agents.

---

## System Overview

**ARIS** = Autonomous Research Intelligence System

**Purpose**: Multi-agent research orchestration preventing document proliferation and hallucinations through consensus validation.

**Core Innovation**: Document-as-database + semantic deduplication + multi-model consensus = never create duplicates, always validate facts.

---

## Architecture at a Glance

```
CLI → Orchestrator → Task Queue → Agents → MCP Servers → Database
                                   ↓
                            Consensus Validator
                                   ↓
                              Knowledge Graph
```

**Tech Stack**:
- **Language**: Python 3.11+
- **Framework**: asyncio, Click CLI, Pydantic models
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Knowledge**: Neo4j (graph), ChromaDB (vectors)
- **APIs**: Anthropic, OpenAI, Google (consensus), Tavily, Context7

---

## Module Map

| Module | Responsibility | Key Functions |
|--------|----------------|---------------|
| `core/orchestrator.py` | Coordination hub | execute_research() |
| `core/state_manager.py` | Database CRUD | transaction(), get_topic() |
| `core/task_queue.py` | DAG scheduler | submit_task(), execute_dag() |
| `core/consensus.py` | Multi-model validation | validate_claim() |
| `agents/coordinator.py` | Query decomposition | decompose_query(), find_existing_topic() |
| `agents/researcher.py` | Info gathering | research_subtopic() |
| `agents/validator.py` | Fact-checking | extract_claims(), detect_contradictions() |
| `agents/synthesizer.py` | Document generation | update_document() |
| `agents/challenger.py` | Critical analysis | find_gaps() |
| `agents/archivist.py` | Indexing | index_document(), update_graph() |
| `integrations/mcp_client.py` | MCP connection | call_tool() |
| `integrations/*_client.py` | Specific MCP wrappers | search(), lookup(), scrape() |
| `knowledge/graph_db.py` | Neo4j interface | find_related_topics() |
| `knowledge/vector_store.py` | Embeddings | semantic_search() |
| `cli.py` | User interface | All commands |

---

## Database Schema Quick Ref

**Core Tables**:
- `topics`: Research entities (title, state, confidence, document_path)
- `claims`: Atomic facts (content, confidence, validation)
- `sources`: Provenance (url, authority_score, content_hash)
- `claim_sources`: Many-to-many relationship
- `conflicts`: Contradictions (claim_a, claim_b, resolved)
- `tasks`: DAG queue (status, dependencies, results)
- `validation_logs`: Consensus tracking (model, agrees, reasoning)
- `document_versions`: Git-like history (version, diff, commit_message)

**Key Indexes**:
- `topics.query_embedding` (vector similarity)
- `claims.confidence` (quality filtering)
- `tasks.status` + `priority` (queue processing)
- `sources.url` (deduplication)

---

## CLI Commands Reference

```bash
# Initialize
aris init --name <project>

# Research (main command)
aris research "<query>"
aris research "<query>" --stream      # Real-time progress
aris research "<query>" --verbose     # Detailed logging

# Status and inspection
aris status                           # System overview
aris show <document>                  # View document
aris history <document>               # Version history
aris diff <document> --version A:B    # Show changes

# Conflict management
aris conflicts list                   # All conflicts
aris conflicts show <id>              # Conflict details
aris conflicts resolve <id> --resolution <text>

# Search and discovery
aris search "<query>"                 # Semantic search
aris related <topic_id>               # Related topics

# Configuration
aris config set <key> <value>
aris config get <key>
aris config list

# Maintenance
aris validate --all                   # Re-validate claims
aris index rebuild                    # Rebuild search index
aris export --format pdf              # Export reports

# Agent introspection
aris agents --status                  # Agent health
aris logs --agent <name> --tail 50    # Agent logs
```

---

## Data Flow: Research Workflow

```
1. User Query
   ↓
2. Orchestrator (parse, route)
   ↓
3. Coordinator (semantic dedup, decompose)
   ↓ [Mode: UPDATE or CREATE]
4. Task Queue (create DAG)
   ↓
5. Researcher Agents (parallel web search, doc lookup)
   ↓
6. Validator (extract claims, consensus validation)
   ↓
7. Challenger (logical gaps, biases)
   ↓
8. Synthesizer (generate/update document)
   ↓
9. Archivist (index, graph update)
   ↓
10. Result (JSON output with metadata)
```

---

## Key Algorithms

### Semantic Deduplication
```python
query_embedding = embed(query)
similar = vector_store.search(query_embedding, threshold=0.85)
if similar:
    mode = UPDATE
    topic = similar[0]
else:
    mode = CREATE
    topic = create_new()
```

### Multi-Model Consensus
```python
models = [claude, gpt4, gemini]
validations = await asyncio.gather(*[
    model.verify(claim, sources) for model in models
])
consensus = sum(v.agrees for v in validations) / len(models)
approved = consensus >= 0.7
```

### DAG Task Execution
```python
levels = topological_sort(tasks)  # Group by dependency level
for level in levels:
    results = await asyncio.gather(*[
        execute_task(t) for t in level  # Parallel within level
    ])
    propagate_results_to_dependents(results)
```

### Section Mapping
```python
claim_embedding = embed(claim.content)
section_embeddings = [embed(s.header + s.preview) for s in sections]
similarities = cosine_similarity(claim_embedding, section_embeddings)
best_section = sections[argmax(similarities)]
```

---

## Configuration Quick Ref

**config.yaml** (key settings):
```yaml
database:
  type: sqlite | postgresql
  path: ./data/aris.db  # SQLite
  # host, port, database, user, password for PostgreSQL

agents:
  max_parallel: 10
  retry_max_attempts: 3

consensus:
  threshold: 0.7  # 0.0-1.0
  models:
    - anthropic/claude-sonnet-4-5
    - openai/gpt-4-turbo
    - google/gemini-1.5-pro

integrations:
  tavily: {search_depth: advanced, max_results: 10}
  context7: {enabled: true}
  sequential: {enabled: true}
  neo4j: {enabled: false}  # Optional
```

**Environment Variables**:
```bash
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
POSTGRES_PASSWORD=...  # If using PostgreSQL
NEO4J_PASSWORD=...     # If using Neo4j
```

---

## Testing Quick Commands

```bash
# Unit tests
poetry run pytest tests/unit/

# Integration tests
poetry run pytest tests/integration/

# Specific test
poetry run pytest tests/unit/test_consensus.py::test_validation

# Coverage report
poetry run pytest --cov=aris --cov-report=html

# Linting
poetry run ruff check aris/
poetry run black --check aris/
poetry run mypy aris/

# Security scan
poetry run bandit -r aris/
```

---

## Error Handling Patterns

**Transient Errors** (Retry):
```python
@retry(max_attempts=3, backoff=exponential)
async def api_call():
    # Network timeout, rate limit, etc.
    pass
```

**Permanent Errors** (Fail Fast):
```python
if not valid_api_key:
    raise ConfigurationError("Invalid API key")
```

**Degraded Errors** (Fallback):
```python
try:
    result = await tavily_search(query)
except TavilyUnavailable:
    logger.warning("Tavily down, using fallback")
    result = await native_search(query)
```

**Circuit Breaker**:
```python
if circuit_breaker.is_open("tavily"):
    return await fallback_search(query)
```

---

## Performance Optimization Checklist

- [ ] Cache validation results by (claim_hash, sources_hash)
- [ ] Use cheaper models for preliminary screening
- [ ] Batch API calls where possible
- [ ] Parallel execution with asyncio.gather
- [ ] Database connection pooling (max 20)
- [ ] Vector index for semantic search
- [ ] Database query result caching
- [ ] MCP response caching (time-based)

---

## Debugging Tips

**Trace a Research Query**:
```bash
# Enable verbose logging
export ARIS_LOG_LEVEL=DEBUG
aris research "query" --verbose

# Follow task execution
tail -f data/logs/tasks.log

# Inspect database state
sqlite3 data/aris.db
> SELECT * FROM topics ORDER BY updated_at DESC LIMIT 5;
> SELECT * FROM tasks WHERE status='failed';
```

**Common Issues**:

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "Duplicate document created" | Semantic dedup failed | Check embedding service, lower threshold |
| "Validation timeout" | API rate limit | Reduce concurrent validations |
| "Task deadlock" | Circular dependency | Check DAG creation logic |
| "Low confidence" | Conflicting sources | Review sources, adjust threshold |
| "MCP connection failed" | Server down | Check circuit breaker, use fallback |

---

## Security Checklist

- [ ] API keys in keyring (not .env files)
- [ ] Input sanitization (SQL injection prevention)
- [ ] Rate limiting per user/IP
- [ ] Audit logging for all state changes
- [ ] HTTPS for all external API calls
- [ ] No API keys in logs
- [ ] Regular dependency security audits (`poetry audit`)
- [ ] Principle of least privilege (database permissions)

---

## Scalability Thresholds

**Single Process (SQLite)**:
- Topics: < 1,000
- Concurrent tasks: < 10
- Users: 1 (CLI tool)

**Single Process (PostgreSQL)**:
- Topics: < 10,000
- Concurrent tasks: < 50
- Users: < 10 (shared database)

**Distributed (Multi-Process + PostgreSQL)**:
- Topics: < 100,000
- Concurrent tasks: < 500
- Users: < 100

**Enterprise (Kubernetes + PostgreSQL Cluster)**:
- Topics: 1M+
- Concurrent tasks: 5,000+
- Users: 1,000+

---

## Migration Paths

**Development → Production**:
```bash
# 1. Backup SQLite database
cp data/aris.db data/aris.db.backup

# 2. Run migration script
poetry run python scripts/migrate_to_postgres.py

# 3. Update config.yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: aris
  user: aris_user

# 4. Verify migration
poetry run aris status
```

**Single Process → Distributed**:
1. Deploy PostgreSQL cluster (primary + replicas)
2. Deploy RabbitMQ for message bus
3. Update A2A protocol to use RabbitMQ
4. Deploy agent workers (Celery)
5. Deploy orchestrator instances behind load balancer
6. Update configuration for distributed mode

---

## Performance Benchmarks (Target)

**Research Query**:
- Simple (1 sub-query): < 30s
- Complex (5 sub-queries): < 2 min
- Comprehensive (10+ sub-queries): < 5 min

**Validation**:
- Single claim (3 models): < 5s
- 10 claims batch: < 15s
- 100 claims: < 2 min (parallel batching)

**Database Operations**:
- Topic creation: < 50ms
- Claim validation write: < 20ms
- Semantic search: < 100ms
- Document rendering: < 500ms

**API Latencies**:
- Tavily search: 1-3s
- Context7 lookup: 2-4s
- LLM validation: 3-8s (per model)
- Playwright scrape: 5-15s (per page)

---

## Code Quality Standards

**Test Coverage**:
- Core modules: 90%+
- Agents: 85%+
- Integrations: 70%+ (mocked externals)
- Utils: 95%+

**Code Style**:
- Formatter: Black (line length 100)
- Linter: Ruff (strict mode)
- Type Checker: mypy (strict mode)
- Docstrings: Google style

**Git Workflow**:
- Feature branches from main
- Pull requests with review
- Squash merges
- Semantic commit messages

---

## Useful One-Liners

```bash
# Count topics by state
sqlite3 data/aris.db "SELECT state, COUNT(*) FROM topics GROUP BY state;"

# Find low-confidence claims
sqlite3 data/aris.db "SELECT content, confidence FROM claims WHERE confidence < 0.7;"

# Show failed tasks
sqlite3 data/aris.db "SELECT agent_type, error_message FROM tasks WHERE status='failed';"

# Validate all claims above threshold
poetry run python -c "from aris.core.consensus import revalidate_all; import asyncio; asyncio.run(revalidate_all(threshold=0.7))"

# Export knowledge graph
poetry run python -c "from aris.knowledge.graph_db import export_graph; export_graph('graph.json')"

# Backup database
cp data/aris.db "data/aris-backup-$(date +%Y%m%d).db"

# Clear cache
rm -rf data/cache/*

# Reset database (⚠️ destructive)
rm data/aris.db && poetry run aris init --name restored
```

---

## Support and Resources

**Documentation**:
- Architecture: `claudedocs/ARIS-Architecture-Blueprint.md`
- Implementation: `claudedocs/Implementation-Checklist.md`
- Decisions: `claudedocs/Architectural-Decisions.md`
- This Guide: `claudedocs/Quick-Reference.md`

**Issue Reporting**:
1. Check logs: `data/logs/*.log`
2. Gather context: `aris status`, `aris agents --status`
3. Create minimal reproduction case
4. Include: version, config, error messages, logs

**Development Setup**:
```bash
git clone <repo>
cd aris-tool
poetry install
poetry run pre-commit install  # Git hooks
poetry run aris init --name dev
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export TAVILY_API_KEY=...
poetry run pytest
```

---

## Version Compatibility

| ARIS Version | Python | SQLite | PostgreSQL | Neo4j |
|--------------|--------|--------|------------|-------|
| 1.0.x        | 3.11+  | 3.37+  | 14+        | 5.x   |
| 0.9.x (beta) | 3.10+  | 3.35+  | 13+        | 4.x   |

**Deprecation Policy**:
- Major versions: Breaking changes allowed
- Minor versions: New features, no breaking changes
- Patch versions: Bug fixes only

---

## Quick Decision Matrix

**When to use ARIS?**
✅ Multi-document research synthesis
✅ Fact-checking with provenance
✅ Evolving knowledge base (updates, not rewrites)
✅ Collaborative research (shared database)

**When NOT to use ARIS?**
❌ Simple web search (overkill)
❌ Real-time chat (high latency)
❌ Unstructured notes (use Obsidian/Notion)
❌ No API access (requires external services)

---

## Emergency Procedures

**Database Corruption**:
```bash
# 1. Stop all processes
pkill -f "aris"

# 2. Backup current state
cp data/aris.db data/aris-corrupted.db

# 3. Restore from backup
cp data/aris-backup-latest.db data/aris.db

# 4. Verify integrity
sqlite3 data/aris.db "PRAGMA integrity_check;"

# 5. If clean, restart
poetry run aris status
```

**High API Costs**:
```bash
# 1. Check usage
grep "API_COST" data/logs/api.log | awk '{sum+=$4} END {print sum}'

# 2. Temporarily disable expensive models
aris config set consensus.models "anthropic/claude-haiku-3-5"

# 3. Enable aggressive caching
aris config set caching.validation_ttl 86400  # 24 hours

# 4. Monitor going forward
watch -n 60 'grep "API_COST" data/logs/api.log | tail -20'
```

**Performance Degradation**:
```bash
# 1. Check task queue
sqlite3 data/aris.db "SELECT COUNT(*) FROM tasks WHERE status='pending';"

# 2. Kill stuck tasks
poetry run python -c "from aris.core.task_queue import cancel_stuck_tasks; cancel_stuck_tasks()"

# 3. Rebuild indexes
sqlite3 data/aris.db "REINDEX;"

# 4. Clear old logs
find data/logs -type f -mtime +30 -delete

# 5. Restart system
# (graceful shutdown, then restart)
```

---

## Glossary

**A2A**: Agent-to-Agent communication protocol
**Claim**: Atomic factual assertion with provenance
**Consensus**: Multi-model agreement score (0.0-1.0)
**DAG**: Directed Acyclic Graph for task dependencies
**MCP**: Model Context Protocol for tool integration
**Provenance**: Source tracking for claims
**Semantic Deduplication**: Vector similarity to prevent duplicates
**Topic**: Research subject with associated document
**Validation**: Multi-model fact-checking process

---

**End of Quick Reference**

For detailed information, consult the full architectural blueprint and implementation checklist.
