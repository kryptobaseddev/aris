"""Secure API key management using system keyring.

This module provides secure storage and retrieval of API keys using the system
keyring (Keychain on macOS, Windows Credential Locker, Secret Service on Linux).

API keys are NEVER stored in plaintext in configuration files or environment variables
in production usage.
"""

import logging
from typing import Optional

import keyring
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)


class SecureKeyManager:
    """Manages API keys using system keyring.

    All API keys are stored in the system keyring under the service name "aris".
    Each key is identified by its provider name (e.g., "tavily", "anthropic").

    Example:
        manager = SecureKeyManager()
        manager.set_api_key("tavily", "tvly-xxxxx")
        key = manager.get_api_key("tavily")
        manager.delete_api_key("tavily")
    """

    SERVICE_NAME = "aris"

    def __init__(self) -> None:
        """Initialize secure key manager."""
        self._verify_keyring_available()

    def _verify_keyring_available(self) -> None:
        """Verify that keyring backend is available.

        Raises:
            KeyringNotAvailableError: If no keyring backend is available
        """
        try:
            # Test keyring availability
            backend = keyring.get_keyring()
            if backend is None:
                raise KeyringNotAvailableError(
                    "No keyring backend available. "
                    "Install keyring backend for your platform."
                )

            # Check if we're using the null keyring (fallback when no real backend exists)
            backend_name = type(backend).__name__
            if "Null" in backend_name or "Fail" in backend_name:
                logger.warning(
                    f"Using fallback keyring backend: {backend_name}. "
                    "API keys may not persist securely. "
                    "Install platform keyring backend for production use."
                )
        except Exception as e:
            raise KeyringNotAvailableError(
                f"Failed to initialize keyring: {e}"
            ) from e

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Store API key securely in system keyring.

        Args:
            provider: Provider identifier (e.g., "tavily", "anthropic", "openai", "google")
            api_key: The API key to store

        Raises:
            KeyringError: If keyring storage fails
            ValueError: If provider or api_key is empty
        """
        if not provider or not provider.strip():
            raise ValueError("Provider name cannot be empty")

        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        provider_normalized = provider.lower().strip()

        try:
            keyring.set_password(self.SERVICE_NAME, provider_normalized, api_key)
            logger.info(f"Successfully stored API key for provider: {provider_normalized}")
        except KeyringError as e:
            logger.error(f"Failed to store API key for {provider_normalized}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error storing API key for {provider_normalized}: {e}"
            )
            raise KeyringError(f"Failed to store API key: {e}") from e

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key from system keyring.

        Args:
            provider: Provider identifier (e.g., "tavily", "anthropic", "openai", "google")

        Returns:
            The API key if found, None otherwise

        Raises:
            KeyringError: If keyring access fails (not if key is missing)
        """
        if not provider or not provider.strip():
            return None

        provider_normalized = provider.lower().strip()

        try:
            api_key = keyring.get_password(self.SERVICE_NAME, provider_normalized)
            if api_key:
                logger.debug(f"Retrieved API key for provider: {provider_normalized}")
            else:
                logger.debug(f"No API key found for provider: {provider_normalized}")
            return api_key
        except KeyringError as e:
            logger.error(f"Failed to retrieve API key for {provider_normalized}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving API key for {provider_normalized}: {e}"
            )
            raise KeyringError(f"Failed to retrieve API key: {e}") from e

    def delete_api_key(self, provider: str) -> bool:
        """Delete API key from system keyring.

        Args:
            provider: Provider identifier (e.g., "tavily", "anthropic", "openai", "google")

        Returns:
            True if key was deleted, False if key did not exist

        Raises:
            KeyringError: If keyring deletion fails
        """
        if not provider or not provider.strip():
            return False

        provider_normalized = provider.lower().strip()

        try:
            # Check if key exists before deletion
            existing_key = keyring.get_password(self.SERVICE_NAME, provider_normalized)
            if existing_key is None:
                logger.debug(f"No API key to delete for provider: {provider_normalized}")
                return False

            keyring.delete_password(self.SERVICE_NAME, provider_normalized)
            logger.info(f"Successfully deleted API key for provider: {provider_normalized}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to delete API key for {provider_normalized}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error deleting API key for {provider_normalized}: {e}"
            )
            raise KeyringError(f"Failed to delete API key: {e}") from e

    def list_providers(self) -> list[str]:
        """List all providers with stored API keys.

        Note: This is a best-effort operation as not all keyring backends
        support enumeration. Returns empty list if enumeration is not supported.

        Returns:
            List of provider names with stored keys

        Raises:
            KeyringError: If keyring access fails
        """
        # Keyring doesn't provide a standard way to list all keys for a service
        # We'll check known providers
        known_providers = ["tavily", "anthropic", "openai", "google"]
        found_providers = []

        for provider in known_providers:
            try:
                if self.get_api_key(provider) is not None:
                    found_providers.append(provider)
            except KeyringError:
                # Skip providers that fail to access
                continue

        return found_providers

    def verify_key_exists(self, provider: str) -> bool:
        """Check if API key exists for provider.

        Args:
            provider: Provider identifier

        Returns:
            True if key exists, False otherwise
        """
        try:
            return self.get_api_key(provider) is not None
        except KeyringError:
            return False

    def get_all_keys(self) -> dict[str, Optional[str]]:
        """Retrieve all API keys for known providers.

        Returns:
            Dictionary mapping provider names to API keys (or None if not set)

        Raises:
            KeyringError: If keyring access fails
        """
        known_providers = ["tavily", "anthropic", "openai", "google"]
        keys = {}

        for provider in known_providers:
            try:
                keys[provider] = self.get_api_key(provider)
            except KeyringError as e:
                logger.warning(f"Failed to retrieve key for {provider}: {e}")
                keys[provider] = None

        return keys

    @classmethod
    def clear_all_keys(cls) -> int:
        """Clear all ARIS API keys from keyring.

        Warning: This will delete ALL API keys stored by ARIS.
        Use with caution, typically only for cleanup or testing.

        Returns:
            Number of keys deleted

        Raises:
            KeyringError: If keyring access fails
        """
        manager = cls()
        known_providers = ["tavily", "anthropic", "openai", "google"]
        deleted_count = 0

        for provider in known_providers:
            try:
                if manager.delete_api_key(provider):
                    deleted_count += 1
            except KeyringError as e:
                logger.warning(f"Failed to delete key for {provider}: {e}")

        logger.info(f"Cleared {deleted_count} API keys from keyring")
        return deleted_count


class KeyringNotAvailableError(Exception):
    """Raised when keyring backend is not available."""

    pass
