# CLI Test Failures - Root Cause Analysis

**Date**: 2025-11-13
**Test Suite**: `tests/unit/test_cli.py` + `tests/integration/test_cli_integration.py`
**Total Failures**: 15 (9 unit + 6 integration)
**Investigation Time**: 1 hour

---

## Executive Summary

All 15 CLI test failures stem from **2 primary root causes**:

1. **Configuration Loading Issue** (13 tests) - Commands fail because `ConfigManager.get_config()` requires `load()` to be called first
2. **Missing Session Subcommands** (2 tests) - Test expects `session start` but only implemented subcommands are: list, show, resume, stats, export, delete

**Critical Finding**: The mocking strategy in tests doesn't properly initialize the ConfigManager singleton, causing all commands that depend on configuration to fail with "Configuration not loaded" errors.

---

## Failure Categorization

### Category 1: Configuration Not Loaded (13 tests - HIGH PRIORITY)

**Root Cause**: `ConfigManager.get_config()` raises `ConfigurationError` when configuration hasn't been loaded via `load()` first.

**Affected Tests**:

#### Unit Tests (7)
1. `TestInitCommand::test_init_basic` - Exit code 0 but wrong output ("already initialized" warning)
2. `TestInitCommand::test_init_with_profile` - Exit code 0 but missing "production" in output
3. `TestStatusCommand::test_status_basic` - Exit code 1 (ConfigurationError)
4. `TestStatusCommand::test_status_json` - Exit code 1 (ConfigurationError)
5. `TestShowCommand::test_show_metadata_only` - Exit code 1 (ConfigurationError)
6. `TestPlaceholderCommands::test_research_command` - Exit code 1 (ConfigurationError)
7. `TestDBCommands::test_db_status` - Exit code 1 (ConfigurationError)
8. `TestGitCommands::test_git_status` - Exit code 1 (ConfigurationError)

#### Integration Tests (6)
1. `TestCLIIntegration::test_full_initialization_workflow` - Exit code 1 (init fails)
2. `TestCLIIntegration::test_status_after_init` - Exit code 1 (status after init fails)
3. `TestCLIIntegration::test_json_output_mode` - Exit code 1 (JSON output fails)
4. `TestCLIIntegration::test_db_commands_workflow` - Exit code 1 (db status fails)
5. `TestCLIIntegration::test_placeholder_commands_accessible` - Exit code 1 (research fails)
6. `TestCLIOutputFormats::test_verbose_output` - Exit code 1 (status fails)

**Example Error Stack**:
```python
File "src/aris/cli/status_command.py", line 37, in status
    config = config_manager.get_config()
File "src/aris/core/config.py", line 168, in get_config
    raise ConfigurationError("Configuration not loaded. Call load() first.")
```

**File References**:
- `/mnt/projects/aris-tool/src/aris/core/config.py:168` - ConfigManager.get_config()
- `/mnt/projects/aris-tool/src/aris/cli/status_command.py:37` - status command
- `/mnt/projects/aris-tool/src/aris/cli/research_commands.py:51-59` - research command
- `/mnt/projects/aris-tool/src/aris/cli/db_commands.py` - db commands
- `/mnt/projects/aris-tool/src/aris/cli/git_commands.py` - git commands
- `/mnt/projects/aris-tool/src/aris/cli/show_command.py` - show command

---

### Category 2: Missing Session Subcommands (2 tests - MEDIUM PRIORITY)

**Root Cause**: Test expects `session start` command, but it doesn't exist. Implemented subcommands are:
- `list`, `show`, `resume`, `stats`, `export`, `delete`

**Affected Tests**:
1. `TestPlaceholderCommands::test_session_commands` - Exit code 2 (no such command 'start')
2. `TestCLIIntegration::test_placeholder_commands_accessible` - Exit code 2 (no such command 'start')

**Error**:
```
Error: No such command 'start'.
```

**File References**:
- `/mnt/projects/aris-tool/src/aris/cli/session_commands.py:17-33` - session group definition
- `/mnt/projects/aris-tool/tests/unit/test_cli.py:199` - expects 'session start'
- `/mnt/projects/aris-tool/tests/integration/test_cli_integration.py:148` - expects 'session start'

---

## Fix Plan (Prioritized by Impact & Complexity)

### Phase 1: Quick Wins (30 minutes - fixes 13 tests)

**Fix 1.1: Mock ConfigManager Properly in Unit Tests**
- **File**: `tests/unit/test_cli.py:31-40`
- **Action**: Update `mock_config_manager` fixture to call `load()` and set `_config` attribute
- **Complexity**: LOW
- **Impact**: Fixes 7 unit tests
- **Code Change**:
```python
@pytest.fixture
def mock_config_manager(mock_config):
    """Create mock configuration manager."""
    with patch('aris.cli.init_command.ConfigManager') as mock:
        instance = Mock()
        instance.get_config.return_value = mock_config
        instance.load.return_value = mock_config
        instance._config = mock_config  # ADD THIS
        instance.validate.return_value = {"valid": True, "errors": [], "warnings": []}
        instance._profile = ConfigProfile.DEVELOPMENT
        mock.get_instance.return_value = instance
        yield mock
```

**Fix 1.2: Fix Integration Test Initialization**
- **File**: `tests/integration/test_cli_integration.py:30-36`
- **Action**: Ensure `reset_config()` fixture properly resets AND loads config
- **Complexity**: LOW
- **Impact**: Fixes 6 integration tests
- **Code Change**: Investigate why ConfigManager singleton isn't properly initialized after reset

**Fix 1.3: Add Missing `_config` Attribute Check**
- **File**: `src/aris/core/config.py:168`
- **Action**: Consider if `get_config()` should auto-load with defaults instead of failing
- **Complexity**: MEDIUM (architectural decision)
- **Impact**: Makes CLI more resilient
- **Decision Required**: Should we auto-load config or enforce explicit initialization?

---

### Phase 2: Session Command Fix (15 minutes - fixes 2 tests)

**Fix 2.1: Either Add or Update Test**

**Option A - Add Missing Command** (if needed for Wave 4):
- **File**: `src/aris/cli/session_commands.py`
- **Action**: Add `@session.command()` for `start` subcommand
- **Complexity**: LOW
- **Impact**: Fixes 2 tests + adds functionality

**Option B - Update Test Expectations** (if command not needed):
- **File**: `tests/unit/test_cli.py:199` and `tests/integration/test_cli_integration.py:148`
- **Action**: Change `session start` to `session list` in test
- **Complexity**: TRIVIAL
- **Impact**: Fixes 2 tests
- **Recommendation**: **Choose this** - tests should match implemented commands

---

## Estimated Fix Times

| Phase | Task | Complexity | Est. Time | Tests Fixed |
|-------|------|------------|-----------|-------------|
| 1.1 | Fix unit test mocking | LOW | 15 min | 7 unit tests |
| 1.2 | Fix integration reset | LOW | 15 min | 6 integration tests |
| 2.1 | Update session tests | TRIVIAL | 5 min | 2 tests |
| **TOTAL** | | | **35 minutes** | **15 tests** |

---

## Implementation Order (by ROI)

1. **Fix 1.1** - Unit test mock (15 min → 7 tests fixed) - **HIGHEST ROI**
2. **Fix 2.1** - Update session tests (5 min → 2 tests fixed) - **QUICK WIN**
3. **Fix 1.2** - Integration reset (15 min → 6 tests fixed) - **COMPLETES SUITE**

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Mock doesn't match real behavior | MEDIUM | Add integration tests to verify real ConfigManager flow |
| Auto-loading config breaks assumptions | HIGH | DO NOT implement auto-load without design review |
| Session start actually needed | LOW | Check Wave 4 PRD before removing test |
| Circular imports from config changes | LOW | ConfigManager already singleton, minimal risk |

---

## Validation Criteria

After fixes, verify:

1. ✅ All 16 unit tests pass: `pytest tests/unit/test_cli.py -v`
2. ✅ All 13 integration tests pass: `pytest tests/integration/test_cli_integration.py -v`
3. ✅ No new failures introduced: `pytest tests/ -v`
4. ✅ ConfigManager mock behavior matches real implementation
5. ✅ Session commands test matches available subcommands

---

## Deferred Decisions

**Question for Product/Architecture**:
1. Should `ConfigManager.get_config()` auto-load with defaults if not loaded?
   - **Pro**: More convenient CLI usage, fewer errors
   - **Con**: Hidden behavior, harder to debug, less explicit
   - **Current behavior**: Explicit error requiring `load()` first
   - **Recommendation**: Keep explicit - better for testing and debugging

2. Should we implement `session start` command for Wave 4?
   - **Current state**: Not implemented, but tests expect it
   - **Options**: Add command OR update tests
   - **Recommendation**: Check Wave 4 PRD - if not needed, update tests

---

## Files Requiring Changes

### Tests (3 files)
1. `/mnt/projects/aris-tool/tests/unit/test_cli.py:31-40` - mock_config_manager fixture
2. `/mnt/projects/aris-tool/tests/unit/test_cli.py:199` - session start test
3. `/mnt/projects/aris-tool/tests/integration/test_cli_integration.py:148` - session start integration test

### Source (0-1 files - optional)
1. `/mnt/projects/aris-tool/src/aris/cli/session_commands.py` - IF adding start command

---

## Next Steps

1. **Review this diagnosis** with team
2. **Decide** on session start command (add or remove from tests)
3. **Decide** on ConfigManager auto-load behavior (keep explicit or add auto-load)
4. **Implement** Fix 1.1 (unit test mock)
5. **Implement** Fix 2.1 (session test update)
6. **Implement** Fix 1.2 (integration test reset)
7. **Validate** all tests pass
8. **Document** any architectural decisions made

---

## Appendix: Test Execution Evidence

```bash
# Unit Tests Results (9 failures)
source .venv/bin/activate
python -m pytest tests/unit/test_cli.py -v
# 7 passed, 9 failed

# Integration Tests Results (6 failures)
python -m pytest tests/integration/test_cli_integration.py -v
# 7 passed, 6 failed

# Total: 14 passed, 15 failed (not 24 as initially reported)
```

**Note**: Initial report mentioned 24 failing tests. Actual count is 15 CLI-related failures.
