# Production Blockers - Action Checklist

**Status**: ❌ 3 CRITICAL BLOCKERS REMAIN
**Time to Production**: 3-5 days
**Last Updated**: 2025-11-14

---

## Critical Path (Must Complete in Order)

### ⚠️ BLOCKER 1: CostManager Integration
**Status**: ❌ NOT STARTED
**Severity**: CRITICAL
**Time**: 4 hours
**Blocks**: Runtime validation, budget testing

**Action Items**:
- [ ] Open `src/aris/core/research_orchestrator.py`
- [ ] Add to `__init__`: `self.cost_manager = CostManager(self.session_manager)`
- [ ] Add after each hop: `await self.cost_manager.track_hop_cost(session_id, hop_num, searches, tokens)`
- [ ] Add pre-check: `can_proceed = await self.cost_manager.can_perform_operation(...)`
- [ ] Write integration test
- [ ] Verify: `grep -r "self.cost_manager" research_orchestrator.py` returns results

**Success Criteria**:
- CostManager instantiated in ResearchOrchestrator
- Hop costs tracked in database after research execution
- Budget checks called before expensive operations

---

### ⚠️ BLOCKER 2: Runtime Validation
**Status**: ❌ NOT STARTED (blocked by BLOCKER 1)
**Severity**: CRITICAL
**Time**: 6 hours
**Blocks**: Production deployment

**Prerequisites**:
- [ ] BLOCKER 1 completed
- [ ] API keys obtained (see below)

**Action Items**:
- [ ] Create `.env` file with keys (see API Keys section)
- [ ] Execute: `aris research "What are transformer architectures?" --depth quick`
- [ ] Verify success: Document created in `research/` directory
- [ ] Check database: `sqlite3 .aris/metadata.db "SELECT COUNT(*) FROM research_sessions;"`
- [ ] Verify result: Should return 1 (not 0)
- [ ] Check costs: `SELECT total_cost FROM research_sessions;`
- [ ] Verify cost tracking: Should return non-zero value (e.g., 0.03)

**Test Queries** (Execute all 3):
1. **Quick**: "Best practices for Python error handling"
2. **Standard**: "Compare React vs Vue for enterprise applications"
3. **Deep**: "Evolution of transformer architectures in NLP"

**Success Criteria**:
- At least 1 successful research execution
- Database contains: sessions > 0, documents > 0, hops > 0
- Costs tracked: total_cost > 0
- Document files created in research/ directory

---

### ⚠️ BLOCKER 3: Budget Enforcement
**Status**: ❌ NOT STARTED (blocked by BLOCKER 1, 2)
**Severity**: CRITICAL (FINANCIAL RISK)
**Time**: 2 hours
**Blocks**: Safe deployment

**Prerequisites**:
- [ ] BLOCKER 1 completed
- [ ] BLOCKER 2 completed

**Action Items**:
- [ ] Set tight budget: `export ARIS_BUDGET_LIMIT=0.05`
- [ ] Execute expensive query: `aris research "Comprehensive analysis of AI safety research trends 2020-2024" --depth deep`
- [ ] Verify: BudgetExceededError raised
- [ ] Check database: `SELECT total_cost FROM research_sessions ORDER BY id DESC LIMIT 1;`
- [ ] Verify: total_cost <= 0.05
- [ ] Check console: Budget warnings logged at 75%, 90%, 100%

**Success Criteria**:
- Budget limit prevents cost overruns
- BudgetExceededError raised when limit exceeded
- Warnings logged at 75% and 90% thresholds
- Database total_cost never exceeds budget_limit

---

## API Keys (Required for BLOCKER 2)

Create `.env` file in project root:
```bash
# Required for research execution
ARIS_TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxx
ARIS_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
ARIS_OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# Optional - budget controls
ARIS_BUDGET_LIMIT=0.50
ARIS_MONTHLY_BUDGET_LIMIT=50.00
```

**Where to Get Keys**:
- Tavily: https://app.tavily.com/
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/

---

## High Priority (Staging Blockers)

### 🔶 HIGH 1: API Connectivity Verification
**Status**: ❌ NOT STARTED
**Severity**: HIGH
**Time**: 3 hours

**Action Items**:
- [ ] Test Tavily: Execute search, verify results returned
- [ ] Test Anthropic: Execute LLM call, verify response
- [ ] Test OpenAI: Execute validation call, verify response
- [ ] Test error handling: Use invalid keys, verify graceful failure
- [ ] Check rate limiting: Execute 10 rapid queries, verify throttling

**Success Criteria**: All 3 APIs return successful responses

---

### 🔶 HIGH 2: Vector Store Fixes
**Status**: ❌ NOT STARTED
**Severity**: HIGH (degrades deduplication)
**Time**: 6 hours

**Action Items**:
- [ ] Install ChromaDB build tools: `sudo apt-get install build-essential g++`
- [ ] Or use pre-built: `pip install chromadb --only-binary :all:`
- [ ] Fix 37 vector store test failures
- [ ] Re-run: `python -m pytest tests/unit/storage/test_vector_store.py -v`
- [ ] Verify: 0 failures
- [ ] Test deduplication with vector mode enabled
- [ ] Compare: Similarity scores (target >0.90 for identical content)

**Success Criteria**:
- All 37 vector store tests passing
- Deduplication accuracy >90% (up from 81.8%)

---

## Medium Priority (Quality Issues)

### 🔷 MEDIUM 1: Fix pytest Dependencies
**Time**: 5 minutes
```bash
poetry add --group dev pytest pytest-asyncio pytest-cov
poetry install
```

### 🔷 MEDIUM 2: Fix ConfigManager Bug
**Time**: 15 minutes
**File**: `src/aris/cli/research_command.py:97`
```python
# BEFORE
config = ConfigManager.get_instance().get_config()

# AFTER
config_mgr = ConfigManager.get_instance()
config = config_mgr.load()
```

### 🔷 MEDIUM 3: Fix Test Failures
**Time**: 8-12 hours
**Target**: 95%+ pass rate (currently 84%)

- [ ] Fix 3 ResearchOrchestrator format string errors
- [ ] Fix 16 other failing tests
- [ ] Re-run full suite: `python -m pytest tests/ -v`
- [ ] Verify: >325/342 tests passing

---

## Verification Commands

### Check Integration Status
```bash
# Verify CostManager integrated
grep -r "self.cost_manager" src/aris/core/research_orchestrator.py

# Check database state
sqlite3 .aris/metadata.db <<EOF
SELECT COUNT(*) as sessions FROM research_sessions;
SELECT COUNT(*) as documents FROM documents;
SELECT COUNT(*) as hops FROM research_hops;
SELECT SUM(cost) as total_cost FROM research_hops;
EOF

# Run tests
python -m pytest tests/unit -v --tb=short

# Check package version
aris --version
```

### Monitor Live Execution
```bash
# Terminal 1: Watch logs
tail -f .aris/logs/*.log

# Terminal 2: Execute research
aris research "test query" --depth quick -v

# Terminal 3: Monitor database
watch -n 1 'sqlite3 .aris/metadata.db "SELECT * FROM research_sessions;"'
```

---

## Definition of Done

### For Staging Deployment
- [x] BLOCKER 1: CostManager integrated
- [x] BLOCKER 2: 1+ successful research execution
- [x] BLOCKER 3: Budget enforcement proven
- [x] API connectivity verified
- [ ] Deduplication tested (degraded mode acceptable)
- [ ] Error logs reviewed (no critical errors)

### For Production Deployment
- [x] All staging requirements
- [x] Vector store operational (37 tests passing)
- [x] 95%+ test pass rate (325+ tests)
- [x] Security audit complete (bandit clean)
- [x] Performance benchmarks acceptable
- [x] Load testing complete (10+ concurrent users)
- [x] Monitoring dashboard configured
- [x] Rollback plan documented

---

## Current Status Summary

| Requirement | Status | Progress |
|-------------|--------|----------|
| CostManager Integration | ❌ Not Started | 0% |
| Runtime Validation | ❌ Blocked | 0% |
| Budget Enforcement | ❌ Blocked | 0% |
| API Connectivity | ❌ Not Started | 0% |
| Vector Store | ❌ Not Started | 0% (37 failures) |
| Test Suite | ⚠️ Partial | 84% (289/342) |
| **Overall Readiness** | **❌ NOT READY** | **~35%** |

---

## Quick Start Guide

**If you have 4 hours right now**:
1. Fix BLOCKER 1 (CostManager integration) - 4 hours
2. Get API keys - 30 minutes
3. Execute first test query - 30 minutes
4. Validate database writes - 15 minutes

**After 5 hours**: System will be STAGING READY (with degraded deduplication)

**If you have 3 days**:
- Day 1: Fix all 3 CRITICAL blockers
- Day 2: Fix HIGH priority issues (API + vector store)
- Day 3: Security audit, final validation

**After 3 days**: System will be PRODUCTION READY

---

## Who to Contact

**Questions about**:
- Cost tracking: See `claudedocs/COST-TRACKING-VALIDATION-REPORT.md`
- Deduplication: See `claudedocs/DEDUPLICATION-VALIDATION-REPORT.md`
- Full assessment: See `claudedocs/PRODUCTION-READINESS-ASSESSMENT.md`
- Quick summary: See `PRODUCTION-READINESS-EXECUTIVE-SUMMARY.md`

**Report Issues**: Create ticket with:
- Blocker number (e.g., "BLOCKER 1: CostManager")
- Error message or unexpected behavior
- Steps to reproduce
- Expected vs actual result

---

**Last Updated**: 2025-11-14
**Next Review**: After BLOCKER 1 completion
**Target Production Date**: 2025-11-19 (5 days from now)
