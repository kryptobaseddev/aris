# ARIS - Autonomous Research Intelligence System

**Version**: MVP 1.0.0 (Requirements Phase)
**Status**: MVP Requirements Complete, Implementation Ready
**License**: MIT
**Timeline**: 12 weeks to working prototype

---

## Overview

ARIS is a research orchestration system that solves **document proliferation** by intelligently updating existing documents instead of creating duplicates.

**Problem**: LLM agents create new documents for similar queries, causing fragmentation and context loss

**Solution**: Semantic deduplication + multi-model validation + intelligent document updates

**MVP Scope**: Single-agent architecture with role-switching (NOT 6 separate agents)

---

## Core Value Proposition

**Traditional Approach**:
Query → Research → Create New Document → Repeat → 10+ duplicate documents ❌

**ARIS Approach**:
Query → Semantic Search (>0.85 similarity?) → UPDATE existing document ✅

**Result**: Consolidated research, validated information, persistent context, reduced API costs

---

## MVP Innovations (Simplified)

- **Semantic Deduplication**: Vector similarity search (>0.85 = UPDATE mode)
- **Multi-Model Consensus**: 2+ LLMs validate claims (Anthropic + OpenAI minimum)
- **Intelligent Updates**: Section merging with Git-based version history
- **Single Agent**: Role-switching (Coordinator → Researcher → Validator → Synthesizer)
- **Cost Optimization**: Target <$0.50 per query with tracking
- **MCP Integration**: Tavily (search), Sequential (reasoning), Serena (memory)

---

## Simplified MVP Architecture

```
┌─────────────────────────────────────────────────┐
│              ARIS CLI (Click + Rich)            │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         Single Agent (Role-Switching)           │
│  Coordinator → Researcher → Validator → Synth   │
└─────────────────────────────────────────────────┘
                        ↓
┌────────────────┬────────────────┬───────────────┐
│ MCP Servers    │ Validation     │ Storage       │
│ • Tavily       │ • Claude       │ • SQLite      │
│ • Sequential   │ • GPT-4        │ • Git         │
│ • Serena       │ (2+ models)    │ • Embeddings  │
└────────────────┴────────────────┴───────────────┘
```

**Key Simplification**: 1 agent with 4 modes (NOT 6 separate agents, NO A2A protocol, NO Neo4j)

---

## Technology Stack (MVP)

**Core**:
- Python 3.11+ (async/await for I/O concurrency)
- Click (CLI framework) + Rich (terminal formatting)
- Pydantic (data validation)
- SQLite with FTS5 (full-text search)

**Persistence**:
- SQLite (embedded database, no PostgreSQL for MVP)
- Git via GitPython (version history, rollback)
- Vector embeddings (OpenAI or Anthropic APIs)

**External APIs**:
- Anthropic Claude (validation)
- OpenAI GPT-4 (validation + embeddings)
- Tavily (web search MCP)
- Sequential (reasoning MCP)
- Serena (memory MCP)

---

## Documentation

### MVP Requirements (START HERE)

1. **[MVP-Requirements-Specification.md](docs/MVP-Requirements-Specification.md)** - Complete MVP requirements
   - 12 user stories in 6 epics
   - Acceptance criteria (5 per story)
   - Non-functional requirements (Performance, Reliability, Security, Scalability, Usability)
   - Success metrics (8 metrics with targets and thresholds)
   - 12-week implementation timeline
   - Scope boundaries (IN vs. OUT)
   - Risk assessment and mitigation

2. **[MVP-Quick-Reference.md](docs/MVP-Quick-Reference.md)** - Visual summary and cheat sheet
   - Core value proposition
   - Simplified architecture diagram
   - 12 user stories at-a-glance
   - Success metrics table
   - 12-week timeline breakdown
   - Technology stack
   - Quick commands reference

3. **[Requirements-Validation-Checklist.md](docs/Requirements-Validation-Checklist.md)** - Requirements verification
   - All 6 verification criteria validated
   - Evidence for each requirement
   - Quality checks passed
   - Approval recommendation

### Original Architecture (Reference Only)

**Note**: The following documents describe the ORIGINAL 20-week architecture with 6 agents. See MVP requirements above for the SIMPLIFIED 12-week single-agent approach.

4. **[ARIS-Architecture-Blueprint.md](claudedocs/ARIS-Architecture-Blueprint.md)** (55KB) - Original design
5. **[Implementation-Checklist.md](claudedocs/Implementation-Checklist.md)** (25KB) - Original 20-week plan
6. **[Architectural-Decisions.md](claudedocs/Architectural-Decisions.md)** (22KB) - Original ADRs
7. **[Quick-Reference.md](claudedocs/Quick-Reference.md)** (16KB) - Original quick ref

---

## Current Status

**Phase**: MVP Requirements Complete ✅
**Next Step**: Week 1-2 Implementation (Foundation)

**Requirements Validation**:
- ✅ 12 user stories covering core workflows
- ✅ Clear acceptance criteria (5 per story)
- ✅ Scope boundaries defined (IN/OUT)
- ✅ Non-functional requirements specified
- ✅ Success metrics defined (8 metrics)
- ✅ User personas identified

---

## MVP Scope: IN vs. OUT

### ✅ IN SCOPE (MVP v1.0)

1. Semantic deduplication (vector similarity search)
2. Single-agent architecture with role-switching
3. Basic multi-model consensus validation (2+ models)
4. Document update vs. create logic
5. Git-based version history
6. SQLite persistence layer
7. MCP integration (Tavily, Sequential, Serena)
8. CLI interface with structured output
9. Basic provenance tracking (sources per claim)
10. Cost tracking and optimization

### ❌ OUT OF SCOPE (Post-MVP)

1. Multi-agent coordination (A2A protocol)
2. Neo4j knowledge graph
3. DAG task queue with parallel execution
4. Challenger agent (critical analysis)
5. Archivist agent (advanced indexing)
6. Real-time streaming updates
7. Web UI (CLI only for MVP)
8. Multi-user collaboration
9. Cloud deployment support
10. PostgreSQL migration path

---

## Design Principles

**Reliability**:
- Multi-model consensus prevents hallucinations
- Transactional state updates with rollback
- Circuit breakers for external API failures
- Comprehensive audit trails

**Data Integrity**:
- Document versioning with Git-like diffs
- Atomic claim validation before persistence
- Conflict detection and resolution
- Source authentication and authority scoring

**Performance**:
- Async-first architecture (asyncio)
- Parallel task execution via DAG
- Semantic caching with vector embeddings
- Connection pooling for database and HTTP

**Security**:
- API key management via system keyring
- Rate limiting for external APIs
- Input sanitization for all queries
- Audit logging for all state mutations

---

## MVP Implementation Timeline

**12 Weeks Total** (6 phases × 2 weeks each):

- **Week 1-2**: Foundation (Data models, SQLite schema, CLI skeleton, Git integration)
- **Week 3-4**: Research Workflow (Orchestrator, MCP clients, basic execution)
- **Week 5-6**: Semantic Deduplication (Embeddings, similarity search, UPDATE/CREATE logic)
- **Week 7-8**: Multi-Model Validation (Consensus engine, cost tracking, confidence scoring)
- **Week 9-10**: Document Updates (Section merging, document parsing, Git automation)
- **Week 11**: Session Persistence (Project context, research history, Serena integration)
- **Week 12**: Polish & Testing (Terminal output, configuration, end-to-end tests, documentation)

**Working System Available**: After Week 4 (Basic research workflow)

---

## Success Metrics (3-Month Validation)

| Metric | Target | Threshold |
|--------|--------|-----------|
| M1: Deduplication accuracy | >95% | >90% |
| M2: Cost per query | <$0.50 | <$0.75 |
| M3: Query completion time | <30s (80%) | <45s (80%) |
| M4: Validation confidence | >0.85 avg | >0.75 avg |
| M5: User satisfaction | >4.5/5 | >4.0/5 |
| M6: Document consolidation | 50% reduction | 30% reduction |
| M7: Context retention | 90% resume | 80% resume |
| M8: Error rate | <2% | <5% |

---

## Key MVP Decisions

1. **Single Agent Architecture**: Role-switching instead of 6 specialized agents
2. **SQLite Only**: No PostgreSQL migration path for MVP
3. **Git for History**: No Neo4j knowledge graph for MVP
4. **Sequential Workflow**: No DAG task queue for MVP
5. **2+ Model Validation**: Minimum viable consensus (not 3+ models)
6. **Vector Embeddings**: OpenAI or Anthropic APIs (semantic deduplication)
7. **MCP Integration**: Tavily, Sequential, Serena only (not Context7/Playwright)
8. **JSON CLI Output**: LLM-agent friendly structured format
9. **Cost Optimization**: <$0.50 per query target with tracking
10. **12-Week Timeline**: MVP-first approach (not 20-week full system)

See [MVP-Requirements-Specification.md](docs/MVP-Requirements-Specification.md) for complete rationale.

---

## System Requirements (MVP)

**Development**:
- Python 3.11+
- 2GB RAM
- 500MB disk space
- Internet connection (API access)

**User Environment**:
- Python 3.11+
- 4GB RAM
- 2GB disk space (1,000 documents max)
- API keys: Anthropic, OpenAI, Tavily
- macOS, Linux, or Windows (WSL)

---

## Configuration Example (MVP)

```yaml
# ~/.aris/config.yaml
database:
  type: sqlite
  path: ./data/aris.db

deduplication:
  similarity_threshold: 0.85
  embedding_provider: openai

consensus:
  threshold: 0.7
  models:
    - anthropic/claude-sonnet-4-5
    - openai/gpt-4-turbo

cost:
  max_per_query: 0.50
  warn_threshold: 0.40

mcp_servers:
  tavily: {search_depth: advanced}
  sequential: {enabled: true}
  serena: {enabled: true}
```

---

## CLI Usage (Planned)

```bash
# Initialize project
aris init --project my-research

# Execute research
aris research "How do booking systems handle offline mode?"

# Output (JSON)
{
  "status": "success",
  "mode": "update",
  "topic": {
    "id": "uuid-123",
    "title": "Booking Systems Offline Architecture",
    "confidence": 0.91,
    "document_path": "research/booking-offline.md",
    "matched_document": {
      "title": "Booking Systems Architecture (v2.3)",
      "similarity_score": 0.89,
      "last_updated": "2025-11-10"
    }
  },
  "changes": {
    "lines_added": 47,
    "lines_removed": 12,
    "sections_updated": ["Architecture", "Offline Mode"],
    "git_commit": "abc123def"
  },
  "validation": {
    "claims_validated": 12,
    "consensus_score": 0.91,
    "low_confidence_claims": 1,
    "sources_count": 5
  },
  "cost": {
    "total": 0.42,
    "breakdown": {
      "embeddings": 0.05,
      "research": 0.15,
      "validation": 0.22
    }
  },
  "execution_time": "28.5s"
}

# View document
aris show research/booking-offline.md

# Check system status
aris status

# View history
aris history

# Show changes
aris diff <doc> --version A:B

# Rollback changes
aris rollback <doc> --to <commit>

# Configure
aris config set max_cost 0.50
```

---

## Project Structure (MVP)

```
aris-tool/
├── aris/                      # Main package
│   ├── core/
│   │   ├── orchestrator.py    # Main entry point, CLI routing
│   │   ├── agent.py           # Single agent with role-switching
│   │   ├── state_manager.py   # SQLite persistence
│   │   └── consensus.py       # Multi-model validation
│   ├── integrations/
│   │   ├── mcp_client.py      # Base MCP client
│   │   ├── tavily_client.py   # Web search
│   │   ├── sequential_client.py # Reasoning
│   │   └── serena_client.py   # Memory/project context
│   ├── knowledge/
│   │   ├── vector_store.py    # Embedding-based similarity
│   │   ├── document.py        # Document parsing/merging
│   │   └── provenance.py      # Source tracking
│   ├── models/
│   │   ├── topic.py           # Research topic model
│   │   ├── claim.py           # Atomic fact model
│   │   └── source.py          # Provenance model
│   └── utils/
│       ├── config.py          # Configuration management
│       ├── cost_tracker.py    # API cost monitoring
│       └── git_manager.py     # Git operations
├── tests/                     # Unit + integration tests
├── docs/                      # MVP requirements documentation
├── claudedocs/                # Original architecture (reference)
├── data/                      # Runtime data (gitignored)
└── pyproject.toml             # Poetry dependencies
```

---

## Quality Standards (MVP)

**Test Coverage**:
- Core modules: 80%+
- Integrations: 60%+ (mocked externals)
- End-to-end: 10+ realistic scenarios

**Code Quality**:
- Formatter: Black (line length 100)
- Linter: Ruff (strict mode)
- Type Checker: mypy (strict mode)
- Docstrings: Google style

---

## Contributing

This project is currently in the architecture phase. Implementation will follow the detailed roadmap in the documentation.

**Development Setup** (future):
```bash
git clone https://github.com/user/aris-tool.git
cd aris-tool
poetry install
poetry run pre-commit install
poetry run pytest
```

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

**Design Inspiration**:
- Airflow (DAG task orchestration)
- Alembic (database migrations)
- MCP Protocol (tool integration standard)
- SuperClaude Framework (agent coordination patterns)

**Technology Credits**:
- Anthropic Claude (consensus validation)
- OpenAI GPT (consensus validation)
- Google Gemini (consensus validation)
- Tavily (web search API)
- Context7 (technical documentation)

---

## Contact

**Project Status**: MVP Requirements Complete, Implementation Ready
**Documentation**: See `/docs/` for MVP requirements, `/claudedocs/` for original architecture

**For MVP Requirements**: Refer to [MVP-Requirements-Specification.md](docs/MVP-Requirements-Specification.md)
**For Quick Reference**: Refer to [MVP-Quick-Reference.md](docs/MVP-Quick-Reference.md)
**For Requirements Validation**: Refer to [Requirements-Validation-Checklist.md](docs/Requirements-Validation-Checklist.md)

---

## Next Steps

1. **Review MVP requirements** - Read [MVP-Requirements-Specification.md](docs/MVP-Requirements-Specification.md)
2. **Understand scope** - Review IN vs. OUT scope in this README
3. **Week 1-2 implementation** - Begin Foundation phase (data models, SQLite, CLI)
4. **Cost validation** - Validate <$0.50 per query target EARLY
5. **Deduplication testing** - Test similarity threshold on real queries

---

**Built with MVP principles**: Simplest system that proves core value proposition, 12-week timeline, cost-optimized architecture.
