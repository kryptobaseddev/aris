"""Unit tests for ARIS configuration management.

Tests cover:
- ConfigManager singleton pattern
- Configuration loading from multiple sources
- API key management via keyring
- Configuration validation
- Profile management
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aris.core.config import ConfigManager, ConfigProfile, ConfigurationError
from aris.core.secrets import KeyringNotAvailableError, SecureKeyManager


class TestSecureKeyManager:
    """Tests for SecureKeyManager."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: Aggressively clear keyring state at START
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass

        yield

        # Teardown: Clean up any test keys
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass

    def test_set_and_get_api_key(self):
        """Test storing and retrieving API keys."""
        manager = SecureKeyManager()

        # Set key
        test_key = "test_key_12345"
        manager.set_api_key("tavily", test_key)

        # Get key
        retrieved_key = manager.get_api_key("tavily")
        assert retrieved_key == test_key

    def test_get_nonexistent_key(self):
        """Test retrieving a key that doesn't exist."""
        manager = SecureKeyManager()
        key = manager.get_api_key("nonexistent_provider")
        assert key is None

    def test_delete_api_key(self):
        """Test deleting API keys."""
        manager = SecureKeyManager()

        # Set key
        manager.set_api_key("tavily", "test_key")

        # Delete key
        deleted = manager.delete_api_key("tavily")
        assert deleted is True

        # Verify deleted
        key = manager.get_api_key("tavily")
        assert key is None

    def test_delete_nonexistent_key(self):
        """Test deleting a key that doesn't exist."""
        manager = SecureKeyManager()
        deleted = manager.delete_api_key("nonexistent")
        assert deleted is False

    def test_set_empty_provider_raises_error(self):
        """Test that setting a key with empty provider raises ValueError."""
        manager = SecureKeyManager()
        with pytest.raises(ValueError, match="Provider name cannot be empty"):
            manager.set_api_key("", "test_key")

    def test_set_empty_key_raises_error(self):
        """Test that setting an empty API key raises ValueError."""
        manager = SecureKeyManager()
        with pytest.raises(ValueError, match="API key cannot be empty"):
            manager.set_api_key("tavily", "")

    def test_verify_key_exists(self):
        """Test checking if key exists."""
        manager = SecureKeyManager()

        # Key doesn't exist
        assert manager.verify_key_exists("tavily") is False

        # Set key
        manager.set_api_key("tavily", "test_key")

        # Key exists
        assert manager.verify_key_exists("tavily") is True

    def test_list_providers(self):
        """Test listing providers with stored keys."""
        manager = SecureKeyManager()

        # Set multiple keys
        manager.set_api_key("tavily", "key1")
        manager.set_api_key("anthropic", "key2")

        # List providers
        providers = manager.list_providers()
        assert "tavily" in providers
        assert "anthropic" in providers

    def test_get_all_keys(self):
        """Test retrieving all API keys."""
        manager = SecureKeyManager()

        # Set some keys
        manager.set_api_key("tavily", "key1")
        manager.set_api_key("openai", "key2")

        # Get all keys
        all_keys = manager.get_all_keys()
        assert all_keys["tavily"] == "key1"
        assert all_keys["openai"] == "key2"
        assert all_keys["anthropic"] is None  # Not set
        assert all_keys["google"] is None  # Not set

    def test_clear_all_keys(self):
        """Test clearing all API keys."""
        manager = SecureKeyManager()

        # Set multiple keys
        manager.set_api_key("tavily", "key1")
        manager.set_api_key("anthropic", "key2")
        manager.set_api_key("openai", "key3")

        # Clear all
        deleted_count = SecureKeyManager.clear_all_keys()
        assert deleted_count >= 3

        # Verify all cleared
        assert manager.get_api_key("tavily") is None
        assert manager.get_api_key("anthropic") is None
        assert manager.get_api_key("openai") is None


class TestConfigManager:
    """Tests for ConfigManager."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: Clear keyring first, THEN reset singleton
        # This ensures ConfigManager creates a new _secrets_manager with mocked keyring
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass
        ConfigManager.reset_instance()

        yield

        # Teardown: Reset singleton and clean up keys
        ConfigManager.reset_instance()
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass

    def test_singleton_pattern(self):
        """Test that ConfigManager is a singleton."""
        instance1 = ConfigManager.get_instance()
        instance2 = ConfigManager.get_instance()
        assert instance1 is instance2

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        instance1 = ConfigManager.get_instance()
        ConfigManager.reset_instance()
        instance2 = ConfigManager.get_instance()
        assert instance1 is not instance2

    def test_load_configuration_default_profile(self, tmp_path):
        """Test loading configuration with default profile."""
        config_manager = ConfigManager.get_instance()

        # Create temp .env file
        env_file = tmp_path / ".env"
        env_file.write_text("ARIS_PROJECT_ROOT=/test/path\n")

        config = config_manager.load(env_file=env_file)

        assert config is not None
        assert config_manager.profile == ConfigProfile.DEVELOPMENT

    def test_load_configuration_with_profile(self, tmp_path):
        """Test loading configuration with specific profile."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")

        config = config_manager.load(
            profile=ConfigProfile.PRODUCTION, env_file=env_file
        )

        assert config is not None
        assert config_manager.profile == ConfigProfile.PRODUCTION

    def test_get_config_before_load_raises_error(self):
        """Test that getting config before load raises ConfigurationError."""
        config_manager = ConfigManager.get_instance()

        with pytest.raises(ConfigurationError, match="Configuration not loaded"):
            config_manager.get_config()

    def test_get_api_key_from_keyring(self, tmp_path):
        """Test retrieving API key from keyring."""
        # Store key in keyring
        secrets_manager = SecureKeyManager()
        secrets_manager.set_api_key("tavily", "keyring_key_123")

        # Load config
        config_manager = ConfigManager.get_instance()
        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Get key
        key = config_manager.get_api_key("tavily")
        assert key == "keyring_key_123"

    def test_set_api_key_with_persist(self, tmp_path):
        """Test setting API key with persistence to keyring."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set key
        config_manager.set_api_key("tavily", "new_key_456", persist=True)

        # Verify in config
        assert config_manager.get_api_key("tavily") == "new_key_456"

        # Verify in keyring
        secrets_manager = SecureKeyManager()
        assert secrets_manager.get_api_key("tavily") == "new_key_456"

    def test_set_api_key_without_persist(self, tmp_path):
        """Test setting API key without persisting to keyring."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set key in memory only
        config_manager.set_api_key("tavily", "memory_key", persist=False)

        # Verify in config
        assert config_manager.get_api_key("tavily") == "memory_key"

        # Verify NOT in keyring (should be None or old value)
        secrets_manager = SecureKeyManager()
        keyring_value = secrets_manager.get_api_key("tavily")
        # Should not be the memory-only value
        assert keyring_value != "memory_key" or keyring_value is None

    def test_set_invalid_provider_raises_error(self, tmp_path):
        """Test setting API key for invalid provider raises error."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        with pytest.raises(ConfigurationError, match="Invalid provider"):
            config_manager.set_api_key("invalid_provider", "key")

    def test_delete_api_key(self, tmp_path):
        """Test deleting API key."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set and delete key
        config_manager.set_api_key("tavily", "delete_me", persist=True)
        config_manager.delete_api_key("tavily")

        # Verify deleted
        assert config_manager.get_api_key("tavily") is None

    def test_validate_missing_required_keys(self, tmp_path):
        """Test validation fails when required keys are missing."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        validation = config_manager.validate()

        assert validation["valid"] is False
        assert len(validation["missing_keys"]) >= 3  # tavily, anthropic, openai
        assert "tavily" in validation["missing_keys"]
        assert "anthropic" in validation["missing_keys"]
        assert "openai" in validation["missing_keys"]

    def test_validate_with_all_keys_set(self, tmp_path):
        """Test validation passes when all required keys are set."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set all required keys
        config_manager.set_api_key("tavily", "key1", persist=False)
        config_manager.set_api_key("anthropic", "key2", persist=False)
        config_manager.set_api_key("openai", "key3", persist=False)

        validation = config_manager.validate()

        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert len(validation["missing_keys"]) == 0

    def test_get_config_summary_masked(self, tmp_path):
        """Test getting config summary with masked secrets."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set a key
        long_key = "sk-ant-1234567890abcdefghij"
        config_manager.set_api_key("anthropic", long_key, persist=False)

        summary = config_manager.get_config_summary(mask_secrets=True)

        # Check masked
        assert summary["api_keys"]["anthropic"] != long_key
        assert "..." in summary["api_keys"]["anthropic"]
        assert summary["api_keys"]["tavily"] == "Not set"

    def test_get_config_summary_unmasked(self, tmp_path):
        """Test getting config summary with unmasked secrets."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")
        config_manager.load(env_file=env_file)

        # Set a key
        test_key = "test_key_123"
        config_manager.set_api_key("tavily", test_key, persist=False)

        summary = config_manager.get_config_summary(mask_secrets=False)

        # Check unmasked
        assert summary["api_keys"]["tavily"] == test_key

    def test_set_custom_value(self, tmp_path):
        """Test setting custom configuration values."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")

        # Set custom value before load
        config_manager.set_custom_value("max_hops", 10)
        config = config_manager.load(env_file=env_file)

        assert config.max_hops == 10

    def test_reload_configuration(self, tmp_path):
        """Test reloading configuration."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")

        # Initial load
        config1 = config_manager.load(env_file=env_file)

        # Reload
        config2 = config_manager.load(env_file=env_file, reload=True)

        assert config1 is not config2

    def test_profile_property(self, tmp_path):
        """Test profile property."""
        config_manager = ConfigManager.get_instance()

        env_file = tmp_path / ".env"
        env_file.write_text("")

        config_manager.load(profile=ConfigProfile.PRODUCTION, env_file=env_file)

        assert config_manager.profile == ConfigProfile.PRODUCTION


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: Reset singleton and clear keyring state at START
        ConfigManager.reset_instance()
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass

        yield

        # Teardown: Reset singleton and clean up keys
        ConfigManager.reset_instance()
        try:
            SecureKeyManager.clear_all_keys()
        except Exception:
            pass

    def test_end_to_end_configuration_flow(self, tmp_path):
        """Test complete configuration workflow."""
        # 1. Initialize config manager
        config_manager = ConfigManager.get_instance()

        # 2. Load configuration
        env_file = tmp_path / ".env"
        env_file.write_text("ARIS_MAX_HOPS=3\n")
        config = config_manager.load(env_file=env_file)

        # 3. Validate (should fail - missing keys)
        validation = config_manager.validate()
        assert not validation["valid"]

        # 4. Set API keys
        config_manager.set_api_key("tavily", "tvly_key", persist=True)
        config_manager.set_api_key("anthropic", "ant_key", persist=True)
        config_manager.set_api_key("openai", "oai_key", persist=True)

        # 5. Validate again (should pass)
        validation = config_manager.validate()
        assert validation["valid"]

        # 6. Get config summary
        summary = config_manager.get_config_summary(mask_secrets=True)
        assert "..." in summary["api_keys"]["tavily"]

        # 7. Verify keys are retrievable
        assert config_manager.get_api_key("tavily") == "tvly_key"
        assert config_manager.get_api_key("anthropic") == "ant_key"
        assert config_manager.get_api_key("openai") == "oai_key"

    def test_keyring_fallback_to_env(self, tmp_path):
        """Test that environment variables are used when keyring has no key."""
        # Set env var
        env_file = tmp_path / ".env"
        env_file.write_text("ARIS_TAVILY_API_KEY=env_key_123\n")

        config_manager = ConfigManager.get_instance()
        config = config_manager.load(env_file=env_file)

        # Should get key from environment
        key = config_manager.get_api_key("tavily")
        assert key == "env_key_123"

    def test_keyring_overrides_env(self, tmp_path):
        """Test that keyring keys take precedence over environment."""
        # Set env var
        env_file = tmp_path / ".env"
        env_file.write_text("ARIS_TAVILY_API_KEY=env_key\n")

        # Set keyring key
        secrets_manager = SecureKeyManager()
        secrets_manager.set_api_key("tavily", "keyring_key")

        config_manager = ConfigManager.get_instance()
        config_manager.load(env_file=env_file)

        # Should get key from keyring (not env)
        key = config_manager.get_api_key("tavily")
        assert key == "keyring_key"
