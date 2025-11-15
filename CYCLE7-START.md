# Cycle 7: PROVE IT WORKS

**Directive**: Add dependencies, execute test query, verify success

**Current Reality**: Code fixes complete (Cycle 6), environment setup needed

---

## The Truth (From Cycle 6 Completion)

**What Works**:
- ✅ Config loading fixed (calls `load()` before `get_config()`)
- ✅ CostManager integrated (SessionManager + CostManager in ResearchOrchestrator)
- ✅ Budget checking implemented (`can_perform_operation()` with correct signature)
- ✅ Cost tracking implemented (`track_hop_cost()` with correct signature)
- ✅ Multi-agent validation working (Challenge Agent caught bugs)

**What's Missing**:
- ❌ Python packages not in pyproject.toml (anthropic, openai, tavily-python)
- ❌ Cannot execute research (import errors)
- ❌ Zero successful queries ever (database still empty)

**Proof Code is Fixed**:
```bash
# Config loading fix
grep "config_mgr.load()" src/aris/cli/research_commands.py
# Returns: Lines 98, 209

# CostManager integration
grep "self.cost_manager" src/aris/core/research_orchestrator.py
# Returns: Lines 84, 245, 265
```

**Proof Environment Not Ready**:
```bash
python -c "import anthropic"
# Returns: ModuleNotFoundError

sqlite3 .aris/metadata.db "SELECT COUNT(*) FROM research_sessions"
# Returns: 0
```

---

## MUST DO (Priority Order)

### Task 1: Add Dependencies (5 minutes)

**File**: `pyproject.toml`

**Add to `[tool.poetry.dependencies]` section** (after line 40):
```toml
# LLM and Research APIs
anthropic = "^0.39.0"
openai = "^1.54.0"
tavily-python = "^0.5.0"
```

**Install**:
```bash
poetry install
```

**Verify**:
```bash
python -c "import anthropic, openai; print('SUCCESS')"
# Expected: SUCCESS
```

---

### Task 2: Execute Test Query (30 minutes)

**Command**:
```bash
aris research "What is semantic search?" --depth quick
```

**Expected Output** (no errors):
- Configuration loads successfully
- Research orchestrator initializes
- Cost manager checks budget
- Executes search operations
- Tracks costs
- Generates research document

**If Error Occurs**:
- Document exact error message
- Note which step failed
- Check logs: `.aris/logs/aris.log`

---

### Task 3: Verify Success (10 minutes)

**Database Verification**:
```bash
# Check session created
sqlite3 .aris/metadata.db "SELECT COUNT(*) FROM research_sessions"
# Expected: > 0 (should return 1)

# Check cost tracked
sqlite3 .aris/metadata.db "SELECT session_id, query, total_cost FROM research_sessions"
# Expected: Shows session with query and cost > 0.0

# Check session details
sqlite3 .aris/metadata.db "SELECT * FROM research_sessions" | head -1
# Expected: Full session record
```

**Research Output Verification**:
```bash
# Check document created
ls -la research/

# Should show new .md file with recent timestamp
# Example: research/semantic_search_20251114_143022.md

# Verify content
cat research/[latest-file].md | wc -l
# Expected: > 50 lines of content

# Check content quality
head -20 research/[latest-file].md
# Expected: Research about semantic search, not empty
```

**Cost Tracking Verification**:
```bash
# Check hop costs
sqlite3 .aris/metadata.db "SELECT hop_number, tavily_cost, llm_cost FROM research_hops WHERE session_id IN (SELECT session_id FROM research_sessions ORDER BY created_at DESC LIMIT 1)"
# Expected: Shows costs per hop
```

---

## Success Criteria

**NOT**: More tests passing
**NOT**: More documentation
**YES**: ONE research query executes successfully with proof

**Evidence Required**:
- ✅ Command completes without error
- ✅ Database shows session_id with non-zero total_cost
- ✅ Research document exists and contains content
- ✅ Cost tracked for each hop
- ✅ Budget checking executed (logged)

**Screenshot or Output Capture**:
- Terminal output of successful execution
- Database query results showing session
- First 20 lines of research document

---

## Troubleshooting Guide

### Error: "ModuleNotFoundError: No module named 'anthropic'"

**Cause**: Dependencies not installed
**Fix**:
```bash
poetry install
# OR if not using poetry:
pip install anthropic openai tavily-python
```

### Error: "ConfigurationError: Configuration not loaded"

**Cause**: Code fix not applied (should not happen after Cycle 6)
**Fix**: Verify fix applied:
```bash
grep "config_mgr.load()" src/aris/cli/research_commands.py
```

### Error: "AttributeError: 'CostManager' object has no attribute 'track_operation_cost'"

**Cause**: Code fix not applied (should not happen after Cycle 6)
**Fix**: Verify fix applied:
```bash
grep "track_hop_cost" src/aris/core/research_orchestrator.py
```

### Error: "Missing API key: ARIS_TAVILY_API_KEY"

**Cause**: API keys not configured in .env
**Fix**:
```bash
# Check .env file
cat .env | grep API_KEY

# If missing, copy from .env.example and add real keys
cp .env.example .env
# Edit .env and add actual API keys
```

### Error: "Budget exceeded"

**Cause**: Budget limit too low (default $0.50)
**Fix**: Increase budget:
```bash
aris research "What is semantic search?" --depth quick --max-cost 1.0
```

### Database Empty After Execution

**Cause**: Execution failed silently or session not committed
**Check**:
```bash
# Check logs
cat .aris/logs/aris.log | tail -50

# Look for errors or session creation messages
```

---

## Expected Timeline

| Task | Time | Cumulative |
|------|------|------------|
| Add dependencies to pyproject.toml | 2 min | 2 min |
| Run `poetry install` | 3 min | 5 min |
| Execute test query | 25 min | 30 min |
| Verify database | 5 min | 35 min |
| Verify research output | 5 min | 40 min |
| Document success | 5 min | 45 min |

**Total**: 45 minutes

---

## After Success

**Next Steps** (Cycle 8):
1. Address Challenge Agent warnings:
   - Add error handling around config loading
   - Move hardcoded cost estimates to configuration
   - Implement actual API cost tracking
2. Improve budget estimation accuracy
3. Add integration tests for budget enforcement
4. Test concurrent research sessions

**But FIRST**: Complete Cycle 7 validation

---

**START**: Add dependencies to pyproject.toml
**EXECUTE**: One successful research query
**VERIFY**: Database has session with non-zero cost, document created
**PROVE**: System works end-to-end

---

**NO MORE**:
- Fixing tests without runtime validation
- Writing documentation without proof
- Claiming success without evidence

**ONLY**:
- Add dependencies (5 min)
- Execute query (30 min)
- Verify success (10 min)
- PROVE IT WORKS
