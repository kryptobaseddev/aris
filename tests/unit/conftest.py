"""Pytest configuration for unit tests.

This conftest.py runs before all tests and sets up critical mocks
to isolate tests from the real system environment.
"""

import pytest


@pytest.fixture(scope="function", autouse=True)
def isolate_environment(monkeypatch, request):
    """Isolate tests from real environment variables and system keyring.

    This fixture automatically:
    1. Clears all API key environment variables
    2. Mocks the keyring module to prevent touching real system keyring

    This ensures tests have clean state and real credentials never leak
    into test assertions.

    Applied at function scope with autouse=True to ensure it runs
    BEFORE any test class fixtures.
    """
    # Remove all API key environment variables (both prefixed and non-prefixed)
    env_vars_to_clear = [
        # Non-prefixed (used by pydantic-settings fallback)
        'TAVILY_API_KEY',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'GOOGLE_API_KEY',
        'SERENA_API_KEY',
        # Prefixed (ARIS_ prefix)
        'ARIS_TAVILY_API_KEY',
        'ARIS_ANTHROPIC_API_KEY',
        'ARIS_OPENAI_API_KEY',
        'ARIS_GOOGLE_API_KEY',
        'ARIS_PROFILE'
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # Prevent pydantic-settings from loading .env files by patching
    # the BaseSettings to use an empty env_file
    from pathlib import Path
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    empty_env = temp_dir / ".env"
    empty_env.write_text("")

    # Patch the ArisConfig model to use empty .env BY DEFAULT
    # Tests that need to load specific .env content will override via load(env_file=...)
    from aris.models.config import ArisConfig
    original_env_file = ArisConfig.model_config.get("env_file")
    ArisConfig.model_config["env_file"] = str(empty_env)

    #  Mock keyring to use in-memory storage instead of system keyring
    # This prevents tests from reading/writing real developer credentials
    test_keyring_storage = {}

    def mock_set_password(service: str, username: str, password: str):
        """Mock keyring.set_password() with in-memory storage."""
        test_keyring_storage[f"{service}:{username}"] = password

    def mock_get_password(service: str, username: str):
        """Mock keyring.get_password() with in-memory storage."""
        return test_keyring_storage.get(f"{service}:{username}")

    def mock_delete_password(service: str, username: str):
        """Mock keyring.delete_password() with in-memory storage."""
        key = f"{service}:{username}"
        if key in test_keyring_storage:
            del test_keyring_storage[key]

    # Apply keyring mocks to where they're USED (in aris.core.secrets module)
    # Not where they're defined (keyring module itself)
    monkeypatch.setattr("aris.core.secrets.keyring.set_password", mock_set_password)
    monkeypatch.setattr("aris.core.secrets.keyring.get_password", mock_get_password)
    monkeypatch.setattr("aris.core.secrets.keyring.delete_password", mock_delete_password)

    yield

    # Restore original model config
    if original_env_file is not None:
        ArisConfig.model_config["env_file"] = original_env_file
