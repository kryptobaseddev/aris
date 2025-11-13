# Wave 4 - Agent 1 to Agent 2: Handoff Package

**From**: Agent 1 (Performance Engineer) - Cost Tracking System
**To**: Agent 2 (Session Management & Recovery)
**Date**: 2025-11-12
**Status**: READY FOR HANDOFF

---

## What You're Receiving

Agent 1 has completed the cost tracking and budget management system. This provides a solid foundation for Agent 2's session management work.

### Delivered Components

**Production Code** (770+ lines):
```
src/aris/core/cost_manager.py         (370+ lines)
src/aris/cli/cost_commands.py         (400+ lines)
```

**Tests** (250+ lines):
```
tests/test_cost_manager.py            (20+ tests)
```

**Documentation**:
```
docs/COST_TRACKING_GUIDE.md           (comprehensive)
WAVE4-AGENT1-COST-TRACKING-COMPLETE.md
WAVE4-AGENT1-VERIFICATION.md
```

**Integration**:
```
src/aris/cli/main.py                  (cost commands registered)
```

---

## Architecture Overview

### Cost Tracking System

The system tracks costs at two levels:

1. **Hop Level** (`ResearchHop`):
   - Individual hop cost: `ResearchHop.cost`
   - Cost breakdown: Tavily searches + LLM tokens
   - Example: Hop 1 = $0.03

2. **Session Level** (`ResearchSession`):
   - Total session cost: `ResearchSession.total_cost`
   - Sum of all hops + accumulation
   - Example: Session total = $0.12 (sum of 4 hops)

### Budget Management

Three-tier alert system:
- **75%**: Caution warning
- **90%**: High warning
- **100%+**: Critical alert (operations stopped)

---

## Key Interfaces You'll Use

### 1. Track Cost After Hop Completion
```python
from aris.core.cost_manager import CostManager

cost_mgr = CostManager(session_manager)

# Call after hop completes
breakdown, alert = await cost_mgr.track_hop_cost(
    session_id=session_id,
    hop_number=hop_number,
    tavily_searches=num_searches,
    llm_tokens=num_tokens
)

# Handle alert if budget threshold exceeded
if alert:
    logging.warning(f"Budget alert: {alert.message}")
```

### 2. Check Budget Before Operation
```python
# Call before expensive operations
can_perform = await cost_mgr.can_perform_operation(
    session_id=session_id,
    operation_cost=0.05,
    budget_limit=0.50
)

if not can_perform:
    logging.info("Budget limit reached, stopping research")
    break
```

### 3. Get Cost Status
```python
# Get current session cost summary
summary = await cost_mgr.get_session_summary(session_id)
print(f"Current cost: ${summary['total_cost']:.4f}")
print(f"Budget used: {summary['budget_used_percentage']:.1f}%")
```

---

## Integration Points with Your Work

### Session Checkpointing
When implementing session checkpoints, include cost data:

```python
# Checkpoint should capture cost state
checkpoint = {
    "session_id": session_id,
    "hop_number": current_hop,
    "total_cost": session.total_cost,
    "budget_target": session.budget_target,
    "warnings_issued": session.budget_warnings_issued,
    # ... other checkpoint data
}
```

### Session Recovery
When recovering from checkpoint, restore cost data:

```python
# Restore cost tracking state
session.total_cost = checkpoint["total_cost"]
session.budget_warnings_issued = checkpoint["warnings_issued"]
```

### Progress Tracking
Include cost in progress output:

```python
# Progress update should show cost
progress = {
    "hop": current_hop,
    "status": "analyzing",
    "cost_so_far": f"${session.total_cost:.4f}",
    "budget_remaining": f"${session.budget_target - session.total_cost:.4f}",
}
```

---

## Data Models Already Extended

The database models have been prepared with cost fields:

### ResearchSession (src/aris/storage/models.py)
```python
# Lines 213-215: Cost tracking fields
total_cost: float = 0.0               # Total cost accumulated
budget_target: float = 0.50           # Target budget
budget_warnings_issued: list[str] = []  # Alert history
```

### ResearchHop (src/aris/storage/models.py)
```python
# Lines 254-256: Per-hop cost tracking
llm_calls: int = 0                    # Number of LLM calls
total_tokens: int = 0                 # Total tokens used
cost: float = 0.0                     # Hop cost
```

**No database migrations needed** - fields already exist.

---

## CLI Commands Available for Testing

Once you implement session management, users will have cost tracking via:

```bash
# Summary of session costs
aris cost summary <session-id>

# Cost history over time
aris cost history --days 30

# Cost analytics and trends
aris cost analytics

# Export for external analysis
aris cost export --format json
```

---

## Configuration Available

Cost pricing is configurable:

```bash
aris cost configure \
  --tavily-cost 0.01 \
  --llm-cost-per-k-tokens 0.01
```

Or programmatically:
```python
cost_mgr.set_pricing(
    tavily_per_search=0.01,
    llm_per_1k_tokens=0.01
)
```

---

## Testing Patterns

The test suite provides examples you can follow:

**Example 1: Track cost and verify**
```python
breakdown, alert = await cost_mgr.track_hop_cost(...)
assert abs(breakdown.total_cost - expected) < 0.001
```

**Example 2: Check budget enforcement**
```python
can_perform = await cost_mgr.can_perform_operation(...)
assert can_perform is True
```

**Example 3: Verify alert threshold**
```python
alert = await cost_mgr.check_budget_threshold(...)
assert alert.threshold == BudgetThreshold.WARNING_HIGH
```

---

## Potential Integration Challenges & Solutions

### Challenge 1: Async Context
Cost tracking uses async methods. Ensure your session manager calls are also async.

**Solution**: All methods are properly `await`-able
```python
# Correct
result = await cost_mgr.track_hop_cost(...)

# Not required
result = cost_mgr.track_hop_cost(...)  # This won't work
```

### Challenge 2: Session State Consistency
Cost updates touch both memory cache and database.

**Solution**: Always use the public methods
```python
# Good: Updates both cache and DB
await cost_mgr.track_hop_cost(...)

# Bad: Only updates DB directly
session.total_cost = new_value
```

### Challenge 3: Budget Enforcement in Long Sessions
Multi-hop research might spend budget across hours.

**Solution**: Check budget before each expensive operation
```python
for hop in range(1, max_hops):
    if not await cost_mgr.can_perform_operation(...):
        logging.info("Budget exhausted, ending session")
        break
```

---

## Documentation to Reference

**User Guide**: `docs/COST_TRACKING_GUIDE.md`
- CLI usage examples
- Python API documentation
- Cost calculation formulas
- Budget threshold explanation
- Best practices

**Code**: Comments and docstrings throughout
- `src/aris/core/cost_manager.py` - Implementation details
- `src/aris/cli/cost_commands.py` - CLI command structure
- `tests/test_cost_manager.py` - Usage patterns

---

## Quality Assurance Checklist

Before merging your session management code:

- [ ] All cost tracking calls include proper error handling
- [ ] Cost is tracked after each hop completes
- [ ] Budget checks happen before expensive operations
- [ ] Cost data is persisted in session checkpoints
- [ ] Cost data is restored during session recovery
- [ ] Progress output includes cost information
- [ ] Tests verify cost tracking in session workflows
- [ ] Documentation updated to reference cost features

---

## Recommendation for Implementation Order

Based on the cost tracking system being ready, I recommend:

**Phase 1: Session Basics** (Week 1)
1. Session creation and retrieval ✅ (mostly done)
2. Hop execution tracking
3. Cost accumulation per hop

**Phase 2: Checkpointing** (Week 2)
1. Save session state to disk
2. Include cost data in checkpoints
3. Implement checkpoint recovery

**Phase 3: Advanced Features** (Week 3)
1. Session timeout handling
2. Progress streaming
3. Automatic checkpoint intervals

**Phase 4: Recovery & Validation** (Week 4)
1. Resume from last checkpoint
2. Validate state consistency
3. Handle partial executions

---

## Known Limitations to Keep in Mind

1. **No Real-Time Dashboard**: Cost data is file-based, not streaming
   - Workaround: CLI commands provide current status

2. **Single Account Support**: Only tracks one user's costs
   - Future: Could extend for multi-user/multi-account

3. **No Predictive Budgeting**: Can't predict future costs
   - Workaround: Users can set conservative budgets

4. **No Cost Anomaly Detection**: Can't detect unusual spending
   - Future: Analytics could identify patterns

---

## Success Criteria for Your Work

Your session management implementation should:

1. ✓ Integrate cost tracking into session lifecycle
2. ✓ Persist cost data in session checkpoints
3. ✓ Restore cost data on session recovery
4. ✓ Include cost in progress updates
5. ✓ Enforce budget limits during execution
6. ✓ Generate alerts to user on budget threshold
7. ✓ Support session timeout with cost accounting
8. ✓ All tests pass (both new and existing)

---

## Getting Started Checklist

To begin your work:

- [ ] Read this handoff document completely
- [ ] Review `docs/COST_TRACKING_GUIDE.md`
- [ ] Study `src/aris/core/cost_manager.py` interface
- [ ] Understand test patterns in `tests/test_cost_manager.py`
- [ ] Review `src/aris/storage/models.py` for cost fields
- [ ] Check `WAVE4-AGENT1-VERIFICATION.md` for verification details
- [ ] Run any existing tests to ensure environment works
- [ ] Set up IDE/editor for mypy type checking (strict mode)

---

## Contact/Questions

All code is documented with:
- Docstrings in class and method definitions
- Type hints for all parameters
- Examples in documentation
- Test cases showing usage

If implementation patterns aren't clear, reference:
- `tests/test_cost_manager.py` for usage examples
- `docs/COST_TRACKING_GUIDE.md` for API documentation
- `src/aris/core/cost_manager.py` for implementation details

---

## Summary

You're receiving a complete, tested, and documented cost tracking system that's ready for production use. The system provides:

- Real-time cost accumulation
- Budget enforcement with 3-tier alerts
- CLI commands for monitoring
- Comprehensive testing
- Full documentation

This foundation enables you to focus on session management, checkpointing, and recovery without worrying about cost calculation accuracy.

**Status**: Ready for Agent 2 to begin session management implementation.

---

**Agent 1 - Performance Engineer**
**Handoff Date**: 2025-11-12
**System Status**: PRODUCTION READY
**Code Quality**: VERIFIED
**Documentation**: COMPLETE
