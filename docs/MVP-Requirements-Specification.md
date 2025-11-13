# ARIS MVP Requirements Specification

**Version**: 1.0.0
**Date**: 2025-11-12
**Status**: Requirements Definition Phase
**Target Timeline**: 12 weeks to working prototype

---

## Executive Summary

ARIS (Autonomous Research Intelligence System) MVP solves **document proliferation** in LLM-based research workflows by implementing semantic deduplication and intelligent document updates instead of creating duplicate files.

**Core Value Proposition**: Research agents that UPDATE existing documents instead of creating duplicates, with validation layers to ensure quality.

**MVP Success Criteria**: Cost <$0.50 per research query, <30s query execution time, >95% deduplication accuracy.

---

## 1. Problem Statement

### Current Pain Points

**Problem 1: Document Proliferation**
- LLM agents create new documents for similar queries
- No semantic search for existing research
- Result: 10+ documents on same topic with fragmented information

**Problem 2: Session Context Loss**
- Research context doesn't persist across conversations
- Repeated work with no memory of prior research
- Result: Wasted API costs and user frustration

**Problem 3: No Validation Layer**
- Single LLM outputs accepted without verification
- Hallucinations proliferate into documentation
- Result: Unreliable research artifacts

**Problem 4: No Update Mechanism**
- Existing documents ignored during research
- Information becomes stale and outdated
- Result: Fragmented knowledge base

### Root Cause Analysis

All problems stem from: **Stateless, append-only agent workflows**

Traditional approach: Query → Research → Create New Document → Disconnect

ARIS approach: Query → Semantic Search → Research → Validate → Update/Create → Archive

---

## 2. User Personas

### Primary Persona: Claude Code User (Research Context)

**Profile**:
- Uses Claude Code for development and research
- Accumulates research documents across sessions
- Values context continuity and cost efficiency
- Technical literacy: High

**Use Cases**:
1. Technical architecture research for projects
2. Competitive analysis and market research
3. Framework/library evaluation and selection
4. Problem-solving investigations

**Pain Points**:
- Duplicate research documents clutter workspace
- Lost context between sessions
- Uncertain about information accuracy
- API costs accumulate with redundant queries

**Success Metrics**:
- Documents remain current and consolidated
- Research context persists across sessions
- High confidence in accuracy of information
- Reduced API costs through deduplication

---

## 3. MVP Scope Definition

### IN SCOPE (MVP v1.0)

**Core Features**:
1. ✅ Semantic deduplication (vector similarity search)
2. ✅ Single-agent architecture with role-switching
3. ✅ Basic multi-model consensus validation (2+ models)
4. ✅ Document update vs. create logic
5. ✅ Git-based version history
6. ✅ SQLite persistence layer
7. ✅ MCP integration (Tavily, Sequential, Serena)
8. ✅ CLI interface with structured output
9. ✅ Basic provenance tracking (sources per claim)
10. ✅ Cost tracking and optimization

**Simplified Architecture**:
- Single agent with role modes (Coordinator, Researcher, Validator, Synthesizer)
- No A2A protocol (not needed for single agent)
- No Neo4j (Git + SQLite sufficient)
- No DAG task queue (simple sequential workflow)
- No Challenger/Archivist agents (future enhancement)

### OUT OF SCOPE (Post-MVP)

**Deferred Features**:
- ❌ Multi-agent coordination (A2A protocol)
- ❌ Neo4j knowledge graph
- ❌ DAG task queue with parallel execution
- ❌ Challenger agent (critical analysis)
- ❌ Archivist agent (advanced indexing)
- ❌ Real-time streaming updates
- ❌ Web UI (CLI only for MVP)
- ❌ Multi-user collaboration
- ❌ Cloud deployment support
- ❌ PostgreSQL migration path

**Why Deferred**:
- Each adds significant complexity
- Not required to prove core value proposition
- Can be validated through MVP user feedback
- Allows 12-week timeline vs. 20-week

### Explicit Boundaries

**MVP Delivers**:
- Working system for single-user local research
- Proof of concept for semantic deduplication
- Validation of cost/performance targets
- Foundation for future enhancements

**MVP Does NOT Deliver**:
- Production-ready multi-user system
- Enterprise scalability
- Real-time collaborative research
- Advanced graph analytics

---

## 4. User Stories

### Epic 1: Semantic Deduplication

**US-001: Prevent Duplicate Documents**

**As a** Claude Code user
**I want** ARIS to search existing documents before creating new ones
**So that** I avoid document proliferation and fragmented information

**Acceptance Criteria**:
- AC1: System performs vector similarity search on query
- AC2: Documents with >0.85 similarity trigger UPDATE mode
- AC3: Documents with <0.85 similarity trigger CREATE mode
- AC4: User receives notification about mode selection
- AC5: False positive rate <5% (manual validation on 100 queries)

**Priority**: Critical
**Effort**: 8 points
**Dependencies**: Vector embeddings, document database

---

**US-002: Intelligent Mode Selection**

**As a** Claude Code user
**I want** ARIS to explain why it chose UPDATE vs. CREATE mode
**So that** I can validate the decision makes sense

**Acceptance Criteria**:
- AC1: System outputs similarity score in CLI response
- AC2: System shows matched document title and excerpt
- AC3: User can override with `--force-create` or `--force-update` flags
- AC4: Override decisions logged for analysis

**Priority**: High
**Effort**: 3 points
**Dependencies**: US-001

---

### Epic 2: Multi-Model Validation

**US-003: Consensus Validation**

**As a** Claude Code user
**I want** research claims validated by multiple LLMs
**So that** I can trust the accuracy of information

**Acceptance Criteria**:
- AC1: System queries 2+ LLMs for claim validation (Anthropic + OpenAI minimum)
- AC2: Consensus score calculated (agreement / total models)
- AC3: Claims with consensus <0.7 flagged as "low confidence"
- AC4: Low confidence claims marked in output document
- AC5: Validation results stored with claim provenance

**Priority**: Critical
**Effort**: 13 points
**Dependencies**: Multi-model API integration

---

**US-004: Cost-Aware Validation**

**As a** Claude Code user
**I want** validation to respect cost budgets
**So that** I don't exceed my API spending limits

**Acceptance Criteria**:
- AC1: System tracks API costs per query
- AC2: User can set max cost per query (e.g., `--max-cost 0.50`)
- AC3: System stops validation if budget would be exceeded
- AC4: Cost breakdown shown in CLI output (per model, per operation)
- AC5: Cost logs persisted for analysis

**Priority**: High
**Effort**: 5 points
**Dependencies**: US-003

---

### Epic 3: Document Update Logic

**US-005: Intelligent Section Merging**

**As a** Claude Code user
**I want** ARIS to merge new findings into existing documents intelligently
**So that** information is organized logically without duplication

**Acceptance Criteria**:
- AC1: System identifies relevant sections in existing document
- AC2: New information merged into appropriate sections
- AC3: Outdated information flagged for review (not auto-deleted)
- AC4: Merge logic preserves document structure (headings, lists)
- AC5: Merge preview shown before applying changes

**Priority**: Critical
**Effort**: 13 points
**Dependencies**: US-001, Document parsing

---

**US-006: Git-Based Version History**

**As a** Claude Code user
**I want** document changes tracked in Git
**So that** I can review history and rollback if needed

**Acceptance Criteria**:
- AC1: Each document update creates a Git commit
- AC2: Commit messages include query context and changes summary
- AC3: User can run `aris diff <doc> --version A:B` to see changes
- AC4: User can run `aris rollback <doc> --to <commit>` to revert
- AC5: Git history includes metadata (costs, validation scores)

**Priority**: High
**Effort**: 8 points
**Dependencies**: Git integration, US-005

---

### Epic 4: Research Workflow

**US-007: Simple Research Query**

**As a** Claude Code user
**I want** to execute a research query with a single command
**So that** I can quickly gather validated information

**Acceptance Criteria**:
- AC1: Command: `aris research "query text"`
- AC2: System completes in <30 seconds for simple queries
- AC3: Output includes document path and changes summary
- AC4: CLI output is structured JSON for LLM parsing
- AC5: Errors reported clearly with actionable guidance

**Priority**: Critical
**Effort**: 5 points
**Dependencies**: Core orchestrator, MCP integration

---

**US-008: MCP Integration for Research**

**As a** Claude Code user
**I want** ARIS to leverage MCP servers for research
**So that** I get high-quality information from trusted sources

**Acceptance Criteria**:
- AC1: Tavily integration for web search
- AC2: Sequential integration for complex reasoning
- AC3: Serena integration for project memory
- AC4: Each MCP call has timeout and retry logic
- AC5: MCP failures logged but don't crash system

**Priority**: High
**Effort**: 8 points
**Dependencies**: MCP client library

---

### Epic 5: Session Persistence

**US-009: Project Context Memory**

**As a** Claude Code user
**I want** ARIS to remember project context across sessions
**So that** I don't lose research continuity

**Acceptance Criteria**:
- AC1: Command: `aris init --project <name>` creates project
- AC2: Project stores: documents, embeddings, validation history
- AC3: Command: `aris status` shows project overview
- AC4: Context automatically loaded when working in project directory
- AC5: Multiple projects supported without conflicts

**Priority**: High
**Effort**: 8 points
**Dependencies**: SQLite schema, Serena integration

---

**US-010: Research History Tracking**

**As a** Claude Code user
**I want** to see my research history and patterns
**So that** I can understand my knowledge evolution

**Acceptance Criteria**:
- AC1: Command: `aris history` shows recent queries
- AC2: Command: `aris history <doc>` shows document evolution
- AC3: History includes: query, timestamp, cost, confidence score
- AC4: History searchable by keyword or date range
- AC5: History exportable to CSV for analysis

**Priority**: Medium
**Effort**: 5 points
**Dependencies**: US-009

---

### Epic 6: CLI User Experience

**US-011: Rich Terminal Output**

**As a** Claude Code user
**I want** clear, visual progress indicators
**So that** I know what ARIS is doing during execution

**Acceptance Criteria**:
- AC1: Progress bars for long operations (research, validation)
- AC2: Color-coded status messages (success=green, error=red, info=blue)
- AC3: Real-time status updates (e.g., "Searching Tavily...")
- AC4: Structured JSON output for LLM consumption
- AC5: `--quiet` flag for minimal output

**Priority**: Medium
**Effort**: 5 points
**Dependencies**: Rich library integration

---

**US-012: Configuration Management**

**As a** Claude Code user
**I want** to configure ARIS behavior easily
**So that** I can customize it to my workflow

**Acceptance Criteria**:
- AC1: Config file: `~/.aris/config.yaml`
- AC2: Settings: API keys, cost limits, similarity thresholds, model preferences
- AC3: Command: `aris config set <key> <value>`
- AC4: Command: `aris config get <key>`
- AC5: Environment variables override config file

**Priority**: High
**Effort**: 3 points
**Dependencies**: Config parser

---

## 5. Non-Functional Requirements

### Performance

**NFR-P1: Query Execution Time**
- Simple queries (1 source): <30 seconds
- Complex queries (3+ sources): <2 minutes
- Validation per claim: <5 seconds
- **Rationale**: User responsiveness threshold

**NFR-P2: Database Operations**
- Vector similarity search: <100ms
- Document retrieval: <50ms
- Git operations: <200ms
- **Rationale**: CLI responsiveness

**NFR-P3: Cost Efficiency**
- Target: <$0.50 per research query
- Maximum: <$1.00 per research query (fallback models)
- **Rationale**: Sustainable for individual users

### Reliability

**NFR-R1: Error Handling**
- All MCP calls wrapped in try/catch with retries (3 attempts, exponential backoff)
- Network failures don't corrupt database
- Partial results saved before errors
- **Validation**: 100% error scenarios covered by tests

**NFR-R2: Data Integrity**
- All database writes atomic (SQLite transactions)
- Git commits always succeed or rollback
- No orphaned records or corrupted embeddings
- **Validation**: Database consistency checks in test suite

**NFR-R3: Uptime**
- CLI commands succeed >99% of time (excluding external API failures)
- Graceful degradation when MCP servers unavailable
- **Validation**: Chaos testing with MCP server failures

### Scalability

**NFR-S1: Document Capacity**
- MVP supports <1,000 documents per project
- Vector search remains <100ms at 1,000 documents
- **Rationale**: Single-user local research scope

**NFR-S2: Concurrent Operations**
- MVP supports 1 user, 1 active query
- No concurrent query support required
- **Rationale**: CLI tool for individual users

### Security

**NFR-SE1: API Key Management**
- Keys stored in system keyring (not config files)
- Keys never logged or echoed to terminal
- **Validation**: Manual security audit of codebase

**NFR-SE2: Input Sanitization**
- All user inputs sanitized before SQL queries
- No arbitrary code execution from user input
- **Validation**: SQL injection testing

### Usability

**NFR-U1: Installation**
- Single command: `pip install aris-tool`
- No complex dependencies or setup
- Works on macOS, Linux, Windows (WSL)
- **Validation**: Fresh environment installation tests

**NFR-U2: Documentation**
- CLI help text for all commands
- Quickstart guide for first-time users
- Troubleshooting guide for common errors
- **Validation**: User testing with new users

---

## 6. Technical Constraints

### Required Technologies

**Language**: Python 3.11+ (async/await, type hints)
**Database**: SQLite with FTS5 (full-text search)
**Version Control**: Git via GitPython library
**CLI Framework**: Click + Rich (terminal formatting)
**Vector Embeddings**: OpenAI or Anthropic embedding APIs
**MCP Servers**: Tavily (search), Sequential (reasoning), Serena (memory)

### API Dependencies

**Required**:
- Anthropic API (Claude for validation)
- OpenAI API (GPT for validation + embeddings)
- Tavily API (web search)

**Optional**:
- Google Gemini API (additional validation)
- Context7 API (technical documentation)

### Environment Requirements

**Development**:
- Python 3.11+
- 2GB RAM
- 500MB disk space
- Internet connection

**Production** (user environment):
- Python 3.11+
- 4GB RAM
- 2GB disk space (1,000 documents)
- Internet connection

---

## 7. Success Metrics

### 3-Month Validation Period (Post-MVP)

**Primary Metrics**:

**M1: Deduplication Accuracy**
- Target: >95% of duplicate queries correctly routed to UPDATE mode
- Measurement: Manual review of 100 consecutive queries
- Success Threshold: >90% accuracy

**M2: Cost Per Query**
- Target: <$0.50 average (including validation)
- Measurement: Cost tracking logs over 3 months
- Success Threshold: <$0.75 average

**M3: Query Completion Time**
- Target: <30s for 80% of queries
- Measurement: Execution time logs
- Success Threshold: <45s for 80% of queries

**M4: Validation Confidence**
- Target: >0.85 average consensus score
- Measurement: Validation logs over 3 months
- Success Threshold: >0.75 average

**M5: User Satisfaction**
- Target: >4.5/5 user rating
- Measurement: User survey (5-point scale)
- Success Threshold: >4.0/5

**Secondary Metrics**:

**M6: Document Consolidation**
- Target: 50% reduction in duplicate documents vs. baseline
- Measurement: Before/after document count analysis
- Success Threshold: 30% reduction

**M7: Context Retention**
- Target: 90% of sessions successfully resume prior context
- Measurement: Session continuity logs
- Success Threshold: 80% successful resumption

**M8: Error Rate**
- Target: <2% of queries fail with unhandled errors
- Measurement: Error logs over 3 months
- Success Threshold: <5% error rate

---

## 8. Acceptance Criteria (MVP Completion)

MVP is considered **COMPLETE** when:

1. ✅ All 12 user stories implemented and tested
2. ✅ Test coverage >80% (unit + integration)
3. ✅ All NFRs validated through testing
4. ✅ CLI commands functional and documented
5. ✅ Quickstart guide written and tested
6. ✅ 10+ manual end-to-end test scenarios pass
7. ✅ Cost per query <$0.75 validated on test dataset
8. ✅ Deduplication accuracy >90% validated on test dataset
9. ✅ Installation works on fresh macOS/Linux environments
10. ✅ Architecture document updated to reflect MVP simplifications

---

## 9. Risk Assessment

### High Risks

**R1: API Costs Exceed Target**
- **Probability**: Medium
- **Impact**: High (unsustainable for users)
- **Mitigation**: Implement cost tracking early, optimize validation logic, cache embeddings
- **Contingency**: Single-model validation fallback

**R2: Deduplication False Positives**
- **Probability**: Medium
- **Impact**: High (incorrect updates corrupt documents)
- **Mitigation**: Conservative similarity threshold (0.85), user override flags, Git rollback
- **Contingency**: Manual review mode for borderline cases

**R3: MCP Server Reliability**
- **Probability**: Low
- **Impact**: Medium (degraded functionality)
- **Mitigation**: Retry logic, circuit breakers, graceful fallbacks
- **Contingency**: Native search APIs (non-MCP) as fallback

### Medium Risks

**R4: SQLite Performance at Scale**
- **Probability**: Low
- **Impact**: Medium (slow queries >500 documents)
- **Mitigation**: Proper indexing, FTS5 optimization, document archival
- **Contingency**: Document limit warnings, archive old documents

**R5: Git Repository Growth**
- **Probability**: Medium
- **Impact**: Low (disk space growth)
- **Mitigation**: Git compression, periodic garbage collection
- **Contingency**: User-triggered cleanup commands

---

## 10. MVP Implementation Timeline

### 12-Week Schedule

**Week 1-2: Foundation**
- Core data models (Pydantic)
- SQLite schema and migrations
- Basic CLI structure (Click)
- Git integration setup
- **Deliverable**: Working database + CLI skeleton

**Week 3-4: Research Workflow**
- Single-agent orchestrator
- MCP client integration (Tavily, Sequential, Serena)
- Basic research execution (no validation)
- **Deliverable**: End-to-end research flow (US-007)

**Week 5-6: Semantic Deduplication**
- Vector embeddings generation
- Similarity search implementation
- UPDATE vs. CREATE mode logic
- **Deliverable**: Deduplication working (US-001, US-002)

**Week 7-8: Multi-Model Validation**
- Consensus validation engine
- Cost tracking system
- Low confidence flagging
- **Deliverable**: Validation layer complete (US-003, US-004)

**Week 9-10: Document Updates**
- Section merging logic
- Document parsing and manipulation
- Git commit automation
- **Deliverable**: Intelligent updates working (US-005, US-006)

**Week 11: Session Persistence**
- Project context management
- Research history tracking
- Serena integration
- **Deliverable**: Context continuity (US-009, US-010)

**Week 12: Polish & Testing**
- Rich terminal output
- Configuration management
- End-to-end testing
- Documentation writing
- **Deliverable**: MVP complete (US-011, US-012)

---

## 11. Validation Plan

### Testing Strategy

**Unit Tests**:
- All core functions (orchestrator, deduplication, validation)
- Target coverage: 80%+
- Run on every commit (CI/CD)

**Integration Tests**:
- MCP server interactions (mocked)
- Database operations (real SQLite)
- Git operations (temporary repos)
- Target coverage: 60%+

**End-to-End Tests**:
- 10+ realistic research scenarios
- Manual execution with validation
- Covers: CREATE mode, UPDATE mode, validation, history

**Performance Tests**:
- Query execution time benchmarks
- Vector search performance
- Database query latency
- Cost per query measurements

**User Acceptance Testing**:
- 3-5 beta users
- 2-week testing period
- Structured feedback collection
- Metrics validation (M1-M8)

---

## 12. Dependencies Map

### Critical Path

```
Week 1-2: Foundation
    ↓
Week 3-4: Research Workflow
    ↓
Week 5-6: Deduplication ← Blocks UPDATE mode
    ↓
Week 7-8: Validation ← Blocks quality confidence
    ↓
Week 9-10: Document Updates ← Blocks core value prop
    ↓
Week 11: Session Persistence ← Enhances but not blocking
    ↓
Week 12: Polish & Testing
```

### User Story Dependencies

```
US-001 (Deduplication)
    → US-002 (Mode Selection)
    → US-005 (Section Merging)
    → US-006 (Version History)

US-003 (Consensus Validation)
    → US-004 (Cost-Aware)

US-007 (Research Query)
    → US-008 (MCP Integration)

US-009 (Project Context)
    → US-010 (Research History)

US-011 (Terminal Output) ← Independent
US-012 (Configuration) ← Independent
```

---

## 13. Open Questions

**Q1**: Should MVP support configurable similarity thresholds?
- **Decision Needed By**: Week 5
- **Options**: (A) Hardcoded 0.85, (B) User-configurable
- **Recommendation**: (A) for MVP simplicity

**Q2**: Which embedding provider should be default?
- **Decision Needed By**: Week 5
- **Options**: (A) OpenAI, (B) Anthropic
- **Recommendation**: (A) OpenAI (more stable API)

**Q3**: Should validation be synchronous or background?
- **Decision Needed By**: Week 7
- **Options**: (A) Synchronous (blocking), (B) Background (async)
- **Recommendation**: (A) for MVP simplicity

**Q4**: How to handle validation failures (consensus <0.7)?
- **Decision Needed By**: Week 7
- **Options**: (A) Reject claim, (B) Flag but include, (C) User prompt
- **Recommendation**: (B) Flag but include with warning

---

## 14. Simplified Architecture

### Single-Agent Design

**Agent Modes** (role-switching, not separate agents):

1. **Coordinator Mode**: Query parsing, deduplication check, mode selection
2. **Researcher Mode**: MCP calls (Tavily, Sequential, Serena), information gathering
3. **Validator Mode**: Multi-model consensus, confidence scoring
4. **Synthesizer Mode**: Document merging, Git commits

**State Transitions**:
```
IDLE
    → Coordinator (parse query + dedup check)
    → Researcher (gather information)
    → Validator (consensus check)
    → Synthesizer (update/create document)
    → COMPLETE
```

**No A2A Protocol**: Single agent switches modes sequentially, no inter-agent messaging needed.

**No DAG Queue**: Simple sequential workflow sufficient for MVP (parallel execution deferred to post-MVP).

**No Neo4j**: Git history + SQLite FTS5 sufficient for document relationships and search.

---

## 15. Comparison: MVP vs. Original Architecture

| Feature | Original (20 weeks) | MVP (12 weeks) | Rationale |
|---------|---------------------|----------------|-----------|
| Agents | 6 specialized | 1 with role-switching | Simplicity, no coordination overhead |
| Task Queue | DAG with parallel execution | Sequential workflow | MVP doesn't need parallelism yet |
| Graph DB | Neo4j | None (Git + SQLite) | Relationships via FTS5 search |
| A2A Protocol | Full message bus | None | Single agent = no inter-agent comms |
| Validation Models | 3+ | 2+ | Cost optimization |
| MCP Servers | 6 (Context7, Tavily, Sequential, Playwright, etc.) | 3 (Tavily, Sequential, Serena) | Focus on core research needs |
| Scalability | Multi-user, distributed | Single-user, local | Prove value first |
| Deployment | PostgreSQL, Kubernetes | SQLite, local CLI | Simple start |

**Key Principle**: Build the **simplest system** that proves the **core value proposition** (semantic deduplication + validation).

---

## 16. Glossary

**Semantic Deduplication**: Vector similarity search to identify duplicate or highly similar research queries.

**Consensus Validation**: Multi-model LLM validation where 2+ models must agree (consensus ≥0.7) for claim acceptance.

**UPDATE Mode**: Research mode triggered when existing document found (similarity >0.85).

**CREATE Mode**: Research mode triggered when no similar document exists (similarity <0.85).

**Role-Switching**: Single agent changes operational mode sequentially (Coordinator → Researcher → Validator → Synthesizer).

**MCP Integration**: Model Context Protocol server connections for tool access (Tavily, Sequential, Serena).

**Provenance Tracking**: Recording source URLs and retrieval timestamps for all claims.

**Confidence Score**: Numerical measure (0.0-1.0) of consensus validation agreement.

---

## Document Control

**Version History**:
- v1.0.0 (2025-11-12): Initial MVP requirements specification

**Approval Required From**:
- Product Owner: Requirements validation
- Technical Lead: Feasibility and timeline review
- User Representative: User story validation

**Next Review Date**: After Week 6 (mid-implementation checkpoint)

---

**Document Status**: ✅ COMPLETE - Ready for implementation

**Next Action**: Begin Week 1-2 implementation (Foundation phase)
