# Phase 1c Deployment Plan - Critical Path to 77% Pass Rate

**Status**: Phase 1b FAILED - Pass rate 57.4% (target: 77%)
**Gap**: 95 tests needed to reach target
**Strategy**: Sequential deployment of 3 critical fixes

---

## Execution Summary

### Phase 1b Results
- **Pass Rate**: 57.4% (294/512 tests)
- **Improvement**: +0.2% from Phase 1a (+1 test only)
- **Target**: 77.0% (389/512 tests)
- **Shortfall**: -95 tests below target

### What Worked in Phase 1b
✅ Circular import errors ELIMINATED (0 occurrences)
✅ Pydantic "Extra inputs" errors ELIMINATED (0 occurrences)

### What Failed in Phase 1b
❌ Async fixture configuration NOT FIXED (58 errors persist)
❌ Test mock paths NOT UPDATED (28 new errors)
❌ Business logic NOT IMPLEMENTED (160 failures persist)

---

## Phase 1c Critical Path

### Agent 2 Re-Deploy: Fix Async Fixtures
**Priority**: P0 CRITICAL
**Impact**: +58 tests → 68.7% pass rate
**Time**: 15 minutes

**Task**: Fix pytest-asyncio configuration in conftest.py

**Current Error**:
```
pytest.PytestRemovedIn9Warning: 'test_name' requested an async fixture
'database_manager', with no plugin or hook that handled it.
```

**Root Cause**: Fixture scope mismatch - async fixtures requested by sync tests

**Solution**:
1. Add to `tests/conftest.py`:
```python
import pytest
import pytest_asyncio

# Configure async fixture handling
pytest_asyncio.fixture(scope="function")

@pytest_asyncio.fixture
async def database_manager():
    # existing implementation
    pass

@pytest_asyncio.fixture
async def db_manager():
    # existing implementation
    pass

@pytest_asyncio.fixture
async def benchmark_db():
    # existing implementation
    pass
```

2. Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

**Validation**:
```bash
pytest tests/integration/test_complete_workflow.py -v
# Should show 0 async fixture warnings
```

---

### Agent 1 Re-Deploy: Fix Mock Paths
**Priority**: P0 CRITICAL
**Impact**: +28 tests → 74.2% pass rate (cumulative)
**Time**: 10 minutes

**Task**: Update DocumentStore mock paths in test_research_orchestrator.py

**Current Error**:
```
AttributeError: <module 'aris.core.research_orchestrator'> does not have
the attribute 'DocumentStore'
```

**Root Cause**: Mocks reference old import path after circular import fix

**Solution**:
Update ALL mock patches in `tests/unit/test_research_orchestrator.py`:

**Find/Replace**:
- OLD: `@patch('aris.core.research_orchestrator.DocumentStore')`
- NEW: `@patch('aris.storage.DocumentStore')`

**Files to Update**:
```python
# tests/unit/test_research_orchestrator.py
@patch('aris.storage.DocumentStore')  # Changed from aris.core
@patch('aris.storage.database.DatabaseManager')
@patch('aris.cost.cost_manager.CostManager')
def test_create_research_session(...):
    pass
```

**Validation**:
```bash
pytest tests/unit/test_research_orchestrator.py -v
# Should show 28 tests passing, 0 AttributeErrors
```

---

### Agent 3 Re-Deploy: Cost Manager Budget Logic
**Priority**: P1 HIGH
**Impact**: +10 tests → 76.2% pass rate (cumulative) ✅ TARGET MET
**Time**: 20 minutes

**Task**: Implement budget enforcement methods in cost_manager.py

**Current Failures**:
```
test_budget_threshold_75_percent
test_budget_threshold_90_percent
test_budget_threshold_critical
test_can_perform_operation_within_budget
test_can_perform_operation_exceeds_budget
```

**Root Cause**: Methods are stubs or incomplete

**Solution**:
Implement in `src/aris/cost/cost_manager.py`:

```python
def can_perform_operation(
    self,
    estimated_cost: float,
    session_id: str
) -> tuple[bool, str]:
    """Check if operation can be performed within budget."""
    if self.budget_limit is None:
        return True, "No budget limit set"

    session_total = self.get_session_total(session_id)
    projected_total = session_total + estimated_cost

    if projected_total > self.budget_limit:
        return False, f"Would exceed budget: ${projected_total:.4f} > ${self.budget_limit:.4f}"

    # Check threshold warnings
    usage_pct = (projected_total / self.budget_limit) * 100

    if usage_pct >= 90:
        return True, f"CRITICAL: {usage_pct:.1f}% of budget"
    elif usage_pct >= 75:
        return True, f"WARNING: {usage_pct:.1f}% of budget"

    return True, f"OK: {usage_pct:.1f}% of budget"

def track_hop_cost(
    self,
    session_id: str,
    hop_number: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_cost: Optional[float] = None
):
    """Track cost for a research hop."""
    if total_cost is None:
        total_cost = (
            input_tokens * self.pricing["input_token_cost"] +
            output_tokens * self.pricing["output_token_cost"]
        )

    breakdown = CostBreakdown(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_cost=total_cost
    )

    if session_id not in self.session_costs:
        self.session_costs[session_id] = []

    self.session_costs[session_id].append(breakdown)

    # Check budget after tracking
    if self.budget_limit:
        session_total = self.get_session_total(session_id)
        usage_pct = (session_total / self.budget_limit) * 100

        if usage_pct >= 90:
            alert = BudgetAlert(
                threshold=0.90,
                current_cost=session_total,
                budget_limit=self.budget_limit,
                message=f"CRITICAL: {usage_pct:.1f}% of budget used"
            )
            self.alerts.append(alert)
```

**Validation**:
```bash
pytest tests/test_cost_manager.py -v
# Should show 10+ tests passing
```

---

## Deployment Sequence

### Step 1: Agent 2 (Async Fixtures)
```bash
# 1. Deploy fix
# 2. Run checkpoint validation
pytest tests/integration/test_complete_workflow.py -v
# 3. Verify: 0 async warnings, ~20 tests passing
```

**Checkpoint**: Pass rate should be ~68.7% (352/512 tests)

### Step 2: Agent 1 (Mock Paths)
```bash
# 1. Deploy fix
# 2. Run checkpoint validation
pytest tests/unit/test_research_orchestrator.py -v
# 3. Verify: 0 AttributeErrors, 28 tests passing
```

**Checkpoint**: Pass rate should be ~74.2% (380/512 tests)

### Step 3: Agent 3 (Cost Logic)
```bash
# 1. Deploy fix
# 2. Run checkpoint validation
pytest tests/test_cost_manager.py -v
# 3. Verify: 10+ tests passing
```

**Checkpoint**: Pass rate should be ~76.2% (390/512 tests) ✅ TARGET MET

### Step 4: Final Validation (Quality Engineer)
```bash
# Full test suite
pytest --maxfail=512 -v
# Verify: ≥77% pass rate (389+ tests)
```

---

## Success Criteria

### Phase 1c Complete When:
- ✅ Pass rate ≥ 77% (389/512 tests)
- ✅ Zero async fixture warnings
- ✅ Zero AttributeError for DocumentStore
- ✅ Budget enforcement tests passing
- ✅ No new regressions introduced

### Abort Conditions:
- ❌ Pass rate decreases after any deployment
- ❌ New error types introduced
- ❌ More than 10 additional test failures

---

## Risk Assessment

### Low Risk
- Agent 2 fix (async fixtures) - isolated to conftest.py
- Agent 1 fix (mock paths) - find/replace in test file

### Medium Risk
- Agent 3 fix (cost logic) - touches business logic
- Mitigation: Implement only required methods, minimal changes

### Rollback Plan
If any deployment fails:
1. Git reset to Phase 1b state
2. Re-analyze with Quality Engineer
3. Adjust deployment plan
4. Re-execute with corrections

---

## Timeline

| Agent | Task | Time | Cumulative |
|-------|------|------|------------|
| Agent 2 | Async fixtures | 15 min | 15 min |
| Validation | Checkpoint | 5 min | 20 min |
| Agent 1 | Mock paths | 10 min | 30 min |
| Validation | Checkpoint | 5 min | 35 min |
| Agent 3 | Cost logic | 20 min | 55 min |
| Validation | Final test suite | 10 min | 65 min |

**Total Estimated Time**: 65 minutes (1 hour 5 minutes)

---

## Post-Phase 1c Actions

### If Target Met (77%+)
1. Mark Phase 1 COMPLETE
2. Document lessons learned
3. Archive validation reports
4. Begin Phase 2 planning (remaining 88 tests)

### If Target Not Met (< 77%)
1. Analyze new blockers
2. Determine if Phase 1d needed
3. Re-prioritize remaining work
4. Update deployment strategy

---

**Report Generated**: 2025-11-13
**Next Action**: Deploy Agent 2 async fixture fix
**Validation**: Quality Engineer checkpoint after each agent
