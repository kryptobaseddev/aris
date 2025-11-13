# Cost Tracking and Budget Management Guide

## Overview

ARIS provides comprehensive cost tracking and budget management for research operations. The system tracks costs per research hop, accumulates totals at the session level, and provides alerts when budget thresholds are exceeded.

**Key Features:**
- Real-time cost accumulation during research
- Budget threshold warnings (75%, 90%, 100%)
- Cost breakdown by service (Tavily searches, LLM tokens)
- Monthly/weekly cost analytics and trends
- Budget enforcement before operations
- Cost history export (JSON/CSV)

## Architecture

### Core Components

#### CostManager (`src/aris/core/cost_manager.py`)
Main class for cost tracking and budget management.

**Responsibilities:**
- Track costs per hop and session
- Enforce budget limits
- Generate cost reports and analytics
- Export cost history

**Key Methods:**
```python
# Track cost for a research hop
await cost_mgr.track_hop_cost(
    session_id="session-123",
    hop_number=1,
    tavily_searches=2,
    llm_tokens=1500
)

# Check if operation fits within budget
can_perform = await cost_mgr.can_perform_operation(
    session_id="session-123",
    operation_cost=0.05,
    budget_limit=0.50
)

# Get cost summary for session
summary = await cost_mgr.get_session_summary(session_id="session-123")

# Get historical cost data
history = await cost_mgr.get_cost_history(days=30)
```

#### CostBreakdown
Data class for detailed cost breakdown.

**Fields:**
- `tavily_cost`: Cost of Tavily searches
- `llm_tokens`: Number of LLM tokens used
- `llm_cost`: Cost of LLM usage
- `total_cost`: Sum of all costs
- `timestamp`: When cost was recorded

#### BudgetAlert
Data class for budget threshold alerts.

**Fields:**
- `threshold`: Which threshold was exceeded (75%, 90%, 100%)
- `current_cost`: Current session cost
- `budget_limit`: Budget limit in dollars
- `percentage_used`: Percentage of budget used
- `message`: Human-readable alert message

### Data Models

The system extends existing SQLAlchemy models:

**ResearchSession**
```python
total_cost: float          # Total cost of session
budget_target: float       # Target budget for session
budget_warnings_issued: list[str]  # Alert messages
```

**ResearchHop**
```python
cost: float               # Cost of this hop
llm_calls: int           # Number of LLM calls
total_tokens: int        # Total tokens used
```

## Usage

### Via CLI

#### Cost Summary
Show cost summary for a session or all sessions:

```bash
# Show summary for specific session
aris cost summary <session-id>

# Show summary for all recent sessions
aris cost summary

# JSON output for integration
aris cost summary --json
```

Example output:
```
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric          ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Status          │ complete    │
│ Hops Completed  │ 3/5         │
│ Tavily Cost     │ $0.0300     │
│ LLM Tokens      │ 4,500       │
│ LLM Cost        │ $0.0450     │
│ Total Cost      │ $0.0750     │
│ Budget Target   │ $0.5000     │
│ Budget Used     │ 15.0%       │
│ Status          │ ✓ Within Budget │
└─────────────────┴─────────────┘
```

#### Cost History
View cost trends over time:

```bash
# Last 30 days (default)
aris cost history

# Specific number of days
aris cost history --days 7

# Filter by topic
aris cost history --topic-id <topic-id>

# JSON output
aris cost history --json
```

#### Cost Analytics
View spending patterns and trends:

```bash
aris cost analytics

# Output shows:
# - 7-day spending
# - 30-day spending
# - Trend analysis (increasing/decreasing/stable)
```

#### Cost Configuration
Configure pricing for calculations:

```bash
# Update pricing
aris cost configure \
  --tavily-cost 0.01 \
  --llm-cost-per-k-tokens 0.015
```

#### Cost Export
Export cost data for external analysis:

```bash
# Export as JSON
aris cost export --format json

# Export as CSV
aris cost export --format csv
```

### Via Python API

#### Basic Usage

```python
from aris.core.cost_manager import CostManager
from aris.storage.session_manager import SessionManager

# Initialize
session_mgr = SessionManager(db_engine)
cost_mgr = CostManager(session_mgr)

# Track hop cost
breakdown, alert = await cost_mgr.track_hop_cost(
    session_id="session-123",
    hop_number=1,
    tavily_searches=2,
    llm_tokens=1500
)

if alert:
    print(f"Budget warning: {alert.message}")

# Check if next operation fits in budget
can_perform = await cost_mgr.can_perform_operation(
    session_id="session-123",
    operation_cost=0.05,
    budget_limit=0.50
)

if not can_perform:
    print("Operation would exceed budget")
    return
```

#### Custom Pricing

```python
# Set custom pricing
cost_mgr.set_pricing(
    tavily_per_search=0.02,  # $0.02 per search
    llm_per_1k_tokens=0.015  # $0.015 per 1K tokens
)
```

#### Cost Analytics

```python
# Get session cost summary
summary = await cost_mgr.get_session_summary(session_id)
print(f"Total cost: ${summary['total_cost']:.4f}")
print(f"Budget used: {summary['budget_used_percentage']:.1f}%")

# Get all sessions summary
all_summaries = await cost_mgr.get_all_sessions_cost_summary()

# Get historical data
history = await cost_mgr.get_cost_history(days=30)
for day, costs in history["daily_costs"].items():
    print(f"{day}: {costs['sessions']} sessions, ${costs['total_cost']:.4f}")

# Export to file
report_file = await cost_mgr.save_cost_report(session_id)
export_file = await cost_mgr.export_cost_history(format="json")
```

## Budget Thresholds

The system provides three levels of budget alerts:

| Threshold | Level | Action |
|-----------|-------|--------|
| 0-74% | Normal | Continue normally |
| 75-89% | Caution | Issue warning, suggest review |
| 90-99% | Warning | Issue alert, recommend limiting further ops |
| 100%+ | Critical | Stop new operations, enforce budget |

### Alert Messages

- **Caution (75%)**: "Budget caution (75%): $0.3750 / $0.5000"
- **Warning (90%)**: "Budget warning (90%): $0.4500 / $0.5000"
- **Critical (100%)**: "Budget exhausted: $0.5000 / $0.5000"

## Cost Calculation

Costs are calculated based on service usage:

### Tavily Searches
```
Cost = Number of Searches × Cost Per Search
Default: $0.01 per search
```

### LLM Tokens
```
Cost = (Total Tokens / 1000) × Cost Per 1K Tokens
Default: $0.01 per 1K tokens
```

### Total Session Cost
```
Total = Tavily Cost + LLM Cost
```

## Example Workflow

### Scenario: Multi-hop Research Session

```python
import asyncio
from aris.core.cost_manager import CostManager
from aris.storage.session_manager import SessionManager

async def research_with_budget():
    cost_mgr = CostManager(session_mgr)
    budget = 0.50  # $0.50 budget
    session_id = "research-123"

    for hop in range(1, 6):
        # Estimate cost for next hop
        estimated_cost = 0.05

        # Check if we can afford it
        can_perform = await cost_mgr.can_perform_operation(
            session_id=session_id,
            operation_cost=estimated_cost,
            budget_limit=budget
        )

        if not can_perform:
            print("Budget limit reached, stopping research")
            break

        # Execute hop (search + analysis)
        tavily_searches = 2
        llm_tokens = 1200

        # Track the cost
        breakdown, alert = await cost_mgr.track_hop_cost(
            session_id=session_id,
            hop_number=hop,
            tavily_searches=tavily_searches,
            llm_tokens=llm_tokens
        )

        print(f"Hop {hop} cost: ${breakdown.total_cost:.4f}")

        if alert:
            print(f"Alert: {alert.message}")

            # Stop at critical threshold
            if alert.threshold.value >= 1.0:
                break

    # Final report
    summary = await cost_mgr.get_session_summary(session_id)
    print(f"\nFinal Summary:")
    print(f"Total cost: ${summary['total_cost']:.4f}")
    print(f"Budget used: {summary['budget_used_percentage']:.1f}%")
    print(f"Within budget: {'Yes' if summary['within_budget'] else 'No'}")

asyncio.run(research_with_budget())
```

## Cost History Storage

Cost reports are stored in `.aris/cost-history/` directory:

```
.aris/
└── cost-history/
    ├── cost-report-session-123.json
    ├── cost-report-session-456.json
    └── cost-history-export-20250115-120000.json
```

Format example:
```json
{
  "session_id": "session-123",
  "status": "complete",
  "hops_completed": 3,
  "total_hops": 5,
  "tavily_cost": 0.03,
  "llm_tokens": 4500,
  "llm_cost": 0.045,
  "total_cost": 0.075,
  "budget_target": 0.5,
  "budget_used_percentage": 15.0,
  "within_budget": true,
  "warnings_issued": 0,
  "started_at": "2025-01-15T12:00:00",
  "completed_at": "2025-01-15T12:15:30"
}
```

## Best Practices

1. **Set Realistic Budgets**: Based on typical research depth needs
   - Quick: $0.20
   - Standard: $0.50
   - Deep: $2.00

2. **Monitor Cost Trends**: Review analytics regularly for cost optimization

3. **Use Budget Alerts**: Act on warnings before critical threshold

4. **Track Pricing Changes**: Update pricing configuration when service rates change

5. **Export Historical Data**: Archive monthly reports for auditing

6. **Batch Operations**: Accumulate requests to reduce overhead

## Troubleshooting

### Cost Seems High
- Check `aris cost analytics` for trends
- Review individual session costs with `aris cost summary <session-id>`
- Consider reducing hop count or LLM model complexity

### Budget Exceeded
- Review `budget_warnings_issued` in session summary
- Check which hops consumed most resources
- Adjust budget targets for future sessions

### Missing Cost Data
- Ensure hops are being tracked with `track_hop_cost()`
- Check database for orphaned sessions
- Verify cost manager is initialized with correct session manager

## Integration with Research Workflow

The cost manager integrates seamlessly with research operations:

```python
# During research hop execution
async def execute_research_hop(hop_spec):
    # ... perform search and analysis ...

    # Track the actual costs
    breakdown, alert = await cost_mgr.track_hop_cost(
        session_id=session_id,
        hop_number=hop_number,
        tavily_searches=actual_searches,
        llm_tokens=actual_tokens
    )

    # Handle budget alerts
    if alert and alert.threshold.value >= 0.9:
        # Log warning or adjust strategy
        pass

    return hop_result
```

## Future Enhancements

- [ ] Real-time cost dashboard with WebSocket updates
- [ ] Cost prediction based on query complexity
- [ ] Cost optimization recommendations
- [ ] Multi-account budget tracking
- [ ] Budget allocation across topics/projects
- [ ] Cost anomaly detection
