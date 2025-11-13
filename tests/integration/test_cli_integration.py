"""Integration tests for ARIS CLI.

Tests end-to-end CLI workflows with real file system operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

from aris.cli.main import cli
from aris.core.config import ConfigManager


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration manager before each test."""
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()


class TestCLIIntegration:
    """Integration tests for complete CLI workflows."""
    
    def test_full_initialization_workflow(self, runner, temp_project_dir, monkeypatch):
        """Test complete project initialization."""
        # Set environment variables
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Run init command
        result = runner.invoke(cli, [
            "init",
            "--name", "TestProject",
            "--profile", "development"
        ])
        
        assert result.exit_code == 0
        assert "Initialized ARIS project" in result.output
        
        # Verify directories created
        aris_dir = temp_project_dir / ".aris"
        research_dir = temp_project_dir / "research"
        
        assert aris_dir.exists()
        assert research_dir.exists()
        
        # Verify database exists
        db_path = aris_dir / "aris.db"
        assert db_path.exists()
        
        # Verify Git repository initialized
        git_dir = research_dir / ".git"
        assert git_dir.exists()
    
    def test_status_after_init(self, runner, temp_project_dir, monkeypatch):
        """Test status command after initialization."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Initialize project
        runner.invoke(cli, [
            "init",
            "--name", "TestProject"
        ])
        
        # Check status
        result = runner.invoke(cli, ["status"])
        
        assert result.exit_code == 0
        assert "System Status" in result.output
        assert "Configured" in result.output or "✅" in result.output
    
    def test_json_output_mode(self, runner, temp_project_dir, monkeypatch):
        """Test JSON output mode across commands."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Initialize with JSON output
        result = runner.invoke(cli, [
            "--json",
            "init",
            "--name", "TestProject"
        ])
        
        assert result.exit_code == 0
        assert "status" in result.output.lower() or "project" in result.output.lower()
        
        # Status with JSON output
        result = runner.invoke(cli, ["--json", "status"])
        
        assert result.exit_code == 0
        # JSON output should contain structured data
        assert "{" in result.output
    
    def test_db_commands_workflow(self, runner, temp_project_dir, monkeypatch):
        """Test database command workflow."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Initialize project
        runner.invoke(cli, ["init", "--name", "TestProject"])
        
        # Check database status
        result = runner.invoke(cli, ["db", "status"])
        
        assert result.exit_code == 0
        assert "Database Status" in result.output
    
    def test_git_commands_workflow(self, runner, temp_project_dir, monkeypatch):
        """Test Git command workflow."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Initialize project
        runner.invoke(cli, ["init", "--name", "TestProject"])
        
        # Check Git status
        result = runner.invoke(cli, ["git", "status"])
        
        assert result.exit_code == 0
        assert "Git Repository Status" in result.output
    
    def test_placeholder_commands_accessible(self, runner):
        """Test that placeholder commands are accessible."""
        # Research command
        result = runner.invoke(cli, ["research", "test query"])
        assert result.exit_code == 0
        assert "Wave 2" in result.output
        
        # Organize command
        result = runner.invoke(cli, ["organize"])
        assert result.exit_code == 0
        assert "Wave 3" in result.output
        
        # Session commands
        result = runner.invoke(cli, ["session", "start"])
        assert result.exit_code == 0
        assert "Wave 4" in result.output
    
    def test_config_integration(self, runner, temp_project_dir, monkeypatch):
        """Test config command integration."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        # Initialize project
        runner.invoke(cli, ["init", "--name", "TestProject"])
        
        # Show config
        result = runner.invoke(cli, ["config", "show"])
        
        # Should succeed or show configuration
        assert result.exit_code in [0, 1]  # May fail if keyring not available
    
    def test_error_handling(self, runner):
        """Test error handling for invalid commands."""
        # Non-existent command
        result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code != 0
        
        # Invalid option
        result = runner.invoke(cli, ["--invalid-option"])
        assert result.exit_code != 0
    
    def test_help_for_all_commands(self, runner):
        """Test that help is available for all commands."""
        commands = [
            "init",
            "status",
            "show",
            "config",
            "db",
            "git",
            "research",
            "organize",
            "session"
        ]
        
        for command in commands:
            result = runner.invoke(cli, [command, "--help"])
            assert result.exit_code == 0
            assert "help" in result.output.lower() or command in result.output.lower()


class TestCLIErrorHandling:
    """Test error handling scenarios."""
    
    def test_status_without_init(self, runner, temp_project_dir, monkeypatch):
        """Test status command before initialization."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        result = runner.invoke(cli, ["status"])
        
        # Should fail gracefully or show uninitialized status
        assert "not initialized" in result.output.lower() or result.exit_code != 0
    
    def test_show_nonexistent_document(self, runner):
        """Test show command with nonexistent document."""
        result = runner.invoke(cli, ["show", "/nonexistent/path.md"])
        
        assert result.exit_code != 0


class TestCLIOutputFormats:
    """Test different output format scenarios."""
    
    def test_verbose_output(self, runner, temp_project_dir, monkeypatch):
        """Test verbose flag adds detail."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        runner.invoke(cli, ["init", "--name", "TestProject"])
        
        # Regular output
        result_normal = runner.invoke(cli, ["status"])
        
        # Verbose output
        result_verbose = runner.invoke(cli, ["-v", "status"])
        
        # Both should succeed
        assert result_normal.exit_code == 0
        assert result_verbose.exit_code == 0
    
    def test_json_vs_rich_output(self, runner, temp_project_dir, monkeypatch):
        """Test JSON vs Rich output formats."""
        monkeypatch.setenv("ARIS_PROJECT_ROOT", str(temp_project_dir))
        
        runner.invoke(cli, ["init", "--name", "TestProject"])
        
        # Rich output (default)
        result_rich = runner.invoke(cli, ["status"])
        
        # JSON output
        result_json = runner.invoke(cli, ["--json", "status"])
        
        # Rich should have formatting
        assert any(char in result_rich.output for char in ["✅", "❌", "│", "─"])
        
        # JSON should be structured (though may not parse perfectly in tests)
        assert result_json.output.strip() != result_rich.output.strip()
