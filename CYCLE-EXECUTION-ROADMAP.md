# ARIS Multi-Cycle Execution Roadmap

**Objective**: Achieve 95%+ test pass rate and production deployment readiness
**Current Status** (Cycle 3 End): 68.0% pass rate (347/510 tests)
**Target Status**: 95%+ pass rate (487+/510 tests)
**Estimated Remaining Time**: 15-24 hours (4 priorities)

---

## Cycle 3 Actual Results (Lessons Learned)

**Original Estimates vs Reality**:
- **Estimated**: Phase 1 (77%) in 2-4h
- **Actual**: Phase 1 (68%) in ~6h across 4 iterations (1a, 1b, 1c, 1d)
- **Why Different**: Hidden blocker (pytest-asyncio package missing), multi-iteration debugging required

**Key Discoveries**:
1. pytest-asyncio package was missing from venv (blocked async tests until Phase 1d)
2. Budget_limit field needed in multiple models, not just ArisConfig
3. Circular import was actually TYPE_CHECKING pattern need, not a bug
4. Test execution timeouts prevented full Phase 2 validation
5. CLI failures are 87% due to one ConfigManager mock issue

**Pass Rate Progress**:
- Cycle 2 End: 43.1% (221/512 tests)
- Phase 1a: 57.2% (+72 tests)
- Phase 1b: 57.4% (+2 tests) - uncovered pytest-asyncio missing
- Phase 1c: 57.4% (0 tests) - fixes blocked by missing package
- Phase 1d: 68.0% (+53 tests) ✅ - package installed, async fixtures activated
- **Total Cycle 3**: +126 tests (+24.9 percentage points)

---

## Priority-Based Execution (Cycle 4+)

Based on Cycle 3 learnings, reorganized from phases to priorities for better ROI and reduced risk.

---

## Priority 1: Quick Wins (2-3 hours) → 77% ✅

**Target**: 77.2% pass rate (389/510 tests)
**Priority**: P0 Critical - Completes original Phase 1 target
**Dependencies**: None - can start immediately
**Confidence**: Very High (all fixes <1h each, well-understood)

### Category A: DocumentStatus.PUBLISHED Enum (5 minutes, 2 tests)

**Issue**: `AttributeError: type object 'DocumentStatus' has no attribute 'PUBLISHED'`
**File**: `tests/unit/test_document_finder.py`
**Root Cause**: Missing enum value

**Implementation**:
```python
# src/aris/models/enums.py or wherever DocumentStatus is defined
class DocumentStatus(Enum):
    # ... existing values ...
    PUBLISHED = "published"  # Add this value
```

**Subagent Deployment**:
1. Pattern Agent: Find DocumentStatus enum definition (2 min)
2. Implementation Agent: Add PUBLISHED value (3 min)

**Verification**: Run `pytest tests/unit/test_document_finder.py -k "rank_by_relevance_applies_recency_boost"`

**Time**: 5 minutes
**Impact**: +2 tests → 68.4% pass rate

---

### Category B: DatabaseManager.initialize() Method (30 minutes, 25 tests)

**Issue**: `AttributeError: 'DatabaseManager' object has no attribute 'initialize'`
**Files Affected**:
- `tests/integration/test_complete_workflow.py`
- `tests/integration/test_critical_paths.py`
- `tests/integration/test_performance_benchmarks.py`

**Root Cause**: Tests call `db_manager.initialize()` but method doesn't exist

**Implementation**:
```python
# src/aris/storage/database.py (DatabaseManager class)
async def initialize(self) -> None:
    """Initialize database and create tables.

    This is a convenience method that wraps create_tables() for
    backward compatibility with tests.
    """
    await self.create_tables()
```

**Subagent Deployment**:
1. Pattern Agent: Analyze DatabaseManager class and initialize() calls (10 min)
2. Implementation Agent: Add initialize() method (15 min)
3. Validation Agent: Run affected integration tests (5 min)

**Verification**: Run `pytest tests/integration/ -k "database" -v`

**Time**: 30 minutes
**Impact**: +25 tests → 73.3% pass rate

---

### Category C: CLI Mock Configuration Fix (35 minutes, 15 tests)

**Issue**: ConfigManager mock doesn't set `_config` attribute, causing ConfigurationError
**Tests Affected**: 9 unit tests + 6 integration tests = 15 total

**Root Cause Analysis** (from Cycle 3 diagnosis):
- Tests mock ConfigManager but don't set `_config` attribute
- When commands call `config_manager.get_config()`, it raises ConfigurationError
- **87% of CLI failures** from this one issue

**Primary Fix** (15 minutes, 13 tests):
```python
# tests/unit/test_cli.py (line ~40, mock_config_manager fixture)
@pytest.fixture
def mock_config_manager():
    instance = Mock(spec=ConfigManager)
    mock_config = Mock(spec=ArisConfig)
    # ... existing mock setup ...
    instance._config = mock_config  # ADD THIS LINE
    return instance
```

**Secondary Fix** (5 minutes, 2 tests):
```python
# tests/unit/test_cli.py (lines 199, and integration test)
# Change: "session start" → "session list"
# (session start command doesn't exist)
```

**Subagent Deployment**:
1. Implementation Agent A: Fix ConfigManager mock (15 min)
2. Implementation Agent B: Update session command tests (5 min)
3. Validation Agent: Run CLI tests (15 min)

**Verification**: Run `pytest tests/unit/test_cli.py tests/integration/test_cli_integration.py -v`

**Time**: 35 minutes (20 min implementation + 15 min validation)
**Impact**: +15 tests → 77.2% pass rate ✅

---

**Priority 1 Total**:
- **Time**: 1 hour 10 minutes (plus validation overhead = 2-3h total)
- **Impact**: +42 tests (68.0% → 77.2%)
- **Deliverable**: PHASE 1 COMPLETE ✅

**Validation Gate**:
- ✅ Pass rate ≥77% (389+ tests / 510 total)
- ✅ No regressions in existing 347 passing tests
- ✅ All 3 categories validated independently
- ✅ Test execution time <30 seconds (fast regression check)

---

## Priority 2: API Validation & Integration (5-7 hours) → 90%+

**Target**: 91.4% pass rate (470/510 tests)
**Priority**: P0-P1 High - Validates Phase 2 implementations
**Dependencies**: Priority 1 complete
**Confidence**: Medium (API aliases implemented but not fully validated)

### Category D: Test Timeout Investigation (1 hour, diagnostic)

**Issue**: Test execution timeouts prevented full Cycle 3 Phase 2 validation
**Impact**: Cannot confirm API alias effectiveness

**Investigation Tasks**:
1. Identify which tests cause timeouts (30 min)
2. Determine if timeout is test logic or infrastructure (15 min)
3. Implement workaround or fix (15 min)

**Possible Solutions**:
- Run targeted test subsets instead of full suite
- Increase pytest timeout configuration
- Identify and deselect problematic tests
- Fix test cleanup issues causing hangs

**Subagent Deployment**:
1. Backend Architect: Root cause analysis (30 min)
2. Quality Engineer: Test execution strategies (30 min)

**Verification**: Ability to run full test suite without timeouts

**Time**: 1 hour
**Impact**: Enables proper validation (no direct test fixes)

---

### Category E: API Alias Validation (1 hour, 58 tests estimated)

**Status**: Implementations complete in Cycle 3, validation incomplete

**API Aliases to Validate**:
1. **DocumentStore.save_document** (line 124) → Expected: 42 tests
2. **CostTracker.track_operation** (line 112) → Expected: 12 tests
3. **ProgressTracker.record_hop** (lines 186-193) → Expected: 4 tests

**Validation Strategy**:
```bash
# Run targeted subsets
pytest tests/integration/test_document_store.py -v
pytest -k "cost" -v
pytest -k "progress" -v
pytest -k "record_hop" -v
```

**Subagent Deployment**:
1. Validation Agent: Execute targeted test subsets (30 min)
2. Quality Engineer: Analyze results and identify remaining issues (30 min)

**Success Criteria**:
- DocumentStore tests using save_document() pass
- CostTracker tests using track_operation() pass
- ProgressTracker tests using record_hop() pass

**Time**: 1 hour
**Impact**: Confirm +58 tests work → 88.6% pass rate (if all pass)

---

### Category F: DocumentStore Git Integration (3-4 hours, 23 tests)

**Issue**: 23 test failures in `tests/integration/test_document_store.py`
**Root Cause**: Git operation failures (not fully diagnosed in Cycle 3)

**Investigation Required**:
1. Run failing tests individually to understand errors (30 min)
2. Categorize failures by error type (git setup, commit, diff, etc.) (30 min)
3. Implement fixes based on categories (2-3h)

**Likely Issues**:
- Git repository not initialized in test fixtures
- Mock git operations not configured correctly
- Git commit author/email not set in test environment
- Working directory not set correctly for git operations

**Subagent Deployment**:
1. Root Cause Analyst: Diagnose git operation failures (1h)
2. Backend Architect: Design fix strategy (30 min)
3. Implementation Agent: Apply fixes (2h)
4. Validation Agent: Run document store tests (30 min)

**Verification**: Run `pytest tests/integration/test_document_store.py -v`

**Time**: 3-4 hours
**Impact**: +23 tests → 91.4% pass rate

---

**Priority 2 Total**:
- **Time**: 5-7 hours
- **Impact**: +81 tests (77.2% → 91.4%)
- **Deliverable**: Phase 2 API alignment validated and working

**Validation Gate**:
- ✅ Pass rate ≥90% (459+ tests / 510 total)
- ✅ All API aliases confirmed working
- ✅ DocumentStore git integration functional
- ✅ Test execution reliable (no timeouts)

---

## Priority 3: Test Quality & Isolation (6-10 hours) → 98%+

**Target**: 98.8% pass rate (508/510 tests)
**Priority**: P2 Medium - Quality and edge cases
**Dependencies**: Priority 2 complete
**Confidence**: Medium (requires detailed debugging)

### Category G: ChromaDB Isolation (2-3 hours, 15 tests)

**Issue**: "An instance of Chroma already exists for ephemeral with different settings"
**Files Affected**: `tests/unit/storage/test_vector_store.py`
**Root Cause**: ChromaDB v1.3.4 enforces singleton pattern

**Investigation Required**:
1. Understand ChromaDB 1.3.4 singleton behavior (30 min)
2. Design isolation strategy (unique collections vs client reset) (30 min)
3. Implement fixtures with proper teardown (1-2h)

**Possible Solutions**:
```python
# Strategy 1: Unique collection names per test
@pytest.fixture
def unique_collection_name():
    return f"test_collection_{uuid.uuid4()}"

# Strategy 2: Proper Chroma client teardown
@pytest.fixture(autouse=True)
def reset_chroma_client():
    yield
    # Reset singleton state (if possible)

# Strategy 3: Use persistent mode instead of ephemeral
# (may be more stable with v1.3.4)
```

**Subagent Deployment**:
1. Research Agent: ChromaDB 1.3.4 best practices (30 min)
2. Pattern Agent: Analyze current test setup (30 min)
3. Implementation Agent: Implement isolation strategy (1-2h)
4. Validation Agent: Run vector store tests (30 min)

**Verification**: Run `pytest tests/unit/storage/test_vector_store.py -v` (all pass, no singleton errors)

**Time**: 2-3 hours
**Impact**: +15 tests → 94.3% pass rate

---

### Category H: Test Assertions & Logic (4-6 hours, 23 tests)

**Issue**: Various test assertion failures across multiple test files
**Types**: Enum .value access, metadata merge logic, boundary values, schema mismatches

**Categorized Fixes**:

1. **Enum .value access** (1h, ~7 tests)
   - Fix: Remove `.value` access on string enums
   - Files: `tests/test_document_merger.py`

2. **Metadata merge logic** (2h, ~7 tests)
   - Fix: Update questions_answered merge expectations
   - Files: `tests/test_document_merger.py`

3. **Boundary value assertions** (1h, ~3 tests)
   - Fix: Adjust 0.5 vs >0.5 comparisons
   - Files: Various deduplication tests

4. **Schema expectations** (1-2h, ~6 tests)
   - Fix: Update for new tables added in Migrations 002
   - Files: Database and schema tests

**Subagent Deployment**:
1. Pattern Agent: Categorize all assertion failures (1h)
2. Implementation Agent A: Fix enum and metadata issues (2h)
3. Implementation Agent B: Fix boundary values and schema (2h)
4. Validation Agent: Run affected test files (1h)

**Verification**: Run full test suite, verify specific assertion errors eliminated

**Time**: 4-6 hours
**Impact**: +23 tests → 98.8% pass rate

---

**Priority 3 Total**:
- **Time**: 6-10 hours
- **Impact**: +38 tests (91.4% → 98.8%)
- **Deliverable**: Test quality issues resolved, isolation working

**Validation Gate**:
- ✅ Pass rate ≥98% (500+ tests / 510 total)
- ✅ No singleton or isolation errors
- ✅ All assertion logic correct
- ✅ Test suite stable (no flaky tests)

---

## Priority 4: Production Polish (2-4 hours) → 100%

**Target**: 100% pass rate (510/510 tests) + Production Ready
**Priority**: P3 Nice to have (95% already achieved)
**Dependencies**: Priority 3 complete
**Confidence**: High (only 2 tests + quality checks remaining)

### Category I: Final Test Fixes (2 hours, 2 tests)

**Remaining Tests**: Whatever didn't get fixed in Priorities 1-3

**Likely Candidates**:
- Mock path issues (ResearchOrchestrator tests)
- Schema enum additions (beyond PUBLISHED)
- Edge cases in various test files

**Subagent Deployment**:
1. Quality Engineer: Identify remaining 2 failures (30 min)
2. Implementation Agent: Fix both tests (1h)
3. Validation Agent: Full suite validation (30 min)

**Verification**: Run `pytest --maxfail=512 -v` → 510/510 passing

**Time**: 2 hours
**Impact**: +2 tests → 100% pass rate ✅

---

### Category J: Coverage & Quality Gates (2 hours, quality metrics)

**Quality Requirements**:
1. Code coverage ≥85% (measure and improve if needed)
2. No critical warnings
3. Resource leak warnings <10
4. All git changes committed

**Tasks**:
- Run coverage report: `pytest --cov=src/aris --cov-report=html --cov-report=term`
- Review warnings and fix critical ones
- Clean up test artifacts and temporary files
- Commit all changes with comprehensive message

**Subagent Deployment**:
1. Quality Engineer: Coverage analysis and quality metrics (1h)
2. Refactoring Expert: Address any code quality issues (1h)

**Time**: 2 hours
**Impact**: Quality metrics achievement (no test count change)

---

### Category K: Production Readiness Validation (1 hour, checklist)

**Production Deployment Checklist**:

**Testing**:
- [ ] 100% test pass rate (510/510 tests)
- [ ] Coverage ≥85%
- [ ] Integration tests passing
- [ ] No critical warnings

**Infrastructure**:
- [ ] Database migrations tested
- [ ] Environment variables documented
- [ ] API keys configuration documented
- [ ] Logging configured

**Documentation**:
- [ ] README updated
- [ ] API documentation current
- [ ] Known issues documented
- [ ] Deployment guide created

**Quality**:
- [ ] No security vulnerabilities
- [ ] Resource leak warnings <10
- [ ] All changes committed

**Subagent Deployment**:
1. Technical Writer: Create deployment guide (30 min)
2. System Architect: Production readiness assessment (30 min)

**Deliverable**: Complete deployment guide + Go/No-Go decision

**Time**: 1 hour
**Impact**: Production deployment enabled

---

**Priority 4 Total**:
- **Time**: 2-4 hours (may be less if 100% achieved in Priority 3)
- **Impact**: +2 tests + production readiness (98.8% → 100%)
- **Deliverable**: Fully production-ready system

**Validation Gate**:
- ✅ 100% test pass rate (510/510 tests)
- ✅ Coverage ≥85%
- ✅ Production checklist complete
- ✅ Deployment guide ready
- ✅ No critical blockers

---

## Success Metrics by Priority

| Priority | Duration | Pass Rate | Tests Passing | Cumulative Time | Status |
|----------|----------|-----------|---------------|-----------------|--------|
| Start (Cycle 3 End) | - | 68.0% | 347/510 | 0h | BASELINE |
| Priority 1 | 2-3h | 77.2% | 389/510 | 2-3h | ✅ High Confidence |
| Priority 2 | 5-7h | 91.4% | 470/510 | 7-10h | ⚠️ Medium Confidence |
| Priority 3 | 6-10h | 98.8% | 508/510 | 13-20h | ⚠️ Medium Confidence |
| Priority 4 | 2-4h | 100% | 510/510 | 15-24h | ✅ High Confidence |

**Optimistic Estimate**: 15 hours (all go smoothly, no deep debugging)
**Realistic Estimate**: 20 hours (some investigation needed)
**Conservative Estimate**: 24 hours (unexpected complexity)

**95% Target Achievement**: After Priority 2 (91.4%) or early Priority 3

---

## Risk Mitigation

### High-Impact Risks

**Risk 1: Test timeouts continue in Priority 2**
- **Probability**: Medium
- **Impact**: High (blocks validation)
- **Mitigation**: Use targeted test subsets, investigate root cause thoroughly
- **Contingency**: Document as known issue, validate APIs through unit tests only

**Risk 2: DocumentStore git integration more complex than estimated**
- **Probability**: Medium
- **Impact**: High (23 tests, delays Priority 2)
- **Mitigation**: Time-box to 4 hours, defer if needed
- **Contingency**: Mark as known issue, focus on core functionality

**Risk 3: ChromaDB isolation requires architecture changes**
- **Probability**: Low
- **Impact**: High (delays Priority 3)
- **Mitigation**: Research ChromaDB 1.3.4 thoroughly before implementing
- **Contingency**: Downgrade to ChromaDB 0.4.x if singleton unfixable

**Risk 4: Coverage <85% requires significant refactoring**
- **Probability**: Low
- **Impact**: Medium
- **Mitigation**: Focus on testing critical paths, defer comprehensive coverage
- **Contingency**: Accept 80-85% coverage if tests validate core functionality

---

## Context Management Strategy

**Per-Priority Context Retention**:

**Priority 1**:
- RETAIN: Quick win implementations, validation results
- DISCARD: Pattern analysis after fixes
- ARCHIVE: Priority 1 test results (77% achievement)

**Priority 2**:
- RETAIN: API validation evidence, git integration fixes
- DISCARD: Investigation notes after resolution
- ARCHIVE: Priority 2 test results (90%+ achievement)

**Priority 3**:
- RETAIN: Isolation patterns, assertion fix patterns
- DISCARD: Individual test debugging details
- ARCHIVE: Priority 3 test results (98%+ achievement)

**Priority 4**:
- RETAIN: Production readiness checklist, deployment guide
- DISCARD: Quality metrics details
- ARCHIVE: Final test results (100% achievement)

**Token Budget Management**:
- Start: ~64K tokens free
- After Priority 1: Aggressive pruning (→ 80K free)
- After Priority 2: Comprehensive summarization (→ 90K free)
- After Priority 3: Archive everything except production docs (→ 100K free)

---

## Handoff Checkpoints

### After Priority 1 (Expected: 2-3 hours)
**Deliverable**: Quick wins complete, 77%+ pass rate
**Evidence**: Test run showing 389+ tests passing
**Decision Point**: Continue to Priority 2 or pause?

### After Priority 2 (Expected: 7-10 hours cumulative)
**Deliverable**: API validation complete, git integration working
**Evidence**: Test run showing 470+ tests passing (90%+)
**Decision Point**: Continue to Priority 3 or accept 90%+ and deploy?

### After Priority 3 (Expected: 13-20 hours cumulative)
**Deliverable**: Test quality issues fixed, 98%+ pass rate
**Evidence**: Test run showing 508+ tests passing
**Decision Point**: Polish to 100% or deploy at 98%+?

### After Priority 4 (Expected: 15-24 hours cumulative)
**Deliverable**: Production-ready system, 100% pass rate
**Evidence**: Full test suite pass, coverage report, deployment guide
**Decision Point**: Deploy to production

---

## Deployment Readiness Checklist

**Infrastructure**:
- [ ] Database migrations tested
- [ ] Environment variables configured (.env.example → .env)
- [ ] API keys verified (Tavily, OpenAI, Anthropic)
- [ ] Storage paths accessible (data/, logs/, cache/)
- [ ] Vector store initialized (ChromaDB persistent mode)

**Testing**:
- [ ] ≥95% test pass rate (487+ / 510 tests) ✅ TARGET
- [ ] Integration tests passing
- [ ] Performance benchmarks met (or baselined)
- [ ] No critical warnings in test output
- [ ] Test execution time <60 seconds

**Code Quality**:
- [ ] Coverage ≥85% (measured with pytest-cov)
- [ ] No critical linting errors (ruff/flake8)
- [ ] Type hints coverage >90% (mypy)
- [ ] No security vulnerabilities (bandit scan)
- [ ] Resource leak warnings <10

**Documentation**:
- [ ] README.md updated with setup instructions
- [ ] API documentation current (docstrings complete)
- [ ] Known issues documented (if any remain)
- [ ] Deployment guide created (Priority 4)
- [ ] Configuration examples provided

**Git Hygiene**:
- [ ] All changes committed
- [ ] Commit messages follow conventions
- [ ] No secrets in git history
- [ ] .gitignore properly configured

---

**END OF EXECUTION ROADMAP**

**Use this roadmap to guide Cycle 4+ systematic fixes.**
**Follow priority order, validate at each gate, maintain evidence-based approach.**
**Adjust estimates based on actual complexity discovered during execution.**

---

**Roadmap Version**: 2.0 (Updated from Cycle 3 learnings)
**Last Updated**: 2025-11-13 (Post-Cycle 3)
**Next Update**: After Cycle 4 completion
