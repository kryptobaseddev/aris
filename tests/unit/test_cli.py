"""Unit tests for ARIS CLI commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from aris.cli.main import cli
from aris.core.config import ConfigManager, ConfigProfile
from aris.models.config import ArisConfig


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=ArisConfig)
    config.project_root = Path("/tmp/test-aris")
    config.research_dir = Path("/tmp/test-aris/research")
    config.database_path = Path("/tmp/test-aris/.aris/aris.db")
    config.tavily_api_key = "test-key"
    return config


@pytest.fixture
def mock_config_manager(mock_config):
    """Create mock configuration manager."""
    with patch('aris.cli.init_command.ConfigManager') as mock:
        instance = Mock()
        instance.get_config.return_value = mock_config
        instance.load.return_value = mock_config
        instance.validate.return_value = {"valid": True, "errors": [], "warnings": []}
        instance._profile = ConfigProfile.DEVELOPMENT
        instance._config = mock_config
        mock.get_instance.return_value = instance
        yield mock


class TestCLIMain:
    """Test main CLI entry point."""
    
    def test_version_option(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_help_option(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ARIS" in result.output
        assert "Autonomous Research Intelligence System" in result.output
    
    def test_json_flag(self, runner):
        """Test --json flag is passed to context."""
        result = runner.invoke(cli, ["--json", "--help"])
        assert result.exit_code == 0


class TestInitCommand:
    """Test init command."""
    
    def test_init_basic(self, runner, mock_config_manager):
        """Test basic project initialization."""
        with patch('aris.cli.init_command.DatabaseManager') as mock_db, \
             patch('aris.cli.init_command.GitManager') as mock_git:
            
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance
            
            result = runner.invoke(cli, ["init", "--name", "TestProject"])
            
            assert result.exit_code == 0
            assert "Initialized ARIS project" in result.output
            mock_db_instance.initialize.assert_called_once()
    
    def test_init_with_profile(self, runner, mock_config_manager):
        """Test init with specific profile."""
        with patch('aris.cli.init_command.DatabaseManager'), \
             patch('aris.cli.init_command.GitManager'):
            
            result = runner.invoke(cli, [
                "init",
                "--name", "TestProject",
                "--profile", "production"
            ])
            
            assert result.exit_code == 0
            assert "production" in result.output.lower()
    
    def test_init_already_initialized(self, runner, mock_config_manager):
        """Test init when already initialized."""
        result = runner.invoke(cli, ["init", "--name", "TestProject"])
        assert "already initialized" in result.output.lower() or result.exit_code == 0
    
    def test_init_force(self, runner, mock_config_manager):
        """Test init with --force flag."""
        with patch('aris.cli.init_command.DatabaseManager'), \
             patch('aris.cli.init_command.GitManager'):
            
            result = runner.invoke(cli, [
                "init",
                "--name", "TestProject",
                "--force"
            ])
            
            assert result.exit_code == 0


class TestStatusCommand:
    """Test status command."""
    
    def test_status_basic(self, runner, mock_config_manager):
        """Test basic status display."""
        with patch('aris.cli.status_command.DatabaseManager') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.is_initialized.return_value = True
            mock_db_instance.get_document_count.return_value = 5
            mock_db_instance.get_session_count.return_value = 3
            mock_db.return_value = mock_db_instance
            
            result = runner.invoke(cli, ["status"])
            
            assert result.exit_code == 0
            assert "System Status" in result.output
    
    def test_status_json(self, runner, mock_config_manager):
        """Test status with JSON output."""
        with patch('aris.cli.status_command.DatabaseManager') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.is_initialized.return_value = True
            mock_db_instance.get_document_count.return_value = 5
            mock_db_instance.get_session_count.return_value = 3
            mock_db.return_value = mock_db_instance
            
            result = runner.invoke(cli, ["--json", "status"])
            
            assert result.exit_code == 0
            assert "status" in result.output


class TestShowCommand:
    """Test show command."""
    
    def test_show_nonexistent_file(self, runner, mock_config_manager):
        """Test show with nonexistent file."""
        result = runner.invoke(cli, ["show", "/nonexistent/file.md"])
        assert result.exit_code != 0
    
    def test_show_metadata_only(self, runner, mock_config_manager, tmp_path):
        """Test show with --metadata-only flag."""
        # Create a temporary test document
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document\n\nContent here.")
        
        with patch('aris.cli.show_command.DocumentStore') as mock_store:
            mock_doc = Mock()
            mock_doc.metadata = Mock(
                title="Test Document",
                confidence=0.85,
                topics=["test"],
                created_at=Mock(strftime=lambda x: "2025-01-01 00:00:00"),
                updated_at=Mock(strftime=lambda x: "2025-01-01 00:00:00")
            )
            mock_doc.content = "# Test Document\n\nContent here."
            
            mock_store_instance = Mock()
            mock_store_instance.load_document.return_value = mock_doc
            mock_store.return_value = mock_store_instance
            
            result = runner.invoke(cli, ["show", str(test_file), "--metadata-only"])
            
            assert result.exit_code == 0
            assert "Test Document" in result.output


class TestPlaceholderCommands:
    """Test placeholder commands for future waves."""
    
    def test_research_command(self, runner):
        """Test research placeholder."""
        result = runner.invoke(cli, ["research", "test query"])
        assert result.exit_code == 0
        assert "Wave 2" in result.output
    
    def test_organize_command(self, runner):
        """Test organize placeholder."""
        result = runner.invoke(cli, ["organize"])
        assert result.exit_code == 0
        assert "Wave 3" in result.output
    
    def test_session_commands(self, runner):
        """Test session placeholder commands."""
        result = runner.invoke(cli, ["session", "start"])
        assert result.exit_code == 0
        assert "Wave 4" in result.output
        
        result = runner.invoke(cli, ["session", "list"])
        assert result.exit_code == 0


class TestDBCommands:
    """Test database commands."""
    
    def test_db_status(self, runner, mock_config_manager):
        """Test db status command."""
        with patch('aris.cli.db_commands.DatabaseManager') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.is_initialized.return_value = True
            mock_db_instance.get_document_count.return_value = 10
            mock_db_instance.get_session_count.return_value = 5
            mock_db.return_value = mock_db_instance
            
            result = runner.invoke(cli, ["db", "status"])
            
            assert result.exit_code == 0
            assert "Database Status" in result.output


class TestGitCommands:
    """Test Git commands."""
    
    def test_git_status(self, runner, mock_config_manager):
        """Test git status command."""
        with patch('aris.cli.git_commands.GitManager'):
            result = runner.invoke(cli, ["git", "status"])
            
            assert result.exit_code == 0
            assert "Git Repository Status" in result.output
