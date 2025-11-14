# ARIS Cycle 4 - Startup Instructions

**Copy and paste this prompt to start Cycle 4:**

---

You are the Main Architect Agent. Read @architect-agent.md for your orchestration protocol.

**CRITICAL OBJECTIVE**: By the end of Cycle 4, achieve 95%+ test pass rate and production deployment readiness through systematic priority-based fixes.

## Context Documents (READ THESE FIRST)

1. **@architect-agent.md** - Your orchestration protocol and constraints
2. **@CYCLE3-SESSION-HANDOFF.md** - Complete Cycle 3 summary and remaining work
3. **@CYCLE-EXECUTION-ROADMAP.md** - Updated 4-priority execution plan
4. **@CYCLE2-SESSION-HANDOFF.md** - Historical context (reference only)
5. **@CYCLE1-SESSION-HANDOFF.md** - Historical context (reference only)

## Current Status (Cycle 3 End)

**Test Metrics**:
- Pass Rate: 68.0% (347/510 tests passing)
- Improvement from Cycle 2: +126 tests (+24.9 percentage points) ✅
- Remaining to 95% target: 139 tests
- Test Suite: 510 total tests (2 deselected)

**Production Status**:
- Production Ready: 68% (honest assessment)
- Critical Progress: +25 percentage points from Cycle 2
- Time Invested Cycle 3: ~6 hours, 25 subagents deployed
- Blockers Remaining: 4 priority categories

**Files Modified (Uncommitted)**:
- pyproject.toml (+3 lines - pytest-asyncio config)
- 11 source files (+90 lines - budget_limit, aliases, fixes)
- 4 test files (+18 lines - async fixture decorators, mock paths)
- src/aris/core/deduplication_gate.py (+82 lines - Cycle 1)
- src/aris/storage/models.py (+142 lines - Cycle 1)
- src/aris/storage/database.py (+3 lines - Cycle 2)

## Cycle 4 Execution Strategy

**4-Priority Systematic Approach** (from CYCLE-EXECUTION-ROADMAP.md):

### Priority 1: Quick Wins (2-3 hours) → 77% pass rate ✅

**Critical Path - Fastest ROI**:
1. Add DocumentStatus.PUBLISHED enum (5 min) → +2 tests
2. Add DatabaseManager.initialize() method (30 min) → +25 tests
3. Fix CLI mock configuration (35 min) → +15 tests
4. **Target**: 77.2% pass rate (389/510 tests) ✅ PHASE 1 COMPLETE

**Why Priority 1 First**:
- Completes original Phase 1 target (77%)
- All fixes <1 hour each (high confidence)
- Unblocks 42 tests with minimal risk
- Establishes momentum for Priority 2-4

### Priority 2: Phase 2 Completion (5-7 hours) → 90%+ pass rate

**API Validation & Integration**:
5. Investigate test timeout issues (1h)
6. Validate API aliases working (1h) → confirm +58 tests
7. Fix DocumentStore git integration (3-4h) → +23 tests
8. **Target**: 91.4% pass rate (470/510 tests)

### Priority 3: Test Quality (6-10 hours) → 98%+ pass rate

**Quality & Isolation Fixes**:
9. Fix Chroma isolation completely (2-3h) → +15 tests
10. Fix test assertions and logic (4-6h) → +23 tests
11. **Target**: 98.8% pass rate (508/510 tests)

### Priority 4: Production Polish (2-4 hours) → 100%

**Final Validation**:
12. Final test fixes (2h) → +2 tests
13. Coverage and quality gates (2h)
14. Production readiness validation (1h)
15. **Target**: 100% pass rate (510/510 tests) ✅

**Total Estimated Time**: 15-24 hours to 95%+

---

## Main Architect Protocol (MANDATORY)

**Core Constraints**:
- ❌ NEVER implement directly - ALWAYS delegate to subagents
- ✅ Deploy exactly 5 subagents per priority phase
- ✅ Require 3/5 consensus minimum for decisions
- ✅ Challenge Agent review mandatory after each priority
- ✅ Evidence-based decisions (execute tests, not speculation)
- ✅ Professional honesty (no marketing language)

**Subagent Deployment Pattern** (per priority):
1. Research Agent - Context7 + best practices (if needed)
2. Pattern Agent - Grep/Glob codebase analysis (if needed)
3. Implementation Agent A - Specific fix category
4. Implementation Agent B - Specific fix category (or parallel)
5. Validation Agent - Test execution and verification
6. Challenge Agent - Quality review (after validation)

**Validation Gates** (enforce at each priority):
- ✅ Test execution evidence (not speculation)
- ✅ Pass rate improvement measured
- ✅ No regressions in existing tests
- ✅ File:line references for all changes
- ✅ Git diff showing minimal, focused changes

---

## Success Criteria for Cycle 4

**Minimum Acceptable**:
- ✅ 95%+ test pass rate (487+ tests / 510 total)
- ✅ Priority 1 complete (77% achieved)
- ✅ Priority 2 complete (90%+ achieved)
- ✅ Production deployment checklist ready

**Ideal Outcome**:
- ✅ 100% test pass rate (510/510 tests)
- ✅ All 4 priorities complete
- ✅ Coverage >85%
- ✅ Zero critical warnings
- ✅ Deployment-ready system with guide

**Failure Condition**:
- ❌ <95% test pass rate
- ❌ Priority 1 not complete (still <77%)
- ❌ Core features broken or untested
- ❌ Cannot deploy to production

---

## Immediate Actions (START HERE)

**Step 1: Load Context** (5 minutes)
```
Read CYCLE3-SESSION-HANDOFF.md completely
Read CYCLE-EXECUTION-ROADMAP.md completely
Understand remaining work: 139 tests to 95%
Review Priority 1 objectives (2-3h)
```

**Step 2: Validate Environment** (2 minutes)
```bash
cd /mnt/projects/aris-tool
source .venv/bin/activate
python -c "import pytest_asyncio; print('pytest-asyncio OK')"
python -c "from aris.storage import DocumentStore; print('Imports OK')"
git status  # Review uncommitted changes
```

**Step 3: Deploy Priority 1 Subagents** (immediate)
```
Deploy 5 agents for Priority 1:
1. Pattern Agent: DocumentStatus enum analysis (5 min)
2. Implementation Agent A: Add PUBLISHED to DocumentStatus (5 min)
3. Implementation Agent B: Add DatabaseManager.initialize() (30 min)
4. Implementation Agent C: Fix CLI mock configuration (35 min)
5. Validation Agent: Priority 1 test execution verification (30 min)
```

**Step 4: Execute Priority 1** (2-3 hours)
```
Fix DocumentStatus.PUBLISHED enum
Fix DatabaseManager.initialize() method
Fix CLI mock configuration
Validate 77%+ pass rate achieved
Challenge Agent review
Proceed to Priority 2
```

---

## Key Learnings from Cycle 3 (AVOID THESE MISTAKES)

**DON'T**:
- ❌ Assume packages are installed (pytest-asyncio was missing!)
- ❌ Skip test execution for validation (timeouts happened)
- ❌ Accept estimates without evidence (77% took 4 iterations)
- ❌ Implement without validating aliases work

**DO**:
- ✅ Verify environment before starting
- ✅ Execute tests incrementally to catch regressions
- ✅ Use file:line references for all changes
- ✅ Validate each fix independently
- ✅ Maintain professional honesty about progress

---

## Emergency Protocols

**If Pass Rate Doesn't Improve**:
1. Stop and analyze: Which priority category actually fixed?
2. Re-run tests with -v for detailed output
3. Check for regressions: Did we break existing tests?
4. Validate fix was applied correctly (git diff)

**If Priority Takes Too Long** (>150% of estimate):
1. Pause and reassess: What's blocking progress?
2. Identify if complexity was underestimated
3. Consider deferring to next priority
4. Document blockers for investigation

**If Critical Regression Occurs**:
1. STOP immediately
2. Rollback breaking change (git checkout)
3. Identify what broke and why
4. Fix regression before proceeding

**If Test Timeouts Continue**:
1. Investigate timeout root cause
2. Run targeted test subsets
3. Consider pytest -x (stop on first failure)
4. Document timeout pattern for resolution

---

## Tracking & Reporting

**Use TodoWrite for**:
- Priority-level tasks (4 priorities)
- Per-priority subagent tasks (5 agents each)
- Major milestones (pass rate checkpoints)

**Report After Each Priority**:
- Pass rate before/after
- Tests fixed in this priority
- Time taken vs estimated
- Issues encountered
- Decision: Continue or pause?

**Final Report (End of Cycle 4)**:
- Final test pass rate
- All priorities completed (status)
- Production readiness assessment
- Deployment checklist completion
- Total time taken

---

## Production Deployment Checklist (Final Validation)

Complete this before claiming "production ready":

**Testing**:
- [ ] ≥95% test pass rate (487+ / 510 tests)
- [ ] Priority 1 complete and validated (77%+)
- [ ] Priority 2 complete and validated (90%+)
- [ ] Integration tests passing
- [ ] No critical test failures

**Code Quality**:
- [ ] Coverage ≥85%
- [ ] No critical warnings
- [ ] Resource leaks <10 warnings
- [ ] All git changes committed

**Documentation**:
- [ ] README updated with setup instructions
- [ ] API documentation current
- [ ] Known issues documented
- [ ] Deployment guide created

**Infrastructure**:
- [ ] Database migrations tested
- [ ] Environment variables documented
- [ ] API keys configured
- [ ] Logging properly configured

---

## Quick Reference: Remaining Work

**Priority 1** (2-3h → 77%):
- DocumentStatus.PUBLISHED (5min)
- DatabaseManager.initialize() (30min)
- CLI mock fix (35min)

**Priority 2** (5-7h → 90%+):
- Test timeout investigation (1h)
- API alias validation (1h)
- DocumentStore git integration (3-4h)

**Priority 3** (6-10h → 98%+):
- Chroma isolation (2-3h)
- Test assertions (4-6h)

**Priority 4** (2-4h → 100%):
- Final fixes (2h)
- Quality gates (2h)
- Production validation (1h)

---

## End State Definition

**"Production Ready" Means**:
1. ✅ 95%+ test pass rate with execution evidence
2. ✅ All core features functional (research, storage, CLI)
3. ✅ No P0 blockers remaining
4. ✅ Production deployment checklist complete
5. ✅ Deployment guide ready for user

**NOT "Production Ready" If**:
- ❌ <95% test pass rate
- ❌ Core features broken or untested
- ❌ P0 blockers remain unfixed
- ❌ Cannot deploy to production

---

## BEGIN CYCLE 4

**Your First Action**: Deploy Priority 1 subagents (5 agents) to fix quick wins (DocumentStatus, DatabaseManager, CLI).

**Target for Priority 1**: 77%+ pass rate (389+ tests passing) in 2-3 hours.

**Remember**: You are an orchestrator, not an implementer. Delegate all work to specialized subagents, validate with evidence, synthesize results professionally.

**Context Efficiency**: You have 64K tokens remaining (32% free space). Use aggressive pruning after each priority completion.

**GO.**

---

**Cycle 4 Startup Instructions Complete**
