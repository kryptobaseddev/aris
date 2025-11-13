"""Unit tests for circuit breaker implementation."""

import pytest
import time
from aris.mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
)


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""

    def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute()

    def test_record_success(self):
        """Test recording successful operations."""
        breaker = CircuitBreaker()
        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    def test_record_failure(self):
        """Test recording failed operations."""
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    def test_open_after_threshold(self):
        """Test circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3)

        # Record 3 failures
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not breaker.can_execute()

    def test_open_blocks_requests(self):
        """Test OPEN state blocks new requests."""
        breaker = CircuitBreaker(failure_threshold=2)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not breaker.can_execute()

    def test_half_open_after_timeout(self):
        """Test transition to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Should transition to HALF_OPEN
        assert breaker.can_execute()
        assert breaker.state == CircuitState.HALF_OPEN

    def test_close_from_half_open_on_success(self):
        """Test closing circuit from HALF_OPEN on success."""
        breaker = CircuitBreaker(
            failure_threshold=2, timeout_seconds=1, success_threshold=2
        )

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait and transition to HALF_OPEN
        time.sleep(1.1)
        breaker.can_execute()
        assert breaker.state == CircuitState.HALF_OPEN

        # Record successes to close
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED

    def test_reopen_from_half_open_on_failure(self):
        """Test reopening circuit from HALF_OPEN on failure."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Wait and transition to HALF_OPEN
        time.sleep(1.1)
        breaker.can_execute()
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_get_status(self):
        """Test status reporting."""
        breaker = CircuitBreaker()
        status = breaker.get_status()

        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["state"] == CircuitState.CLOSED.value

    def test_get_status_with_next_attempt(self):
        """Test status includes next attempt time when OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=10)

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()

        status = breaker.get_status()
        assert status["state"] == CircuitState.OPEN.value
        assert "next_attempt_in_seconds" in status
        assert status["next_attempt_in_seconds"] > 0

    def test_reset(self):
        """Test resetting circuit breaker."""
        breaker = CircuitBreaker()

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.can_execute()

    def test_success_resets_failure_count(self):
        """Test success resets failure count in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=5)

        # Accumulate some failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2

        # Success should reset count
        breaker.record_success()
        assert breaker.failure_count == 0

    def test_configurable_thresholds(self):
        """Test configurable failure and success thresholds."""
        breaker = CircuitBreaker(failure_threshold=10, success_threshold=3)

        assert breaker.config.failure_threshold == 10
        assert breaker.config.success_threshold == 3

    def test_configurable_timeout(self):
        """Test configurable timeout duration."""
        breaker = CircuitBreaker(timeout_seconds=120)
        assert breaker.config.timeout_seconds == 120

    def test_circuit_breaker_exception(self):
        """Test CircuitBreakerOpen exception."""
        exception = CircuitBreakerOpen("Test message", next_attempt_in=30.0)
        assert str(exception) == "Test message"
        assert exception.next_attempt_in == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
