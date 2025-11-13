# Research Orchestrator Quick Start Guide

## Overview

The Research Orchestrator is the **core engine** of ARIS that coordinates all components to execute complete research workflows from query to Git-versioned document.

## Quick Usage

### CLI (End Users)

```bash
# Basic research
aris research "What is quantum computing?"

# Deep research with custom budget
aris research "Latest AI developments" --depth deep --max-cost 2.00

# Without streaming (batch mode)
aris research "Machine learning basics" --no-stream

# Check session status (Agent 4 will make this functional)
aris research status <session-id>
```

### Python API (Developers)

```python
from aris.core.config import ConfigManager
from aris.core.research_orchestrator import ResearchOrchestrator

# Initialize
config = ConfigManager.get_instance().get_config()
orchestrator = ResearchOrchestrator(config)

# Execute research
result = await orchestrator.execute_research(
    query="How do LLMs reason?",
    depth="standard",  # quick, standard, deep
    max_cost=0.50      # Optional budget override
)

# Access results
print(f"Document: {result.document_path}")
print(f"Confidence: {result.confidence:.2%}")
print(f"Cost: ${result.total_cost:.2f}")
print(f"Hops: {result.hops_executed}")
print(f"Sources: {result.sources_analyzed}")
```

### With Progress Streaming

```python
orchestrator = ResearchOrchestrator(config)

# Register callback for real-time updates
def show_progress(event):
    print(f"[{event.event_type}] {event.message}")

orchestrator.progress_tracker.register_callback(show_progress)

# Execute with streaming
result = await orchestrator.execute_research(
    query="Latest AI research",
    depth="deep"
)
```

---

## Architecture

```
User Query
    ↓
ResearchOrchestrator
    ↓
┌───────────┬──────────────┬──────────────┐
│           │              │              │
▼           ▼              ▼              ▼
Reasoning   Document       Database      Progress
Engine      Store          Manager       Tracker
│           │              │              │
▼           ▼              ▼              ▼
Tavily +    Git +          SQLite         CLI
Sequential  Filesystem     (session)      Streaming
```

---

## Research Workflow

```
1. Analyze Query
   ├─ Extract topics
   ├─ Generate hypotheses
   └─ Identify knowledge gaps

2. Multi-Hop Research
   ├─ Hop 1: Initial evidence gathering
   │   ├─ Tavily search
   │   ├─ Test hypotheses (Sequential)
   │   └─ Synthesize findings
   ├─ Hop 2: Refine understanding
   │   └─ (same process)
   └─ Hop N: Until confidence or budget reached

3. Create Document
   ├─ Format as markdown
   ├─ Write to research/topic/file.md
   └─ Git commit

4. Return Result
   └─ Metrics and document path
```

---

## Configuration

**Research Depths** (from `src/aris/models/config.py`):

| Depth    | Budget | Max Hops | Use Case                    |
|----------|--------|----------|-----------------------------|
| quick    | $0.20  | 1        | Simple questions, summaries |
| standard | $0.50  | 3        | Normal research needs       |
| deep     | $2.00  | 5        | Complex topics, thorough    |

**Confidence Thresholds**:
- Target: 0.70 (70% - good enough to complete)
- Early stop: 0.85 (85% - excellent, stop early)

**Budget Enforcement**:
- Warning at 90% of budget
- Hard stop at 100% of budget
- User can override with `--max-cost`

---

## Components

### ResearchOrchestrator
**File**: `src/aris/core/research_orchestrator.py`

**Key Methods**:
- `execute_research(query, depth, max_cost)` - Main entry point
- `get_session_status(session_id)` - Get session (Agent 4)
- `resume_research(session_id)` - Resume interrupted (Agent 4)

### ProgressTracker
**File**: `src/aris/core/progress_tracker.py`

**Features**:
- Event emission with callbacks
- Progress percentage calculation
- Duration tracking
- Error/warning events

**Usage**:
```python
tracker = ProgressTracker()
tracker.register_callback(callback_fn)
tracker.update("Message", ProgressEventType.INFO)
```

### ReasoningEngine
**File**: `src/aris/core/reasoning_engine.py`

**Integration**:
- Tavily for evidence gathering
- Sequential for hypothesis testing
- Multi-hop reasoning
- Confidence scoring

---

## Output Document Format

```markdown
# Research: {query}

**Research Date**: YYYY-MM-DD
**Confidence Score**: XX.X%
**Sources Analyzed**: N
**Research Hops**: N
**Cost**: $X.XX

## Summary
- Key finding 1
- Key finding 2
- Key finding 3

## Research Process

### Hop 1
**Hypotheses Tested**:
- ✓ Hypothesis 1 (confidence: 75%)
- ✗ Hypothesis 2 (confidence: 45%)

**Evidence**:
- Source 1
- Source 2

**Key Findings**:
- Finding from hop 1

## Sources
- http://source1.com
- http://source2.com

## Remaining Questions
- Gap to explore

## Recommendations
- Next steps
```

---

## Error Handling

**Graceful Failures**:
- Tavily search errors: logged, research continues
- Sequential errors: stops research, marks session as error
- Document creation errors: raises ResearchOrchestratorError

**Progress Tracking**:
- All errors logged to progress tracker
- CLI shows error messages with context
- Session marked as "error" in database (Agent 4)

---

## Testing

**Unit Tests**:
```bash
pytest tests/unit/test_research_orchestrator.py -v
```

**Integration Tests**:
```bash
pytest tests/integration/test_end_to_end_research.py -v
```

**Coverage**:
```bash
pytest tests/ -k orchestrator --cov=src/aris/core/research_orchestrator
```

---

## Extending the Orchestrator

### Add Custom Progress Event

```python
from aris.core.progress_tracker import ProgressEventType

# In your extension
orchestrator.progress_tracker.update(
    "Custom operation in progress",
    ProgressEventType.INFO,
    data={"custom_field": "value"}
)
```

### Add Pre/Post Hooks

```python
class ExtendedOrchestrator(ResearchOrchestrator):
    async def execute_research(self, query, depth, max_cost):
        # Pre-hook
        await self._pre_research_hook(query)

        # Execute
        result = await super().execute_research(query, depth, max_cost)

        # Post-hook
        await self._post_research_hook(result)

        return result
```

### Custom Document Formatting

```python
# Override formatting method
def _format_research_findings(self, context, query, session):
    # Custom markdown generation
    return custom_markdown_content
```

---

## Common Issues

### "TavilyClient not found"
**Solution**: Set `TAVILY_API_KEY` environment variable

### "Sequential MCP failed to start"
**Solution**: Install Sequential MCP: `npm install -g @modelcontextprotocol/sequential-thinking`

### "Database not found"
**Solution**: Run `aris db init` first

### "Permission denied" on Git commit
**Solution**: Configure Git: `git config user.name/user.email`

---

## Performance Tips

1. **Use quick depth for simple questions** - Saves cost and time
2. **Set max_cost for expensive topics** - Prevents runaway costs
3. **Use --no-stream for batch processing** - Slightly faster
4. **Resume interrupted research** (Agent 4) - Don't start from scratch

---

## Next Steps (Agent 4)

1. **Session Persistence**: Store sessions in database
2. **Resume Capability**: Continue interrupted research
3. **Session Management**: List, search, delete sessions
4. **Analytics**: Research statistics and insights

---

## API Reference

### ResearchOrchestrator

```python
class ResearchOrchestrator:
    def __init__(self, config: ArisConfig)

    async def execute_research(
        query: str,
        depth: str = "standard",
        max_cost: Optional[float] = None
    ) -> ResearchResult

    async def get_session_status(
        session_id: UUID
    ) -> Optional[ResearchSession]

    async def resume_research(
        session_id: UUID,
        max_additional_hops: Optional[int] = None
    ) -> ResearchResult  # Agent 4
```

### ResearchResult

```python
class ResearchResult:
    session_id: UUID
    query_text: str
    success: bool
    document_path: Optional[str]
    operation: str  # "created" | "updated"
    confidence: float
    sources_analyzed: int
    hops_executed: int
    total_cost: float
    within_budget: bool
    duration_seconds: float
    suggestions: list[str]
    warnings: list[str]
```

---

## Support

**Documentation**:
- Complete: `WAVE2-AGENT3-COMPLETE.md`
- Handoff: `AGENT3-ORCHESTRATOR-HANDOFF.md`

**Code**:
- Orchestrator: `src/aris/core/research_orchestrator.py`
- Tests: `tests/unit/test_research_orchestrator.py`
- CLI: `src/aris/cli/research_commands.py`

**Examples**:
- See `tests/integration/test_end_to_end_research.py` for usage patterns
