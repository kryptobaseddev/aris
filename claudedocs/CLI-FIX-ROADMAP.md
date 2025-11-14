# CLI Test Fix Implementation Roadmap

**Status**: Ready for Implementation
**Estimated Total Time**: 35 minutes
**Tests to Fix**: 15 (9 unit + 6 integration)

---

## Implementation Checklist

### ✅ Pre-Implementation
- [x] Diagnosis complete
- [x] Root causes identified
- [x] Fix plan prioritized
- [ ] Team review of diagnosis
- [ ] Decision on session start command
- [ ] Decision on ConfigManager auto-load

---

## Fix Sequence

### Fix 1: Unit Test Mock (15 minutes) → 7 tests fixed

**File**: `tests/unit/test_cli.py`
**Lines**: 31-40
**Current Problem**: Mock ConfigManager doesn't set `_config` attribute, causing `get_config()` to fail

**Implementation**:
```python
@pytest.fixture
def mock_config_manager(mock_config):
    """Create mock configuration manager."""
    with patch('aris.cli.init_command.ConfigManager') as mock:
        instance = Mock()
        # Add _config attribute so get_config() works
        instance._config = mock_config
        instance.get_config.return_value = mock_config
        instance.load.return_value = mock_config
        instance.validate.return_value = {"valid": True, "errors": [], "warnings": []}
        instance._profile = ConfigProfile.DEVELOPMENT
        mock.get_instance.return_value = instance
        yield mock
```

**Validation**:
```bash
source .venv/bin/activate
python -m pytest tests/unit/test_cli.py::TestStatusCommand -v
python -m pytest tests/unit/test_cli.py::TestDBCommands -v
python -m pytest tests/unit/test_cli.py::TestGitCommands -v
python -m pytest tests/unit/test_cli.py::TestShowCommand::test_show_metadata_only -v
python -m pytest tests/unit/test_cli.py::TestPlaceholderCommands::test_research_command -v
```

**Expected Result**: 7 tests pass (status_basic, status_json, show_metadata_only, research_command, db_status, git_status, and possibly init tests)

---

### Fix 2: Session Test Update (5 minutes) → 2 tests fixed

**Decision Required**: Does Wave 4 need `session start` command?

**Option A - Update Tests (RECOMMENDED)**:
```bash
# File: tests/unit/test_cli.py:199
# Change from:
result = runner.invoke(cli, ["session", "start"])

# To:
result = runner.invoke(cli, ["session", "list"])
# And update assertion:
assert "Wave 4" in result.output or result.exit_code == 0
```

```bash
# File: tests/integration/test_cli_integration.py:148
# Change from:
result = runner.invoke(cli, ["session", "start"])

# To:
result = runner.invoke(cli, ["session", "list"])
# And update assertion:
assert result.exit_code == 0
```

**Option B - Add Command** (if needed):
```python
# File: src/aris/cli/session_commands.py
# Add after line 43:

@session.command()
@click.argument("name", required=False)
@click.option("--description", help="Session description")
@click.pass_context
def start(ctx: click.Context, name: str, description: str) -> None:
    """Start a new research session."""
    console.print("[yellow]⏳ Wave 4 feature - Session start coming soon![/yellow]")
```

**Validation**:
```bash
python -m pytest tests/unit/test_cli.py::TestPlaceholderCommands::test_session_commands -v
python -m pytest tests/integration/test_cli_integration.py::TestCLIIntegration::test_placeholder_commands_accessible -v
```

**Expected Result**: 2 tests pass

---

### Fix 3: Integration Test Reset (15 minutes) → 6 tests fixed

**File**: `tests/integration/test_cli_integration.py`
**Lines**: 30-36
**Current Problem**: `reset_config()` fixture doesn't properly initialize ConfigManager for CLI commands

**Investigation Steps**:
1. Check if ConfigManager singleton persists across tests
2. Verify `reset_instance()` clears `_config` attribute
3. Ensure each test gets fresh ConfigManager instance

**Potential Fix**:
```python
@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration manager before each test."""
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()

# MIGHT NEED TO ADD:
@pytest.fixture
def initialized_config_manager(temp_project_dir, monkeypatch):
    """Create and initialize ConfigManager for tests."""
    monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
    ConfigManager.reset_instance()
    manager = ConfigManager.get_instance()
    manager.load()  # This might be the missing piece
    return manager
```

**Alternative**: Patch ConfigManager at module level for all integration tests

**Validation**:
```bash
python -m pytest tests/integration/test_cli_integration.py::TestCLIIntegration::test_full_initialization_workflow -vvs
python -m pytest tests/integration/test_cli_integration.py::TestCLIIntegration::test_status_after_init -v
python -m pytest tests/integration/test_cli_integration.py::TestCLIIntegration::test_json_output_mode -v
python -m pytest tests/integration/test_cli_integration.py::TestCLIIntegration::test_db_commands_workflow -v
python -m pytest tests/integration/test_cli_integration.py::TestCLIOutputFormats::test_verbose_output -v
```

**Expected Result**: 6 integration tests pass

---

## Testing Strategy

### Unit Test Validation
```bash
# Run all unit CLI tests
source .venv/bin/activate
python -m pytest tests/unit/test_cli.py -v

# Expected: 16 passed, 0 failed
```

### Integration Test Validation
```bash
# Run all integration CLI tests
python -m pytest tests/integration/test_cli_integration.py -v

# Expected: 13 passed, 0 failed
```

### Full Test Suite
```bash
# Run all tests to ensure no regressions
python -m pytest tests/ -v

# Monitor for any new failures
```

---

## Debugging Tips

### If Unit Tests Still Fail:
1. Check if mock patches are in correct location
2. Verify `_config` attribute is set before `get_config()` called
3. Add debug print in fixture: `print(f"Mock config: {instance._config}")`
4. Test ConfigManager.get_instance() returns mocked instance

### If Integration Tests Still Fail:
1. Check if temp_project_dir is properly created
2. Verify environment variable is set: `echo $ARIS_PROJECT_ROOT`
3. Check if `init` command actually creates `.aris` directory
4. Verify database is initialized: `ls -la $ARIS_PROJECT_ROOT/.aris/`
5. Test ConfigManager load() is called: Add logging

### If Session Tests Still Fail:
1. Verify subcommand exists: `aris session --help`
2. Check session group registration in main.py
3. Test command directly: `aris session list` or `aris session start`

---

## Rollback Plan

If fixes cause new issues:

1. **Revert commits**: `git checkout -- tests/unit/test_cli.py tests/integration/test_cli_integration.py`
2. **Document new issues**: Create new diagnosis report
3. **Escalate**: If ConfigManager design issue, escalate to architecture team

---

## Success Criteria

- [ ] All 15 failing tests now pass
- [ ] No new test failures introduced
- [ ] ConfigManager mock matches real behavior
- [ ] Integration tests use real file system properly
- [ ] Session commands test matches implemented commands
- [ ] Test execution time remains under 5 seconds for unit tests
- [ ] Test execution time remains under 10 seconds for integration tests

---

## Post-Implementation

After all fixes complete:

1. **Run full test suite**: `pytest tests/ -v --cov=src/aris`
2. **Update coverage report**: Check CLI coverage improved
3. **Document decisions**: Update architecture docs with ConfigManager decisions
4. **Close issue**: Reference this roadmap in commit message
5. **Update ARIS-DELIVERY-COMPLETE.md**: Note CLI tests now passing

---

## File References

**Test Files**:
- `/mnt/projects/aris-tool/tests/unit/test_cli.py` - Unit test fixes
- `/mnt/projects/aris-tool/tests/integration/test_cli_integration.py` - Integration test fixes

**Source Files** (potentially):
- `/mnt/projects/aris-tool/src/aris/cli/session_commands.py` - If adding start command
- `/mnt/projects/aris-tool/src/aris/core/config.py` - If changing auto-load behavior

**Documentation**:
- `/mnt/projects/aris-tool/claudedocs/CLI-FAILURE-DIAGNOSIS.md` - Root cause analysis
- `/mnt/projects/aris-tool/claudedocs/CLI-FIX-ROADMAP.md` - This file

---

## Questions to Resolve Before Implementation

1. **Session Start Command**: Add it or update tests?
   - **Recommendation**: Update tests to use `session list` (command doesn't exist, tests shouldn't expect it)

2. **ConfigManager Auto-Load**: Should `get_config()` auto-load?
   - **Recommendation**: Keep explicit error (better for debugging and testing)

3. **Mock Strategy**: Full mock or partial mock of ConfigManager?
   - **Recommendation**: Full mock with proper `_config` attribute (keeps tests isolated)

4. **Integration Test Strategy**: Mock or real ConfigManager?
   - **Recommendation**: Real ConfigManager with temp directories (true integration test)

---

**Ready for Implementation**: YES (pending decision on session start command)
**Blockers**: None (can proceed with Fix 1 and Fix 3 immediately)
**Estimated Completion**: 35 minutes of focused work
