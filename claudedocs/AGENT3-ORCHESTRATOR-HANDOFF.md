# Agent 3 to Agent 4 Handoff: Research Orchestrator → Document Storage Integration

## What's Complete (Agent 3)

### Core Implementation
✅ **ResearchOrchestrator** (`src/aris/core/research_orchestrator.py`)
- Complete end-to-end research workflow
- Tavily + Sequential MCP integration
- Multi-hop iteration with early stopping
- Budget enforcement and cost tracking
- Document creation with Git commits
- Progress streaming for CLI

✅ **ProgressTracker** (`src/aris/core/progress_tracker.py`)
- Real-time event emission
- Callback registration
- Progress percentage calculation
- Duration tracking

✅ **CLI Commands** (`src/aris/cli/research_commands.py`)
- `aris research "query"` - Execute research
- `aris research status <id>` - Check session (prepared)
- Rich formatting and streaming output
- JSON output support

✅ **Tests**
- Unit tests: orchestrator logic, formatting, session creation
- Integration tests: end-to-end workflow, multi-hop, budget enforcement

---

## What Agent 4 Should Build

### 1. Database Session Persistence

**Current State**: Sessions created in memory, not saved to database

**Task**: Implement database storage in ResearchOrchestrator

**File**: `src/aris/core/research_orchestrator.py`

**Methods to Implement**:

```python
def _update_session(self, session: ResearchSession) -> None:
    """Update research session in database."""
    # Current: No-op placeholder
    # TODO: Store session and hops in database

    with self.db.session_scope() as db_session:
        # Convert Pydantic ResearchSession to SQLAlchemy model
        db_session_model = self._session_to_db_model(session)

        # Merge (insert or update)
        db_session.merge(db_session_model)

        # Store hops with foreign key relationship
        for hop in session.hops:
            db_hop_model = self._hop_to_db_model(hop, session.id)
            db_session.merge(db_hop_model)


async def get_session_status(self, session_id: UUID) -> Optional[ResearchSession]:
    """Get status of a research session."""
    # Current: Returns None
    # TODO: Query from database

    with self.db.session_scope() as db_session:
        db_session_model = db_session.query(DBResearchSession)\
            .filter_by(id=session_id)\
            .first()

        if not db_session_model:
            return None

        # Convert SQLAlchemy model back to Pydantic
        return self._db_model_to_session(db_session_model)
```

**SQLAlchemy Models to Create** (`src/aris/storage/models.py`):

```python
class DBResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(String, primary_key=True)
    query_text = Column(String, nullable=False)
    depth = Column(String, nullable=False)
    status = Column(String, default="planning")
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    total_cost = Column(Float, default=0.0)
    budget_target = Column(Float, nullable=False)
    final_confidence = Column(Float, default=0.0)
    document_created = Column(String, nullable=True)
    document_updated = Column(String, nullable=True)

    # Relationships
    hops = relationship("DBResearchHop", back_populates="session")


class DBResearchHop(Base):
    __tablename__ = "research_hops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("research_sessions.id"))
    hop_number = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    sources_found = Column(Integer, default=0)
    tavily_cost = Column(Float, default=0.0)
    llm_cost = Column(Float, default=0.0)
    confidence_before = Column(Float, default=0.0)
    confidence_after = Column(Float, default=0.0)

    # Relationships
    session = relationship("DBResearchSession", back_populates="hops")
```

**Alembic Migration**:
```bash
# Create migration
alembic revision -m "Add research sessions and hops tables"

# Edit migration file to create tables
# Apply migration
alembic upgrade head
```

---

### 2. Session Management Commands

**File**: `src/aris/cli/research_commands.py`

**New Commands**:

```python
@click.command()
@click.option("--status", type=click.Choice(["all", "planning", "complete", "error"]))
@click.option("--limit", type=int, default=10)
@click.pass_context
def list(ctx: click.Context, status: str, limit: int):
    """List recent research sessions.

    Examples:
        aris research list
        aris research list --status complete
        aris research list --limit 20
    """
    # Query database for sessions
    # Display as table with status, query, confidence, cost


@click.command()
@click.argument("session_id")
@click.pass_context
def resume(ctx: click.Context, session_id: str):
    """Resume interrupted research session.

    Examples:
        aris research resume abc123...
    """
    # Load session from database
    # Continue from last completed hop
    # Update session on completion


@click.command()
@click.argument("session_id")
@click.option("--confirm", is_flag=True)
@click.pass_context
def delete(ctx: click.Context, session_id: str, confirm: bool):
    """Delete research session.

    Examples:
        aris research delete abc123... --confirm
    """
    # Delete session and hops from database
    # Optionally delete associated document


@click.command()
@click.option("--format", type=click.Choice(["json", "csv"]))
@click.pass_context
def export(ctx: click.Context, format: str):
    """Export research history.

    Examples:
        aris research export --format json > history.json
        aris research export --format csv > history.csv
    """
    # Query all sessions from database
    # Format and output
```

**Register Commands**:
```python
research_group.add_command(list_sessions, name="list")
research_group.add_command(resume)
research_group.add_command(delete)
research_group.add_command(export)
```

---

### 3. Enhanced Metrics and Analytics

**Task**: Add detailed metrics tracking per hop

**ResearchHop Enhancements**:
```python
class ResearchHop(BaseModel):
    # Existing fields...

    # Add detailed token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    llm_model: str = ""  # e.g., "claude-sonnet-3.5"

    # Add source quality metrics
    source_domains: list[str] = Field(default_factory=list)
    avg_source_credibility: float = 0.0

    # Add hypothesis metrics
    hypotheses_tested: int = 0
    hypotheses_supported: int = 0
    hypotheses_rejected: int = 0
```

**Analytics Command**:
```python
@click.command()
@click.option("--days", type=int, default=7)
@click.pass_context
def stats(ctx: click.Context, days: int):
    """Show research statistics.

    Examples:
        aris research stats
        aris research stats --days 30
    """
    # Query sessions from last N days
    # Calculate:
    # - Total research sessions
    # - Average cost per session
    # - Average confidence achieved
    # - Most researched topics
    # - Cost by depth level
    # Display as tables and charts (rich formatting)
```

---

### 4. Resume Capability

**Task**: Enable resuming interrupted research sessions

**ResearchOrchestrator Enhancement**:
```python
async def resume_research(
    self,
    session_id: UUID,
    max_additional_hops: Optional[int] = None
) -> ResearchResult:
    """Resume interrupted research session.

    Args:
        session_id: Session to resume
        max_additional_hops: Maximum additional hops (None = continue to max)

    Returns:
        ResearchResult with updated findings
    """
    # 1. Load session from database
    session = await self.get_session_status(session_id)
    if not session:
        raise ResearchOrchestratorError(f"Session not found: {session_id}")

    if session.is_complete:
        raise ResearchOrchestratorError("Session already complete")

    # 2. Load existing context from hops
    context = self._reconstruct_context_from_hops(session.hops)

    # 3. Continue research from current hop
    remaining_hops = max_hops - len(session.hops)
    if max_additional_hops:
        remaining_hops = min(remaining_hops, max_additional_hops)

    # 4. Execute remaining hops
    for hop_num in range(len(session.hops) + 1, len(session.hops) + remaining_hops + 1):
        # Execute hop (same as execute_research)
        # Update session
        # Check early stopping

    # 5. Update or create document
    # 6. Mark session complete
    # 7. Return result
```

---

### 5. Query History and Search

**Task**: Enable searching through past research

**Repository Class** (`src/aris/storage/repositories.py`):
```python
class ResearchSessionRepository:
    """Repository for research session database operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, session_id: UUID) -> Optional[DBResearchSession]:
        """Get session by ID."""
        return self.session.query(DBResearchSession)\
            .filter_by(id=str(session_id))\
            .first()

    def get_recent(self, limit: int = 10, status: Optional[str] = None) -> list[DBResearchSession]:
        """Get recent sessions."""
        query = self.session.query(DBResearchSession)\
            .order_by(DBResearchSession.started_at.desc())

        if status:
            query = query.filter_by(status=status)

        return query.limit(limit).all()

    def search_by_query(self, search_text: str) -> list[DBResearchSession]:
        """Search sessions by query text."""
        return self.session.query(DBResearchSession)\
            .filter(DBResearchSession.query_text.ilike(f"%{search_text}%"))\
            .order_by(DBResearchSession.started_at.desc())\
            .all()

    def get_statistics(self, days: int = 7) -> dict:
        """Get research statistics for last N days."""
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        sessions = self.session.query(DBResearchSession)\
            .filter(DBResearchSession.started_at >= cutoff)\
            .all()

        return {
            "total_sessions": len(sessions),
            "total_cost": sum(s.total_cost for s in sessions),
            "avg_cost": sum(s.total_cost for s in sessions) / len(sessions) if sessions else 0,
            "avg_confidence": sum(s.final_confidence for s in sessions) / len(sessions) if sessions else 0,
            "completed": sum(1 for s in sessions if s.status == "complete"),
            "errors": sum(1 for s in sessions if s.status == "error"),
        }
```

---

## Testing Checklist for Agent 4

### Unit Tests
- [ ] `_update_session()` stores session in database
- [ ] `_update_session()` stores hops with foreign keys
- [ ] `get_session_status()` retrieves session correctly
- [ ] `get_session_status()` returns None for missing session
- [ ] `resume_research()` continues from last hop
- [ ] ResearchSessionRepository CRUD operations
- [ ] Session-to-model conversion (Pydantic ↔ SQLAlchemy)

### Integration Tests
- [ ] End-to-end research saves session to database
- [ ] Multiple hops stored correctly
- [ ] Session can be retrieved after research
- [ ] Resume continues research correctly
- [ ] List command shows recent sessions
- [ ] Export command generates correct output
- [ ] Statistics calculation accurate

### Database Tests
- [ ] Alembic migration creates tables
- [ ] Foreign key constraints work
- [ ] Session deletion cascades to hops
- [ ] Query performance acceptable (<100ms for recent sessions)

---

## Implementation Priority

### Phase 1 (Core Persistence)
1. Create SQLAlchemy models (DBResearchSession, DBResearchHop)
2. Create Alembic migration
3. Implement `_update_session()` in orchestrator
4. Implement `get_session_status()` in orchestrator
5. Test session storage end-to-end

### Phase 2 (Session Management)
1. Implement ResearchSessionRepository
2. Add `aris research list` command
3. Add `aris research status` (connect to database)
4. Test session retrieval and display

### Phase 3 (Resume & Advanced)
1. Implement `resume_research()` in orchestrator
2. Add `aris research resume` command
3. Implement `_reconstruct_context_from_hops()`
4. Test resume functionality

### Phase 4 (Analytics)
1. Add enhanced metrics to ResearchHop
2. Implement `aris research stats` command
3. Add `aris research export` command
4. Add `aris research delete` command

---

## API Reference for Agent 4

### Key Classes to Interact With

**ResearchOrchestrator** (`src/aris/core/research_orchestrator.py`):
```python
class ResearchOrchestrator:
    db: DatabaseManager           # Database access
    document_store: DocumentStore # Document operations
    reasoning_engine: ReasoningEngine  # Research logic
    progress_tracker: ProgressTracker  # Event streaming
```

**DatabaseManager** (`src/aris/storage/database.py`):
```python
with db_manager.session_scope() as session:
    # SQLAlchemy session for queries
    session.add(model)
    session.query(Model).filter_by(...).first()
```

**ResearchSession** (`src/aris/models/research.py`):
```python
session = ResearchSession(
    query=ResearchQuery(...),
    budget_target=0.50
)
session.add_hop(hop)  # Adds hop and updates totals
```

---

## Questions for Agent 4 to Answer

1. **Session Serialization**: Should we store full ReasoningContext in database or reconstruct from hops?
   - **Recommendation**: Reconstruct (keeps database lean)

2. **Resume Strategy**: Should resume create new hops or continue existing session ID?
   - **Recommendation**: Continue existing session (maintains history)

3. **Soft Delete**: Should session deletion be soft (status="deleted") or hard?
   - **Recommendation**: Soft delete (preserves analytics)

4. **Cost Breakdown**: Track Tavily vs LLM costs separately?
   - **Recommendation**: Yes (needed for budget optimization)

---

## Success Criteria for Agent 4

✅ Research sessions persisted to database
✅ Session retrieval works (status command)
✅ Resume capability functional
✅ List/search commands operational
✅ Enhanced metrics tracked
✅ Analytics command provides insights
✅ Export functionality works
✅ Tests pass (unit + integration)
✅ Alembic migration successful

---

## Resources

**Documentation**:
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/orm/
- Alembic migrations: https://alembic.sqlalchemy.org/
- Click CLI: https://click.palletsprojects.com/
- Rich formatting: https://rich.readthedocs.io/

**Code References**:
- Existing models: `src/aris/storage/models.py`
- Database manager: `src/aris/storage/database.py`
- Research models: `src/aris/models/research.py`
- CLI structure: `src/aris/cli/`

---

## Agent 3 Available for Questions

If you need clarification on:
- Research workflow logic
- Session state management
- Progress tracking integration
- Test patterns

Refer to `WAVE2-AGENT3-COMPLETE.md` or review the orchestrator code directly.

Good luck! 🚀
