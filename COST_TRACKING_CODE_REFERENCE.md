# Cost Tracking Code Reference Guide

Quick reference for navigating the cost tracking implementation.

## Core Modules

### 1. Cost Manager (`src/aris/core/cost_manager.py`)
Main cost tracking engine - 441 lines

| Component | Lines | Purpose |
|-----------|-------|---------|
| `BudgetThreshold` enum | 22-28 | Defines threshold levels (75%, 90%, 100%) |
| `CostBreakdownType` enum | 30-35 | Cost category types (Tavily, LLM, total) |
| `CostBreakdown` dataclass | 38-61 | Single cost record with breakdown |
| `BudgetAlert` dataclass | 64-83 | Budget threshold alert structure |
| `CostManager` class | 86-441 | Main cost tracking implementation |

**Key Methods**:
```python
# Line 102-104: Pricing configuration
TAVILY_COST_PER_SEARCH = 0.01
LLM_COST_PER_1K_TOKENS = 0.01

# Line 135-192: Track cost for single hop
async def track_hop_cost(session_id, hop_number, tavily_searches=0, llm_tokens=0)
  → Returns: (CostBreakdown, BudgetAlert or None)

# Line 193-247: Check if threshold exceeded
async def check_budget_threshold(session_id, budget_limit)
  → Returns: BudgetAlert or None

# Line 249-270: Pre-flight budget check
async def can_perform_operation(session_id, operation_cost, budget_limit)
  → Returns: bool

# Line 285-317: Get session cost summary
async def get_session_summary(session_id)
  → Returns: Dict with full cost breakdown

# Line 319-333: Get all sessions summary
async def get_all_sessions_cost_summary()
  → Returns: List[Dict]

# Line 335-385: Get cost history for period
async def get_cost_history(days=30, topic_id=None)
  → Returns: Dict with daily breakdown

# Line 387-403: Save detailed cost report
async def save_cost_report(session_id)
  → Returns: Path to saved JSON report

# Line 405-431: Export cost history
async def export_cost_history(format='json')
  → Returns: Path to exported file (json or csv)

# Line 433-440: Clear session cache
def clear_session_cache(session_id)
```

---

### 2. CLI Cost Commands (`src/aris/cli/cost_commands.py`)
Command-line interface for cost reporting - 343 lines

| Command | Lines | Purpose |
|---------|-------|---------|
| `cost_group` | 27-38 | Command group definition |
| `summary` | 41-130 | Show cost summary (session or all) |
| `history` | 133-191 | Show cost history with trends |
| `analytics` | 194-272 | Analytics dashboard (7-day, 30-day) |
| `export` | 275-302 | Export history to JSON/CSV |
| `configure` | 305-342 | Update pricing configuration |

**Command Usage**:
```bash
# Show summary for all sessions
aris cost summary

# Show detailed breakdown for specific session
aris cost summary <session-id>

# JSON output
aris cost summary --json

# Cost history for last 30 days
aris cost history --days 30

# Filter by topic
aris cost history --topic-id <topic-id> --json

# Analytics dashboard
aris cost analytics
aris cost analytics --json

# Export data
aris cost export --format json --days 30
aris cost export --format csv --days 30

# Configure pricing
aris cost configure --tavily-cost 0.01 --llm-cost-per-k-tokens 0.01
```

---

## Integration Points

### 3. Research Orchestrator (`src/aris/core/research_orchestrator.py`)
Budget enforcement during research - 680+ lines

| Section | Lines | Purpose |
|---------|-------|---------|
| Budget mapping | 575-581 | Default budgets: quick=$0.20, standard=$0.50, deep=$2.00 |
| Budget check (90%) | 266-273 | Warning when approaching limit |
| Budget check (100%) | 275-280 | Hard stop when budget exhausted |
| Session creation | 560-594 | Create session with budget_target |

**Key Code**:
```python
# Line 575-581: Set budget based on depth
budget_map = {
    ResearchDepth.QUICK: 0.20,
    ResearchDepth.STANDARD: 0.50,
    ResearchDepth.DEEP: 2.00,
}
budget = max_cost if max_cost is not None else budget_map[depth_enum]

# Line 267-273: Check 90% threshold
if session.total_cost >= session.budget_target * 0.90:
    progress_tracker.warning(
        f"Approaching budget limit: ${session.total_cost:.2f} / ${session.budget_target:.2f}"
    )

# Line 275-280: Check 100% threshold and stop
if session.total_cost >= session.budget_target:
    progress_tracker.warning("Budget limit reached, stopping research")
    session.budget_warnings_issued.append(...)
    break  # Stop research loop
```

---

### 4. Tavily Client (`src/aris/mcp/tavily_client.py`)
Operation cost tracking - 200+ lines

| Component | Lines | Purpose |
|-----------|-------|---------|
| `CostOperation` dataclass | 29-36 | Single operation record |
| `CostTracker` class | 39-95 | Accumulate operation costs |
| `TavilyClient` initialization | 177-200 | Initialize with cost tracker |

**Key Methods**:
```python
# Line 178: Cost per operation
COST_PER_OPERATION = 0.01

# Line 49-71: Initialize and record operations
tracker = CostTracker()
tracker.record_operation(
    operation_type="search",  # or "extract", "crawl", "map"
    cost=0.01,
    metadata={"query": "..."}
)

# Line 72-89: Get summary
summary = tracker.get_summary()
# Returns: {
#     "total_cost": 0.05,
#     "operation_count": 5,
#     "by_type": {
#         "search": {"count": 5, "cost": 0.05}
#     }
# }
```

---

### 5. Deduplication Gate (`src/aris/core/deduplication_gate.py`)
Token optimization via document deduplication - 515 lines

| Component | Lines | Purpose |
|-----------|-------|---------|
| `DeduplicationAction` enum | 19-24 | Decision actions (CREATE, UPDATE, MERGE) |
| `DeduplicationResult` dataclass | 49-92 | Gate decision with confidence |
| `DeduplicationGate` class | 94-515 | Pre-write validation gate |

**Key Methods**:
```python
# Line 150-254: Main validation method
async def check_before_write(content, metadata, query="")
  → Returns: DeduplicationResult

# Line 334-380: Calculate similarity score
def _calculate_similarity(content, existing_content, topics, existing_topics)
  → Returns: float (0.0-1.0)

# Usage:
result = await gate.check_before_write(
    content="New research...",
    metadata={"topics": ["AI", "ML"]},
    query="AI research question"
)

if result.should_update:
    print(f"Update {result.target_document.metadata.title}")
elif result.should_create:
    print("Create new document")
```

**Optimization Impact**:
- Prevents duplicate research (-30-40% tokens)
- Detects when to merge vs. create
- Tracks similarity with confidence scores

---

## Database Schema

### 6. Storage Models (`src/aris/storage/models.py`)
Cost-related database fields

**ResearchSession fields**:
```python
# Line 214-215: Cost tracking
total_cost: Float = 0.0  # Total cost accumulated
budget_target: Float = 0.50  # Budget limit

# Related fields:
status: String  # For tracking research state
budget_warnings_issued: List  # Audit trail of warnings
```

**ResearchHop fields**:
```python
# Line 256: Hop-level cost
cost: Float = 0.0

# Related fields:
llm_calls: Int  # Number of Tavily searches
total_tokens: Int  # LLM tokens used
```

---

## Data Flow Diagram

```
Research Execution:
┌─────────────────────────────────────────────────────────┐
│ 1. ResearchOrchestrator.execute_research()              │
│    - Create session with budget_target                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 2. ReasoningEngine.execute_research_hop()               │
│    - Call Tavily API                                    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 3. TavilyClient operations                              │
│    - CostTracker.record_operation()                     │
│    - Cost accumulated per operation                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 4. SessionManager.create_hop()                          │
│    - Store cost per hop in database                     │
│    - Aggregate session.total_cost                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 5. CostManager.track_hop_cost()                         │
│    - Calculate total cost                              │
│    - Check budget thresholds                            │
│    - Generate BudgetAlert if needed                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 6. ResearchOrchestrator budget checks                   │
│    - 90% threshold: issue warning                       │
│    - 100% threshold: halt research                      │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ 7. ProgressTracker / CLI output                         │
│    - Real-time cost updates to user                     │
└─────────────────────────────────────────────────────────┘

Reporting Pipeline:
┌─────────────────────────────────────────────────────────┐
│ CostManager methods retrieve data from database         │
│ - get_session_summary()                                 │
│ - get_all_sessions_cost_summary()                       │
│ - get_cost_history()                                    │
│ - export_cost_history()                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ CLI cost commands format and display                    │
│ - aris cost summary                                     │
│ - aris cost history                                     │
│ - aris cost analytics                                   │
│ - aris cost export                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

### Default Pricing (Configurable)

Located in: `src/aris/core/cost_manager.py`, lines 102-104

```python
# Change these to adjust cost model
TAVILY_COST_PER_SEARCH = 0.01  # $ per search
LLM_COST_PER_1K_TOKENS = 0.01  # $ per 1000 tokens
```

Update via CLI:
```bash
aris cost configure --tavily-cost 0.015 --llm-cost-per-k-tokens 0.012
```

---

## Testing & Validation

### Cost Calculation Example

```python
# Standard depth research (3 hops)
tavily_searches = 15  # 5 searches per hop × 3 hops
llm_tokens = 9000  # 3000 tokens per hop × 3 hops

tavily_cost = tavily_searches * 0.01 = $0.15
llm_cost = (llm_tokens / 1000) * 0.01 = $0.09
total_cost = $0.24  # ✅ Under $0.50 target
```

### Budget Thresholds

```python
# Session with $0.50 budget
session.total_cost = 0.375  # 75% of budget
→ BudgetAlert(threshold=WARNING_MEDIUM) issued

session.total_cost = 0.450  # 90% of budget
→ BudgetAlert(threshold=WARNING_HIGH) issued + warning logged

session.total_cost = 0.500  # 100% of budget
→ BudgetAlert(threshold=CRITICAL) issued + research halted
```

---

## Performance Characteristics

- **Cost Tracking**: O(1) per operation (simple accumulation)
- **Threshold Check**: O(1) per hop (simple comparison)
- **Session Summary**: O(n) where n = number of hops
- **Cost History**: O(n) where n = number of sessions
- **Similarity Check**: O(n×m) where n = existing docs, m = new doc

---

## Future Enhancements

Planned improvements listed in COST_TRACKING_VERIFICATION_REPORT.md:

1. **Cost Estimation API** - Predict costs before research
2. **Cost Transparency** - Show estimates in CLI
3. **Optimization Dashboard** - Track efficiency metrics
4. **Cost Forecasting** - Monthly projections
5. **Cost Attribution** - Breakdown by topic/domain

---

## Quick Navigation

- **For Implementation**: Start with `cost_manager.py`
- **For CLI Usage**: See `cost_commands.py` docstrings
- **For Integration**: Check `research_orchestrator.py` lines 266-280
- **For Optimization**: Review `deduplication_gate.py`
- **For Database**: See `storage/models.py`

---

**Last Updated**: 2025-11-12
**Version**: Production (5/6 features complete)
