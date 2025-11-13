"""Shared pytest configuration and fixtures for all tests."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ============================================================================
# ASYNCIO EVENT LOOP CONFIGURATION
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TEMPORARY DIRECTORY FIXTURES
# ============================================================================


@pytest.fixture
def temp_aris_dir(tmp_path):
    """Create a temporary ARIS directory with standard subdirectories."""
    aris_dir = tmp_path / ".aris"
    aris_dir.mkdir()

    # Create standard subdirectories
    (aris_dir / "vectors").mkdir(parents=True, exist_ok=True)
    (aris_dir / "documents").mkdir(parents=True, exist_ok=True)
    (aris_dir / "sessions").mkdir(parents=True, exist_ok=True)

    return aris_dir


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client for testing."""
    client = MagicMock()
    client.request = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = MagicMock()
    store.add = MagicMock(return_value="embedding_id")
    store.search = MagicMock(return_value=[])
    store.delete = MagicMock()
    store.get_stats = MagicMock(return_value={"documents": 0})
    return store


# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "benchmark: marks tests as benchmarks",
    )
    config.addinivalue_line(
        "markers",
        "critical: marks tests as critical path validation",
    )


# ============================================================================
# CLEANUP HOOKS
# ============================================================================


@pytest.fixture(autouse=True)
def reset_state():
    """Reset any shared state between tests."""
    yield
    # Cleanup code here if needed
