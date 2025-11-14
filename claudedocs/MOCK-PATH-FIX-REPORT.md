# DocumentStore Mock Path Fix Report

## Issue
After Phase 1b circular import fix, DocumentStore import path changed causing test failures with AttributeError on mock operations.

## Root Cause
- **Old behavior**: DocumentStore was imported at module level in research_orchestrator.py
- **New behavior**: DocumentStore is imported inside `__init__` method from `aris.storage` (line 77)
- **Impact**: Mock path `"aris.core.research_orchestrator.DocumentStore"` no longer valid because DocumentStore is not a module-level attribute

## Changes Made

### tests/unit/test_research_orchestrator.py
**Location**: Lines 50, 61

**Before**:
```python
patch("aris.core.research_orchestrator.DocumentStore", ...)
```

**After**:
```python
patch("aris.storage.DocumentStore", ...)
```

**Evidence**: 2 mock paths updated

### tests/unit/test_cli.py
**Status**: ✅ Already correct - uses `patch('aris.cli.show_command.DocumentStore')`
**Reason**: DocumentStore is imported at module level in show_command.py (line 11)

## Verification

### Mock Path Pattern
```python
# Correct pattern: Mock where the name is bound, not where it's defined
# Since research_orchestrator.py does: from aris.storage import DocumentStore
# The mock path must be: "aris.storage.DocumentStore"
```

### Git Diff
```diff
-         patch("aris.core.research_orchestrator.DocumentStore", return_value=mock_document_store), \
+         patch("aris.storage.DocumentStore", return_value=mock_document_store), \

-             patch("aris.core.research_orchestrator.DocumentStore"), \
+             patch("aris.storage.DocumentStore"), \
```

## Files Updated
1. tests/unit/test_research_orchestrator.py: 2 mock paths fixed
   - Line 50: orchestrator fixture
   - Line 61: test_initialization method

## Evidence Count
- **Total mock paths found**: 3
- **Mock paths fixed**: 2
- **Mock paths already correct**: 1 (test_cli.py)

## Validation Criteria Status
- ✅ All DocumentStore mock paths updated
- ✅ No references to old 'aris.storage.document_store' path in mocks (none existed)
- ✅ File:line references documented above
- ✅ Git diff showing path updates only

## Next Steps
The AttributeError for DocumentStore mocks is now fixed. Tests may still have other unrelated issues (e.g., ChromaDB deprecation warnings) that are separate concerns.
