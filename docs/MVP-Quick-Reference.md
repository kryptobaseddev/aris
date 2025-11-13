# ARIS MVP Quick Reference

**Version**: 1.0.0 | **Timeline**: 12 weeks | **Target Cost**: <$0.50/query

---

## 🎯 Core Value Proposition

**Problem**: LLM agents create duplicate documents instead of updating existing ones
**Solution**: ARIS uses semantic deduplication to UPDATE documents intelligently

**Result**: Consolidated research, validated information, persistent context

---

## 🏗️ Simplified Architecture

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

**Key Simplification**: 1 agent with 4 modes (NOT 6 separate agents)

---

## 📋 12 User Stories in 6 Epics

### Epic 1: Semantic Deduplication
- **US-001**: Prevent duplicate documents (>0.85 similarity → UPDATE mode)
- **US-002**: Explain mode selection (show similarity score + matched doc)

### Epic 2: Multi-Model Validation
- **US-003**: Consensus validation (2+ LLMs, consensus ≥0.7)
- **US-004**: Cost-aware validation (track costs, respect budget limits)

### Epic 3: Document Update Logic
- **US-005**: Intelligent section merging (new info → relevant sections)
- **US-006**: Git-based version history (every update = commit)

### Epic 4: Research Workflow
- **US-007**: Simple research query (`aris research "query"`)
- **US-008**: MCP integration (Tavily, Sequential, Serena)

### Epic 5: Session Persistence
- **US-009**: Project context memory (`aris init --project <name>`)
- **US-010**: Research history tracking (`aris history`)

### Epic 6: CLI User Experience
- **US-011**: Rich terminal output (progress bars, colors, JSON)
- **US-012**: Configuration management (`~/.aris/config.yaml`)

---

## 🎯 Success Metrics (3-Month Validation)

| Metric | Target | Threshold | Measurement |
|--------|--------|-----------|-------------|
| M1: Deduplication accuracy | >95% | >90% | Manual review (100 queries) |
| M2: Cost per query | <$0.50 | <$0.75 | Cost tracking logs |
| M3: Query completion time | <30s (80%) | <45s (80%) | Execution time logs |
| M4: Validation confidence | >0.85 avg | >0.75 avg | Consensus scores |
| M5: User satisfaction | >4.5/5 | >4.0/5 | User survey |
| M6: Document consolidation | 50% reduction | 30% reduction | Before/after analysis |
| M7: Context retention | 90% resume | 80% resume | Session logs |
| M8: Error rate | <2% | <5% | Error logs |

---

## ⚡ Non-Functional Requirements

### Performance
- Simple queries: **<30 seconds**
- Complex queries: **<2 minutes**
- Vector search: **<100ms**
- Cost per query: **<$0.50** (target), **<$1.00** (max)

### Reliability
- Error handling: **3 retries** with exponential backoff
- Data integrity: **Atomic transactions** (SQLite), **Git rollback**
- Uptime: **>99%** (excluding external API failures)

### Scalability
- Documents: **<1,000 per project** (MVP limit)
- Users: **1 user, 1 concurrent query**

### Security
- API keys: **System keyring** (not config files)
- Input sanitization: **All queries** before SQL

### Usability
- Installation: **`pip install aris-tool`**
- Documentation: **CLI help + quickstart + troubleshooting**

---

## 📅 12-Week Implementation Plan

```
Week 1-2:  Foundation
           ├─ Data models (Pydantic)
           ├─ SQLite schema
           ├─ CLI skeleton (Click)
           └─ Git integration
           ✓ Deliverable: Working database + CLI

Week 3-4:  Research Workflow
           ├─ Single-agent orchestrator
           ├─ MCP client integration
           └─ Basic research execution
           ✓ Deliverable: End-to-end flow (US-007)

Week 5-6:  Semantic Deduplication
           ├─ Vector embeddings
           ├─ Similarity search
           └─ UPDATE vs. CREATE logic
           ✓ Deliverable: Deduplication (US-001, US-002)

Week 7-8:  Multi-Model Validation
           ├─ Consensus validation
           ├─ Cost tracking
           └─ Low confidence flagging
           ✓ Deliverable: Validation (US-003, US-004)

Week 9-10: Document Updates
           ├─ Section merging
           ├─ Document parsing
           └─ Git commit automation
           ✓ Deliverable: Updates (US-005, US-006)

Week 11:   Session Persistence
           ├─ Project context management
           ├─ Research history
           └─ Serena integration
           ✓ Deliverable: Context (US-009, US-010)

Week 12:   Polish & Testing
           ├─ Rich terminal output
           ├─ Configuration management
           ├─ End-to-end testing
           └─ Documentation
           ✓ Deliverable: MVP COMPLETE
```

---

## 🔴 High Risks & Mitigations

| Risk | Mitigation | Contingency |
|------|------------|-------------|
| **R1: API costs exceed target** | Cost tracking early, optimize validation, cache embeddings | Single-model validation fallback |
| **R2: Deduplication false positives** | Conservative threshold (0.85), user overrides, Git rollback | Manual review mode |
| **R3: MCP server reliability** | Retry logic, circuit breakers, graceful fallbacks | Native search APIs (non-MCP) |

---

## ✅ MVP Scope: IN vs. OUT

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

**Rationale**: Each deferred feature adds significant complexity not required to prove core value proposition.

---

## 🔧 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | async/await, type hints |
| **Database** | SQLite + FTS5 | Simple, embedded, full-text search |
| **Version Control** | Git (GitPython) | Document history, rollback |
| **CLI** | Click + Rich | Commands + terminal formatting |
| **Embeddings** | OpenAI or Anthropic | Vector similarity search |
| **Validation** | Claude + GPT-4 | Multi-model consensus |
| **Search** | Tavily MCP | Web search integration |
| **Reasoning** | Sequential MCP | Complex analysis |
| **Memory** | Serena MCP | Project context persistence |

---

## 💡 Key Innovations

1. **Semantic Deduplication**: Vector embeddings prevent duplicate documents (>0.85 similarity = UPDATE)
2. **Multi-Model Consensus**: 2+ LLMs validate every claim (consensus ≥0.7 required)
3. **Document-as-Database**: Claims stored atomically, documents generated on-demand
4. **Role-Switching Agent**: Single agent with 4 modes (not 6 separate agents)
5. **Git-Based History**: Every update creates commit for rollback capability

---

## 🚀 Quick Commands (Planned)

```bash
# Initialize project
aris init --project my-research

# Execute research
aris research "How do booking systems handle offline mode?"

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
aris config get similarity_threshold
```

---

## 📊 Expected Output Format

```json
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
```

---

## 📝 Acceptance Criteria (MVP Complete)

MVP is **COMPLETE** when:

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

## 🎓 User Persona

**Name**: Claude Code User (Research Context)

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
- Duplicate research documents clutter workspace ❌
- Lost context between sessions ❌
- Uncertain about information accuracy ❌
- API costs accumulate with redundant queries ❌

**ARIS Solutions**:
- Semantic deduplication prevents duplicates ✅
- Project context persists across sessions ✅
- Multi-model validation ensures accuracy ✅
- Cost tracking and optimization ✅

---

## 📖 Related Documents

1. **[MVP-Requirements-Specification.md](./MVP-Requirements-Specification.md)** - Full requirements (16 sections)
2. **[Requirements-Validation-Checklist.md](./Requirements-Validation-Checklist.md)** - Verification proof
3. **[ARIS-Architecture-Blueprint.md](../claudedocs/ARIS-Architecture-Blueprint.md)** - Original architecture (reference)
4. **[README.md](../README.md)** - Project overview

---

## ⚠️ Important Notes

**MVP Philosophy**: Build the **simplest system** that proves the **core value proposition**

**Core Value**: Semantic deduplication + validation (everything else is enhancement)

**Timeline**: 12 weeks (NOT 20 weeks from original architecture)

**Scope Discipline**: If it's not in the 12 user stories, it's POST-MVP

**Cost Target**: <$0.50 per query (validate this EARLY)

**Quality Gate**: Don't add features until core workflows are rock-solid

---

**Document Status**: ✅ COMPLETE - Reference Guide for MVP Implementation

**Next Action**: Begin Week 1-2 (Foundation phase)
