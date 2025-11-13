# ARIS Architectural Decision Records (ADR)

Generated: 2025-11-12
Blueprint Version: 1.0.0

This document captures key architectural decisions, their rationale, and trade-offs.

---

## ADR-001: SQLite for Development, PostgreSQL for Production

**Status**: Accepted

**Context**:
Need database that supports:
- ACID transactions for state consistency
- Vector embeddings for semantic search
- Graph-like queries for relationships
- Migration path from simple to enterprise

**Decision**:
- Start with SQLite for development/single-user
- Design schema for PostgreSQL compatibility
- Use Alembic for version-controlled migrations
- Provide migration script for production upgrade

**Rationale**:
- SQLite: Zero configuration, embedded, perfect for CLI tool
- PostgreSQL: Production-grade, pgvector extension, replication support
- Alembic: Industry-standard migration tool with rollback support

**Trade-offs**:
✅ **Pros**:
- Fast development iteration with SQLite
- No external dependencies initially
- Clear upgrade path for scaling
- Schema remains consistent across databases

❌ **Cons**:
- Different SQL dialects require testing both
- Some PostgreSQL features unavailable in SQLite
- Migration adds operational complexity

**Alternatives Considered**:
- **PostgreSQL Only**: Rejected (too heavy for CLI tool)
- **MongoDB**: Rejected (ACID transactions less robust, no vector support)
- **DynamoDB**: Rejected (AWS lock-in, complex local development)

---

## ADR-002: Multi-Model Consensus for Validation

**Status**: Accepted

**Context**:
LLMs hallucinate. Single model validation insufficient for reliable research. Need mechanism to detect and prevent false claims.

**Decision**:
- Query 3+ LLM providers for each claim validation
- Calculate consensus score (% agreement)
- Require threshold (default 0.7) for claim acceptance
- Store per-model validation logs for provenance

**Rationale**:
- Multiple models unlikely to hallucinate identically
- Disagreement signals uncertainty or complexity
- Consensus provides measurable confidence metric
- Logs enable debugging and improvement

**Trade-offs**:
✅ **Pros**:
- Dramatically reduces hallucination risk
- Quantifiable confidence scores
- Catches model-specific biases
- Auditable validation process

❌ **Cons**:
- 3x API costs for validation
- Increased latency (parallel helps)
- Models may agree on popular misconceptions
- Requires managing multiple API keys

**Cost Mitigation**:
- Cache validation results by (claim_hash, sources_hash)
- Use cheaper models (Claude Haiku, GPT-3.5) for preliminary screening
- Invoke expensive models only for disagreements
- Batch validation requests where possible

**Alternatives Considered**:
- **Single Model**: Rejected (unacceptable hallucination risk)
- **RAG Only**: Rejected (retrieval doesn't guarantee correctness)
- **Human Review**: Rejected (doesn't scale, defeats automation)

---

## ADR-003: Document-as-Database Pattern

**Status**: Accepted

**Context**:
Traditional approach: append-only markdown files proliferate, lose structure, contain redundancy and contradictions. Need single source of truth.

**Decision**:
- Store claims atomically in database with provenance
- Generate documents from database state (rendering layer)
- Never create duplicate documents (semantic deduplication)
- Update existing documents via structured sections
- Version documents like Git commits

**Rationale**:
- Database enforces consistency and relationships
- Claims linked to sources (provenance)
- Semantic search prevents duplication
- Structured updates preserve manual edits
- Version history enables rollback and diffs

**Trade-offs**:
✅ **Pros**:
- Single source of truth
- No duplicate documents
- Queryable knowledge base
- Provenance tracking built-in
- Version control for changes

❌ **Cons**:
- More complex than simple file writing
- Requires database schema design
- Document rendering adds layer
- Migration from file-based approaches difficult

**Implementation Pattern**:
```python
# Anti-pattern: Create new file
with open(f"research-{timestamp}.md", "w") as f:
    f.write(content)  # ❌ Proliferation

# Correct pattern: Update structured database
async with state_manager.transaction() as tx:
    existing = await find_existing_topic(query)
    if existing:
        await tx.update_claims(existing.id, new_claims)
    else:
        await tx.create_topic(title, new_claims)
    await synthesizer.render_document(topic)  # ✅ Single source
```

**Alternatives Considered**:
- **Append-Only Files**: Rejected (proliferation problem)
- **Wiki-Style**: Rejected (lacks structured provenance)
- **Graph DB Only**: Rejected (rendering complex, query performance)

---

## ADR-004: DAG-Based Task Queue

**Status**: Accepted

**Context**:
Research workflows have complex dependencies. Need to:
- Execute independent tasks in parallel
- Respect dependencies (task B waits for task A)
- Handle failures gracefully
- Track progress for long-running operations

**Decision**:
- Represent research plan as Directed Acyclic Graph (DAG)
- Tasks are nodes, dependencies are edges
- Topological sort determines execution order
- Tasks at same level execute in parallel
- Store task state in database for recovery

**Rationale**:
- DAG naturally models research dependencies
- Topological sort guarantees correct order
- Parallel execution within levels maximizes speed
- Database persistence enables recovery
- Industry-proven pattern (Airflow, Prefect)

**Trade-offs**:
✅ **Pros**:
- Maximum parallelism while respecting dependencies
- Clear visualization of workflow
- Fault tolerance (failed tasks retryable)
- Progress tracking per task

❌ **Cons**:
- More complex than sequential execution
- DAG creation overhead
- Deadlock detection needed (cycle prevention)
- Debugging parallel failures harder

**Example DAG**:
```
Research Query: "How do booking systems handle offline mode?"

Level 0 (Parallel):
├─ Task 1: Tavily search "offline-first architecture"
├─ Task 2: Context7 lookup "offline data sync"
└─ Task 3: Web scrape "PowerSync documentation"

Level 1 (Depends on Level 0):
└─ Task 4: Validate findings (all 3 inputs required)

Level 2 (Depends on Level 1):
├─ Task 5: Challenge analysis (parallel)
└─ Task 6: Synthesize document (parallel)

Level 3 (Depends on Level 2):
└─ Task 7: Archive and index
```

**Alternatives Considered**:
- **Sequential Execution**: Rejected (too slow for research)
- **Simple Parallel**: Rejected (can't handle dependencies)
- **Message Queue**: Rejected (overkill for single-process initially)

---

## ADR-005: A2A Protocol for Agent Communication

**Status**: Accepted

**Context**:
Multiple specialized agents need to coordinate. Need standard communication protocol for task delegation, result passing, error propagation.

**Decision**:
- Define A2A (Agent-to-Agent) message format
- JSON-serializable for portability
- Include trace IDs for debugging
- Support message types: task, result, error, query
- In-process message bus initially (migrate to RabbitMQ later)

**Rationale**:
- Standard format ensures interoperability
- Trace IDs enable distributed tracing
- Type system clarifies intent
- Message bus decouples agents (can scale later)

**Trade-offs**:
✅ **Pros**:
- Clean separation of concerns
- Agents independently developable
- Easy to add new agent types
- Migration path to distributed system

❌ **Cons**:
- Message serialization overhead
- More complex than direct function calls
- Requires message bus implementation
- Debugging message flow harder

**Message Format**:
```json
{
  "protocol_version": "a2a-v1",
  "message_id": "uuid",
  "from_agent": "coordinator",
  "to_agent": "researcher",
  "message_type": "task",
  "trace_id": "uuid",
  "timestamp": "2025-11-12T10:30:00Z",
  "payload": {
    "task_id": "uuid",
    "action": "web_search",
    "parameters": {...}
  }
}
```

**Alternatives Considered**:
- **Direct Function Calls**: Rejected (tight coupling, hard to scale)
- **REST APIs**: Rejected (overkill for in-process, latency)
- **gRPC**: Rejected (unnecessary complexity initially)

---

## ADR-006: Semantic Deduplication via Vector Embeddings

**Status**: Accepted

**Context**:
Users often ask similar questions in different words. Need to detect semantic similarity to prevent duplicate documents.

**Decision**:
- Generate embeddings for all topic queries (OpenAI text-embedding-3-small)
- Store embeddings in vector database (ChromaDB initially)
- Before creating topic, search for cosine similarity > 0.85
- If found, use UPDATE mode on existing topic
- If not found, create new topic

**Rationale**:
- Embeddings capture semantic meaning
- Cosine similarity robust similarity metric
- 0.85 threshold balances false positives/negatives
- ChromaDB lightweight, embeddable

**Trade-offs**:
✅ **Pros**:
- Prevents duplicate documents
- Works across different phrasings
- Fast similarity search (vector indexes)
- Extensible to claim-level deduplication

❌ **Cons**:
- Embedding API cost per query
- False positives possible (merges distinct topics)
- Requires embedding model dependency
- Vector DB adds complexity

**Threshold Tuning**:
- 0.90+: Very conservative (may create duplicates)
- 0.85: Balanced (recommended default)
- 0.80: Aggressive (may merge distinct topics)

**Example**:
```python
Query 1: "How do booking systems handle offline mode?"
Embedding 1: [0.234, -0.512, 0.891, ...]

Query 2: "What's the offline architecture for reservation software?"
Embedding 2: [0.221, -0.498, 0.875, ...]

Cosine Similarity: 0.92 → UPDATE existing topic ✅

Query 3: "Best practices for mobile app authentication"
Embedding 3: [-0.456, 0.723, -0.134, ...]

Cosine Similarity: 0.23 → CREATE new topic ✅
```

**Alternatives Considered**:
- **Keyword Matching**: Rejected (misses semantic similarity)
- **Manual User Decision**: Rejected (defeats automation)
- **No Deduplication**: Rejected (core problem we're solving)

---

## ADR-007: MCP Servers for External Tool Integration

**Status**: Accepted

**Context**:
Need web search, documentation lookup, browser automation, deep reasoning. Multiple tool providers available. Need consistent integration pattern.

**Decision**:
- Use MCP (Model Context Protocol) servers for external tools
- Implement generic MCP client with circuit breakers
- Specific clients for Tavily, Context7, Sequential, Playwright
- Fallback strategies when servers unavailable
- Configuration-driven server selection

**Rationale**:
- MCP provides standard interface across tools
- Circuit breakers prevent cascading failures
- Fallbacks ensure graceful degradation
- Configuration allows disabling expensive tools

**Trade-offs**:
✅ **Pros**:
- Clean abstraction over tools
- Easy to add new tools
- Consistent error handling
- Testable (mock MCP responses)

❌ **Cons**:
- Additional dependency on MCP servers
- Network calls for every tool invocation
- Server unavailability impacts functionality
- Configuration complexity

**Circuit Breaker Logic**:
```
State: CLOSED (normal operation)
  └─ Success → Stay CLOSED
  └─ Failure → Increment failure count
      └─ If count > threshold → Open circuit

State: OPEN (service down)
  └─ All requests fail fast
  └─ After timeout → Move to HALF_OPEN

State: HALF_OPEN (testing recovery)
  └─ Allow single test request
      └─ Success → Close circuit
      └─ Failure → Open circuit
```

**Fallback Chain**:
```
Tavily Search
  └─ (if unavailable) → Native WebSearch
      └─ (if unavailable) → Cached results
          └─ (if none) → Error with guidance

Context7 Docs
  └─ (if unavailable) → Tavily documentation search
      └─ (if unavailable) → General web search

Sequential Reasoning
  └─ (if unavailable) → Native Claude reasoning
      └─ (always available) → Continue
```

**Alternatives Considered**:
- **Direct API Calls**: Rejected (inconsistent error handling)
- **Monolithic Integration**: Rejected (tight coupling)
- **Plugin System**: Rejected (over-engineered for MVP)

---

## ADR-008: Rich CLI Output for LLM Consumption

**Status**: Accepted

**Context**:
Primary users are LLM agents (Claude Code, Gemini, Codex). Need machine-parseable output while remaining human-readable.

**Decision**:
- Output structured JSON by default
- Include status, results, warnings, next actions
- Use consistent field naming and structure
- Support `--format` flag for markdown/html alternatives
- Real-time progress via separate channel (stderr or log file)

**Rationale**:
- JSON parseable by LLMs without ambiguity
- Structured format enables programmatic workflows
- Consistent schema reduces parsing errors
- Human-readable JSON with proper formatting

**Trade-offs**:
✅ **Pros**:
- Perfect for LLM agent consumption
- Enables chaining ARIS with other tools
- Machine-verifiable output
- Easy to test output format

❌ **Cons**:
- Less human-friendly than plain text
- Verbose for simple queries
- Requires JSON parser for human viewing
- Multiple output formats add complexity

**Output Schema**:
```json
{
  "schema_version": "1.0",
  "command": "research",
  "status": "success",
  "result": {
    "topic": {...},
    "changes": {...},
    "validation": {...}
  },
  "warnings": [],
  "next_actions": [],
  "commands": {
    "view_document": "aris show path/to/doc.md"
  }
}
```

**Human-Friendly Alternative**:
```bash
aris research "query" --format markdown
# Outputs readable markdown instead of JSON
```

**Alternatives Considered**:
- **Plain Text**: Rejected (hard to parse reliably)
- **YAML**: Rejected (more complex than JSON for parsing)
- **XML**: Rejected (verbose, outdated)

---

## ADR-009: Async-First Architecture

**Status**: Accepted

**Context**:
Research involves many I/O operations: API calls, database queries, web scraping. Need non-blocking execution for performance.

**Decision**:
- Use asyncio as foundation
- All agents async (async def)
- Database operations async (aiosqlite, asyncpg)
- HTTP calls async (httpx)
- Parallel task execution with asyncio.gather

**Rationale**:
- Async maximizes I/O concurrency
- Python asyncio mature and stable
- Natural fit for web operations
- Enables efficient resource usage

**Trade-offs**:
✅ **Pros**:
- 10-100x speedup for I/O-bound tasks
- Efficient resource usage (single thread)
- Natural parallel execution model
- Non-blocking user experience

❌ **Cons**:
- Steeper learning curve
- Debugging async harder
- Must use async-compatible libraries
- Sync code requires thread pool wrapping

**Performance Example**:
```python
# Synchronous (slow)
def research_sequential(queries):
    results = []
    for q in queries:
        results.append(tavily_search(q))  # 2s each
    return results  # Total: 10s for 5 queries

# Asynchronous (fast)
async def research_parallel(queries):
    results = await asyncio.gather(*[
        tavily_search(q) for q in queries
    ])
    return results  # Total: 2s for 5 queries (parallel)
```

**Alternatives Considered**:
- **Threading**: Rejected (GIL limits, complex debugging)
- **Multiprocessing**: Rejected (IPC overhead, state sharing hard)
- **Synchronous**: Rejected (too slow for research workloads)

---

## ADR-010: Neo4j for Knowledge Graph (Optional Component)

**Status**: Accepted with Optionality

**Context**:
Need to discover relationships between topics, trace claim contradictions, find related research. Graph queries natural fit.

**Decision**:
- Use Neo4j for knowledge graph (optional component)
- Gracefully degrade if Neo4j unavailable
- Primary storage remains PostgreSQL
- Neo4j as enrichment layer for graph queries

**Rationale**:
- Neo4j purpose-built for graph queries
- Cypher query language intuitive
- Performant for relationship traversal
- Optional: system works without it

**Trade-offs**:
✅ **Pros**:
- Powerful relationship queries
- Visual graph exploration
- Native graph algorithms
- Industry standard for knowledge graphs

❌ **Cons**:
- Additional infrastructure (Docker/server)
- Learning curve for Cypher
- Data duplication (PostgreSQL + Neo4j)
- Sync complexity between stores

**Optional Degradation**:
```python
if neo4j_available():
    related = await graph_db.find_related_topics(topic_id, depth=2)
else:
    # Fallback: SQL joins (slower, less powerful)
    related = await state_manager.find_related_by_claims(topic_id)
```

**When to Enable**:
- Research corpus > 100 topics
- Need for complex relationship queries
- Graph visualization requirements
- Available infrastructure for Neo4j

**Alternatives Considered**:
- **NetworkX (in-memory)**: Rejected (doesn't persist, memory limits)
- **PostgreSQL Recursive CTEs**: Rejected (slower, less expressive)
- **No Graph Support**: Rejected (relationship queries valuable)

---

## ADR-011: Alembic for Database Migrations

**Status**: Accepted

**Context**:
Database schema will evolve. Need version-controlled, reversible migrations for production upgrades.

**Decision**:
- Use Alembic for schema migrations
- Auto-generate migrations from ORM models
- Manual review all generated migrations
- Test both upgrade and downgrade paths

**Rationale**:
- Industry standard for Python (used by SQLAlchemy)
- Version control for schema changes
- Reversible migrations (rollback support)
- Supports both SQLite and PostgreSQL

**Trade-offs**:
✅ **Pros**:
- Safe production upgrades
- Rollback capability
- Schema versioning
- Team collaboration (merge migrations)

❌ **Cons**:
- Learning curve for migration system
- Manual review required (auto-gen not perfect)
- Migration conflicts in team settings
- Testing overhead (up + down)

**Migration Workflow**:
```bash
# 1. Modify ORM models
# Edit aris/core/state_manager.py

# 2. Auto-generate migration
alembic revision --autogenerate -m "add claim_type field"

# 3. Review generated migration
# Edit migrations/versions/xxx_add_claim_type.py

# 4. Test upgrade
alembic upgrade head

# 5. Test downgrade
alembic downgrade -1

# 6. Commit migration to git
git add migrations/versions/xxx_add_claim_type.py
git commit -m "Add claim_type field to claims table"
```

**Alternatives Considered**:
- **Manual SQL Scripts**: Rejected (error-prone, no versioning)
- **ORM Auto-Create**: Rejected (destroys data, no rollback)
- **Django Migrations**: Rejected (not using Django)

---

## ADR-012: Progressive Implementation Strategy

**Status**: Accepted

**Context**:
Large system with 20-week timeline. Need to deliver value incrementally while maintaining quality.

**Decision**:
- 10 phases, each 2 weeks
- Each phase delivers working functionality
- Strict quality gates between phases
- Can deploy earlier phases before later ones complete

**Rationale**:
- Risk mitigation (fail fast on wrong approaches)
- Early validation with users
- Maintain motivation (regular "done" milestones)
- Flexibility to re-prioritize

**Trade-offs**:
✅ **Pros**:
- Working system from Phase 2 onward
- Can gather feedback early
- Reduces big-bang integration risk
- Flexibility to adjust priorities

❌ **Cons**:
- Some rework between phases
- Temptation to skip later phases
- Integration complexity if phases diverge
- Documentation must stay current

**Phase Dependencies**:
- **Must Complete in Order**: 1, 2, 3 (foundation)
- **Can Parallelize**: 4-7 (features)
- **Can Defer**: 8, 9 (polish)
- **Can Skip**: 10 (release, if internal only)

**Quality Gates**:
Each phase must pass:
1. All tests passing (>80% coverage)
2. No critical bugs
3. Documentation updated
4. Manual smoke test successful
5. Performance acceptable (no regressions)

**Alternatives Considered**:
- **Waterfall (Design All First)**: Rejected (risky, no validation)
- **Big Bang (One Release)**: Rejected (high risk, late feedback)
- **Continuous Delivery**: Rejected (too complex for initial MVP)

---

## Decision Summary Table

| ADR | Decision | Primary Rationale | Main Trade-off |
|-----|----------|-------------------|----------------|
| 001 | SQLite → PostgreSQL | Simple start, production path | Multiple DB testing |
| 002 | Multi-model consensus | Hallucination prevention | 3x API costs |
| 003 | Document-as-database | Single source of truth | Complexity vs files |
| 004 | DAG task queue | Parallel + dependencies | Complexity vs speed |
| 005 | A2A protocol | Agent decoupling | Message overhead |
| 006 | Vector embeddings | Semantic deduplication | Embedding API costs |
| 007 | MCP servers | Tool abstraction | Server dependencies |
| 008 | JSON CLI output | LLM parsing | Less human-friendly |
| 009 | Async-first | I/O performance | Debugging complexity |
| 010 | Neo4j (optional) | Graph queries | Additional infrastructure |
| 011 | Alembic migrations | Safe schema evolution | Migration overhead |
| 012 | Progressive phases | Risk mitigation | Some rework |

---

## Future ADRs to Consider

When implementing Phase 11+:

**ADR-013**: Distributed Agent Architecture (vs single-process)
**ADR-014**: Real-time Collaboration (vs single-user)
**ADR-015**: Web UI Framework (React, Vue, Svelte)
**ADR-016**: Authentication Strategy (OAuth, JWT, API keys)
**ADR-017**: Caching Layer (Redis, Memcached, in-memory)
**ADR-018**: Monitoring Platform (Prometheus, Datadog, Sentry)
**ADR-019**: Deployment Strategy (Docker, Kubernetes, Serverless)
**ADR-020**: Multi-Language Support (i18n strategy)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-12 | Initial ADRs | Backend Architect |

---

## References

- [Architectural Decision Records](https://adr.github.io/)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)
- [Async Python Best Practices](https://docs.python.org/3/library/asyncio-dev.html)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Semantic Similarity](https://platform.openai.com/docs/guides/embeddings)
