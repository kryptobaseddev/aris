# Phase 2 Critical Fixes Roadmap

**Created**: 2025-11-13
**Based On**: Phase 1b Quality Assessment
**Target**: 77%+ pass rate (389/512 tests)
**Current**: 57.2% pass rate (293/512 tests)
**Gap**: 96 tests to fix

---

## Executive Summary

Phase 1b achieved 57.2% pass rate (+72 tests), falling short of 77% target by 96 tests. Quality assessment reveals:

- ✅ Circular import fix is excellent (85/100) - production-ready
- ⚠️ Async config is correct but exposed fixture issues (70/100)
- ❌ Budget_limit implementation incomplete (45/100)
- ❌ 60 NEW test errors introduced (regressions)

**Phase 2 Focus**: Fix P0 critical issues blocking the remaining 96 tests

**Estimated Effort**: 5-6 hours

---

## Critical Issues Breakdown

### Issue 1: Async Fixture Decorators (30+ errors)

**Impact**: 30 test errors in performance benchmarks and integration tests

**Root Cause**: Missing `@pytest_asyncio.fixture` decorators

**Error Pattern**:
```
pytest.PytestRemovedIn9Warning: 'test_X' requested an async fixture
'benchmark_db', with no plugin or hook that handled it.
```

**Files Affected**:
- tests/conftest.py
- tests/integration/test_performance_benchmarks.py
- tests/integration/test_complete_workflow.py
- tests/integration/test_critical_paths.py

**Fix Required**:
```python
import pytest_asyncio

@pytest_asyncio.fixture  # ← ADD THIS DECORATOR
async def benchmark_db():
    """Async database fixture."""
    # ... existing code ...
```

**Verification**:
```bash
pytest tests/integration/test_performance_benchmarks.py -v
# Should pass without PytestRemovedIn9Warning
```

**Priority**: 🔴 P0-1
**Estimated Time**: 2 hours

---

### Issue 2: Incomplete Budget Limit Integration (47+ errors)

**Impact**: 47 Pydantic validation errors

**Root Cause**: `budget_limit` field only added to ArisConfig, missing from:
1. CostBreakdown dataclass
2. CostManager class
3. Related test fixtures

**Error Pattern**:
```
ValidationError: Extra inputs are not permitted
[type=extra_forbidden, input_value=5.0, input_type=float]
Field: budget_limit
```

**Files Affected**:
- src/aris/core/cost_manager.py (CostBreakdown)
- src/aris/core/cost_manager.py (CostManager.__init__)
- tests/unit/test_cost_manager.py
- tests/integration/test_complete_workflow.py

**Fix Required**:
```python
# src/aris/core/cost_manager.py

@dataclass
class CostBreakdown:
    tavily_cost: float = 0.0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    total_cost: float = 0.0
    budget_limit: Optional[float] = None  # ← ADD THIS
    timestamp: datetime = field(default_factory=datetime.utcnow)

# May also need to update:
class CostManager:
    def __init__(self, session_manager, budget_limit: Optional[float] = None):
        # ...
```

**Verification**:
```bash
pytest tests/unit/test_cost_manager.py -v
pytest tests/integration/test_complete_workflow.py::TestIntegrationHelpers::test_config_validation -v
```

**Priority**: 🔴 P0-2
**Estimated Time**: 1 hour

---

### Issue 3: Test Import Path Errors (13+ errors)

**Impact**: 13 AttributeError in test_research_orchestrator.py

**Root Cause**: Tests trying to import DocumentStore from research_orchestrator module after TYPE_CHECKING refactor

**Error Pattern**:
```
AttributeError: <module 'aris.core.research_orchestrator'> does not
have the attribute 'DocumentStore'
```

**Files Affected**:
- tests/unit/test_research_orchestrator.py

**Fix Required**:
```python
# Change this:
from aris.core.research_orchestrator import DocumentStore  # ❌ WRONG

# To this:
from aris.storage.document_store import DocumentStore  # ✅ CORRECT
```

**Verification**:
```bash
pytest tests/unit/test_research_orchestrator.py -v
# Should pass without AttributeError
```

**Priority**: 🔴 P0-3
**Estimated Time**: 30 minutes

---

### Issue 4: VectorStore Singleton Conflict (2 errors)

**Impact**: 2 test errors in vector store tests

**Root Cause**: Chroma client reinitialization with conflicting settings

**Error Pattern**:
```
VectorStoreError: An instance of Chroma already exists for ephemeral
with different settings
```

**Files Affected**:
- tests/unit/test_vector_store.py
- src/aris/storage/vector_store.py

**Fix Required**:
```python
# Add proper cleanup in test fixtures
@pytest.fixture
def vector_store():
    store = VectorStore(...)
    yield store
    store.cleanup()  # ← Ensure cleanup
    # Or reset singleton state
```

**Verification**:
```bash
pytest tests/unit/test_vector_store.py -v
```

**Priority**: 🟡 P1-1
**Estimated Time**: 30 minutes

---

### Issue 5: Resource Leak Warnings (8+ warnings)

**Impact**: 8 unclosed database connection warnings

**Root Cause**: Database connections not properly closed in tests

**Error Pattern**:
```
ResourceWarning: unclosed <sqlite3.Connection object>
```

**Files Affected**:
- Multiple test files using database fixtures
- src/aris/storage/database.py (potentially)

**Fix Required**:
```python
# Ensure context managers used
with DatabaseManager(path) as db:
    # ... operations ...

# Or explicit cleanup
@pytest.fixture
def db_manager():
    manager = DatabaseManager(path)
    yield manager
    manager.close()  # ← Explicit cleanup
```

**Verification**:
```bash
pytest -W error::ResourceWarning tests/
# Should pass without ResourceWarning
```

**Priority**: 🟡 P1-2
**Estimated Time**: 1 hour

---

## Implementation Plan

### Phase 2a: Critical P0 Fixes (4 hours)

**Session 1 (2 hours): Async Fixture Decorators**
1. Identify all async fixtures missing decorators (30 min)
2. Add `@pytest_asyncio.fixture` to all async fixtures (1 hour)
3. Run performance benchmark tests (15 min)
4. Fix any remaining async-related issues (15 min)
5. Validate: 30+ errors → 0 errors

**Session 2 (1 hour): Budget Limit Integration**
1. Add `budget_limit` to CostBreakdown dataclass (15 min)
2. Update CostManager class if needed (15 min)
3. Verify test fixture compatibility (15 min)
4. Run cost manager tests (15 min)
5. Validate: 47+ errors → 0 errors

**Session 3 (30 min): Test Import Paths**
1. Find all wrong imports in test files (10 min)
2. Update import paths (10 min)
3. Run research orchestrator tests (10 min)
4. Validate: 13+ errors → 0 errors

**Session 4 (30 min): Full Validation**
1. Run complete test suite (10 min)
2. Analyze results vs. target (10 min)
3. Document remaining issues (10 min)
4. Target validation: 57.2% → 77%+ pass rate

### Phase 2b: Important P1 Fixes (2 hours)

**Session 5 (30 min): VectorStore Singleton**
1. Add proper fixture cleanup (15 min)
2. Test singleton behavior (15 min)
3. Validate: 2 errors → 0 errors

**Session 6 (1 hour): Resource Leaks**
1. Identify all unclosed connections (20 min)
2. Add context managers or cleanup (30 min)
3. Validate with ResourceWarning checks (10 min)

**Session 7 (30 min): Documentation & Testing**
1. Add TYPE_CHECKING explanatory comments (15 min)
2. Add circular import test (15 min)

---

## Success Criteria

### Phase 2a (P0 - Critical)
- ✅ Zero async fixture decorator errors
- ✅ Zero Pydantic validation errors for budget_limit
- ✅ Zero import AttributeErrors
- ✅ Pass rate ≥ 77% (389/512 tests)
- ✅ No new regressions introduced

### Phase 2b (P1 - Important)
- ✅ Zero VectorStore singleton errors
- ✅ Zero ResourceWarnings
- ✅ Documentation comments added
- ✅ Circular import test added

### Quality Standards
- ✅ Full test suite run before ANY commit
- ✅ All P0 issues resolved before P1 work
- ✅ Pass rate improvement documented
- ✅ No shortcuts or workarounds

---

## Risk Mitigation

### Risk 1: Additional Hidden Issues

**Likelihood**: 🟡 MEDIUM
**Impact**: Could add 1-2 hours to timeline

**Mitigation**:
- Run full test suite after EACH fix
- Document any new issues immediately
- Adjust timeline if new blockers found

### Risk 2: Fixture Scope Conflicts

**Likelihood**: 🟡 MEDIUM
**Impact**: Async fixtures may need scope adjustments

**Mitigation**:
- Test fixture scopes: function, class, module
- Use `asyncio_default_fixture_loop_scope` setting
- Document scope decisions

### Risk 3: Budget Limit Model Integration

**Likelihood**: 🟢 LOW
**Impact**: May need updates to more models than expected

**Mitigation**:
- Grep for all budget_limit usage first
- Update ALL models before testing
- Validate schema consistency

---

## Validation Checklist

### Before Starting Phase 2
- [ ] Review Phase 1b Quality Assessment
- [ ] Understand all P0 issues
- [ ] Set up test environment
- [ ] Baseline: Confirm 57.2% pass rate

### During Phase 2 (After Each Fix)
- [ ] Run affected tests
- [ ] Run full test suite
- [ ] Document pass rate change
- [ ] Check for new regressions
- [ ] Update progress tracking

### After Phase 2a (P0 Complete)
- [ ] Pass rate ≥ 77% (389/512)
- [ ] Zero P0 blocking issues
- [ ] All critical errors resolved
- [ ] No new test failures
- [ ] Ready for Phase 3 or production

### After Phase 2b (P1 Complete)
- [ ] Zero warnings
- [ ] Documentation complete
- [ ] Tests added for circular imports
- [ ] Resource leaks fixed
- [ ] Code review completed

---

## Handoff to Implementation Agent

### Context Package
1. Phase 1b Quality Assessment Report
2. Phase 1 Validation Report
3. This roadmap (Phase 2 Critical Fixes)

### Starting Point
- **Baseline**: 57.2% pass rate (293/512 tests)
- **Target**: 77%+ pass rate (389/512 tests)
- **Gap**: 96 tests to fix

### Work Prioritization
1. 🔴 P0-1: Async fixture decorators (30 errors)
2. 🔴 P0-2: Budget_limit integration (47 errors)
3. 🔴 P0-3: Test import paths (13 errors)
4. 🟡 P1-1: VectorStore singleton (2 errors)
5. 🟡 P1-2: Resource leaks (8 warnings)

### Expected Deliverables
1. Fixed test files with proper decorators
2. Updated cost_manager.py with budget_limit
3. Corrected test import paths
4. Test suite passing at 77%+
5. Documentation of remaining issues (if any)

### Time Budget
- **P0 Critical**: 4 hours (strict)
- **P1 Important**: 2 hours (flexible)
- **Total**: 6 hours maximum

---

## Next Steps

**Immediate**: Hand off to Implementation Agent with:
1. This roadmap
2. Quality Assessment Report
3. Phase 1 Validation Report
4. Clear P0 priority list

**Expected**: Implementation Agent completes P0 fixes in single session (4 hours)

**Validation**: Quality Engineer validates 77%+ pass rate achievement

**Outcome**: Phase 2 complete, ready for Phase 3 (remaining 23% of tests) or production deployment decision

---

**Roadmap Complete**
**Status**: Ready for Implementation Agent
**Quality Assessment**: Complete (62/100 → targeting 85/100 after Phase 2)
