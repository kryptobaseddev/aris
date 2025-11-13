"""Central configuration management for ARIS.

This module provides singleton configuration management with:
- Environment variable loading (.env files)
- Secure API key management via keyring
- Configuration validation
- Multiple profile support (development, production)
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aris.core.secrets import SecureKeyManager
from aris.models.config import ArisConfig


class ConfigProfile(str, Enum):
    """Configuration profiles."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigManager:
    """Singleton configuration manager for ARIS.

    Manages configuration loading from multiple sources:
    1. Environment variables (ARIS_ prefix)
    2. .env files
    3. System keyring for API keys
    4. Config file overrides

    Example:
        config = ConfigManager.get_instance()
        api_key = config.get_api_key("tavily")
        config.validate()
    """

    _instance: Optional["ConfigManager"] = None
    _initialized: bool = False

    def __init__(self) -> None:
        """Initialize configuration manager.

        Note: Use get_instance() instead of direct instantiation.
        """
        if ConfigManager._initialized:
            return

        self._config: Optional[ArisConfig] = None
        self._secrets_manager = SecureKeyManager()
        self._profile = ConfigProfile.DEVELOPMENT
        self._custom_config: Dict[str, Any] = {}

        ConfigManager._initialized = True

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """Get singleton instance of ConfigManager.

        Returns:
            The singleton ConfigManager instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (primarily for testing).

        Warning: Only use in test scenarios.
        """
        cls._instance = None
        cls._initialized = False

    def load(
        self,
        profile: ConfigProfile = ConfigProfile.DEVELOPMENT,
        env_file: Optional[Path] = None,
        reload: bool = False,
    ) -> ArisConfig:
        """Load configuration from all sources.

        Args:
            profile: Configuration profile to use
            env_file: Optional path to .env file (defaults to .env in project root)
            reload: Force reload even if already loaded

        Returns:
            Loaded ArisConfig instance

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        if self._config is not None and not reload:
            return self._config

        self._profile = profile

        # Determine .env file path
        if env_file is None:
            env_file = Path.cwd() / ".env"

        # Load base configuration from environment and .env file
        try:
            # Update model config to use specified env file
            config_dict = {}
            if env_file.exists():
                config_dict["env_file"] = str(env_file)

            self._config = ArisConfig(**self._custom_config)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}") from e

        # Load API keys from keyring
        self._load_api_keys_from_keyring()

        # Ensure directories exist
        self._config.ensure_directories()

        return self._config

    def _load_api_keys_from_keyring(self) -> None:
        """Load API keys from system keyring into config.

        Fallback order:
        1. System keyring
        2. Environment variables (already loaded by pydantic-settings)
        3. None (will fail validation if required)
        """
        if self._config is None:
            return

        # Load keys from keyring if not already set in environment
        key_mappings = {
            "tavily_api_key": "tavily",
            "anthropic_api_key": "anthropic",
            "openai_api_key": "openai",
            "google_api_key": "google",
        }

        for config_attr, key_name in key_mappings.items():
            current_value = getattr(self._config, config_attr)
            if current_value is None:
                # Try loading from keyring
                keyring_value = self._secrets_manager.get_api_key(key_name)
                if keyring_value:
                    # Directly update the config object
                    object.__setattr__(self._config, config_attr, keyring_value)

    def get_config(self) -> ArisConfig:
        """Get current configuration.

        Returns:
            Current ArisConfig instance

        Raises:
            ConfigurationError: If configuration not loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )
        return self._config

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider.

        Args:
            provider: Provider name (tavily, anthropic, openai, google)

        Returns:
            API key if available, None otherwise

        Raises:
            ConfigurationError: If configuration not loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )

        key_mapping = {
            "tavily": self._config.tavily_api_key,
            "anthropic": self._config.anthropic_api_key,
            "openai": self._config.openai_api_key,
            "google": self._config.google_api_key,
        }

        return key_mapping.get(provider.lower())

    def set_api_key(self, provider: str, api_key: str, persist: bool = True) -> None:
        """Set API key for a provider.

        Args:
            provider: Provider name (tavily, anthropic, openai, google)
            api_key: The API key value
            persist: If True, store in keyring; if False, only in memory

        Raises:
            ConfigurationError: If configuration not loaded or invalid provider
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )

        provider_lower = provider.lower()
        valid_providers = ["tavily", "anthropic", "openai", "google"]

        if provider_lower not in valid_providers:
            raise ConfigurationError(
                f"Invalid provider: {provider}. Must be one of {valid_providers}"
            )

        # Store in keyring if persist=True
        if persist:
            self._secrets_manager.set_api_key(provider_lower, api_key)

        # Update config in memory
        key_mapping = {
            "tavily": "tavily_api_key",
            "anthropic": "anthropic_api_key",
            "openai": "openai_api_key",
            "google": "google_api_key",
        }

        config_attr = key_mapping[provider_lower]
        object.__setattr__(self._config, config_attr, api_key)

    def delete_api_key(self, provider: str) -> None:
        """Delete API key for a provider from keyring.

        Args:
            provider: Provider name (tavily, anthropic, openai, google)

        Raises:
            ConfigurationError: If configuration not loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )

        self._secrets_manager.delete_api_key(provider.lower())

        # Clear from config in memory
        key_mapping = {
            "tavily": "tavily_api_key",
            "anthropic": "anthropic_api_key",
            "openai": "openai_api_key",
            "google": "google_api_key",
        }

        if provider.lower() in key_mapping:
            config_attr = key_mapping[provider.lower()]
            object.__setattr__(self._config, config_attr, None)

    def validate(self) -> Dict[str, Any]:
        """Validate configuration completeness.

        Checks that all required API keys are present and configuration
        is valid for the current profile.

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "missing_keys": List[str]
            }

        Raises:
            ConfigurationError: If configuration not loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )

        errors = []
        warnings = []
        missing_keys = []

        # Check required API keys for research functionality
        required_keys = {
            "tavily": self._config.tavily_api_key,
            "anthropic": self._config.anthropic_api_key,
            "openai": self._config.openai_api_key,
        }

        for key_name, key_value in required_keys.items():
            if not key_value:
                missing_keys.append(key_name)
                errors.append(f"Missing required API key: {key_name}")

        # Optional keys
        if not self._config.google_api_key:
            warnings.append(
                "Google API key not set. Multi-model consensus will be limited."
            )

        # Validate paths are accessible
        try:
            self._config.ensure_directories()
        except Exception as e:
            errors.append(f"Failed to create required directories: {e}")

        # Check budget configuration
        if self._config.monthly_budget_limit <= 0:
            errors.append("Monthly budget limit must be positive")

        if self._config.default_budget_deep > self._config.monthly_budget_limit:
            warnings.append(
                "Deep research budget exceeds monthly limit. "
                "Consider adjusting budget values."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "missing_keys": missing_keys,
        }

    def get_config_summary(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Get configuration summary for display.

        Args:
            mask_secrets: If True, mask API keys in output

        Returns:
            Dictionary with configuration summary

        Raises:
            ConfigurationError: If configuration not loaded
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration not loaded. Call load() first."
            )

        def mask_key(key: Optional[str]) -> str:
            if key is None:
                return "Not set"
            if mask_secrets:
                return f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "****"
            return key

        return {
            "profile": self._profile.value,
            "project_root": str(self._config.project_root),
            "research_dir": str(self._config.research_dir),
            "database_path": str(self._config.database_path),
            "api_keys": {
                "tavily": mask_key(self._config.tavily_api_key),
                "anthropic": mask_key(self._config.anthropic_api_key),
                "openai": mask_key(self._config.openai_api_key),
                "google": mask_key(self._config.google_api_key),
            },
            "budgets": {
                "quick": self._config.default_budget_quick,
                "standard": self._config.default_budget_standard,
                "deep": self._config.default_budget_deep,
                "monthly_limit": self._config.monthly_budget_limit,
            },
            "research": {
                "max_hops": self._config.max_hops,
                "similarity_threshold": self._config.semantic_similarity_threshold,
                "confidence_target": self._config.confidence_target,
            },
        }

    def set_custom_value(self, key: str, value: Any) -> None:
        """Set custom configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._custom_config[key] = value
        if self._config is not None:
            # Reload to apply custom value
            self.load(profile=self._profile, reload=True)

    @property
    def profile(self) -> ConfigProfile:
        """Get current configuration profile."""
        return self._profile


class ConfigurationError(Exception):
    """Configuration-related errors."""

    pass
