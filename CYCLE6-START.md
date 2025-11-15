# Cycle 6: FIX THE ACTUAL BUGS

**Directive**: Stop testing, stop documenting - FIX THE SYSTEM

**Current Reality**: ARIS cannot execute research queries. Period.

---

## The Truth (From Cycle 4-5 Validation)

**What Works**:
- ✅ Test suite (95%+ passing)
- ✅ Code architecture
- ✅ Database schema
- ✅ CLI framework

**What's Broken**:
- ❌ Cannot execute research (config bug blocks execution)
- ❌ CostManager never connected (exists but unused)
- ❌ Zero successful queries ever (database empty)

**Proof System Doesn't Work**:
```bash
aris research "test" → Error: Configuration not loaded
sqlite3 .aris/metadata.db "SELECT COUNT(*) FROM research_sessions" → 0
grep "self.cost_manager" research_orchestrator.py → NO MATCHES
```

---

## MUST FIX (Priority Order)

### Fix 1: Configuration Bug (15 minutes)

**File**: `src/aris/cli/research_commands.py:97`

**Current (BROKEN)**:
```python
config = ConfigManager.get_instance().get_config()
```

**Fix**:
```python
config_mgr = ConfigManager.get_instance()
config = config_mgr.load()  # MUST LOAD FIRST
```

**Test**: `aris research "test" --depth quick`

---

### Fix 2: Connect CostManager (4 hours)

**File**: `src/aris/core/research_orchestrator.py`

**Add to __init__**:
```python
self.cost_manager = CostManager(self.session_manager)
```

**Add cost tracking in execute_research**:
```python
# After each hop
await self.cost_manager.track_hop_cost(
    session_id=session.session_id,
    hop_number=hop_num,
    searches=search_count,
    tokens=token_count
)

# Before expensive operations
can_proceed = await self.cost_manager.can_perform_operation(
    session_id=session.session_id,
    estimated_cost=estimated_cost
)
if not can_proceed:
    raise BudgetExceededError("Budget exceeded")
```

**Test**: Check database shows non-zero costs

---

### Fix 3: Execute ONE Successful Query (2 hours)

**Setup**:
1. Create `.env` with API keys
2. Install missing dependencies
3. Run: `aris research "What is semantic search?" --depth quick`

**Verify Success**:
```bash
# Database has session
sqlite3 .aris/metadata.db "SELECT * FROM research_sessions"

# Document created
ls -la research/

# Cost tracked
sqlite3 .aris/metadata.db "SELECT total_cost FROM research_sessions"
```

---

## Success Criteria

**NOT**: Tests passing
**NOT**: Documentation complete
**YES**: ONE research query executes successfully with proof

**Evidence Required**:
- Screenshot of successful execution
- Database showing session data
- Generated research document
- Non-zero cost tracked

---

**START**: Fix bug #1 (config.load), then #2 (CostManager), then #3 (test query)
**STOP**: Making documentation, fixing tests without runtime validation
