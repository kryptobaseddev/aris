# CLI Test Failures - Quick Fix Summary

**Date**: 2025-11-13
**Total Failures**: 15 tests (9 unit + 6 integration)
**Fix Time**: 35 minutes
**Status**: Ready to implement

---

## Root Causes (2 Issues)

1. **ConfigManager Mock Issue** (13 tests) - Mock doesn't set `_config` attribute
2. **Missing Session Start** (2 tests) - Tests expect command that doesn't exist

---

## Quick Fixes

### Fix 1: Add `_config` to Mock (15 min → 7 tests)
```python
# File: tests/unit/test_cli.py:31-40
instance._config = mock_config  # ADD THIS LINE
```

### Fix 2: Update Session Tests (5 min → 2 tests)
```python
# Change: cli, ["session", "start"]
# To:     cli, ["session", "list"]
```

### Fix 3: Integration Reset (15 min → 6 tests)
Investigate why ConfigManager singleton not properly reset between integration tests.

---

## Test Commands

```bash
# Validate unit tests
source .venv/bin/activate
python -m pytest tests/unit/test_cli.py -v

# Validate integration tests
python -m pytest tests/integration/test_cli_integration.py -v

# Full suite
python -m pytest tests/ -v
```

---

## Files to Modify

1. `tests/unit/test_cli.py` (lines 31-40, 199)
2. `tests/integration/test_cli_integration.py` (line 148)
3. Possibly: integration test fixture (lines 30-36)

---

## Success Criteria

- All 15 tests pass
- No new failures
- Execution time < 5s (unit), < 10s (integration)

---

**Full Details**: See `CLI-FAILURE-DIAGNOSIS.md` and `CLI-FIX-ROADMAP.md`
