"""Circuit breaker pattern for resilient API calls.

Implements the circuit breaker pattern to prevent cascading failures
when external services (like Tavily API) experience issues.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failing, requests blocked immediately
- HALF_OPEN: Testing if service recovered, limited requests allowed
"""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests due to failures
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # Failures before opening circuit
    timeout_seconds: int = 60  # How long to stay OPEN before trying HALF_OPEN
    success_threshold: int = 2  # Successes in HALF_OPEN to close circuit


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is OPEN."""

    def __init__(self, message: str = "Circuit breaker is OPEN", next_attempt_in: Optional[float] = None):
        super().__init__(message)
        self.next_attempt_in = next_attempt_in


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

        if not breaker.can_execute():
            raise CircuitBreakerOpen("Service unavailable")

        try:
            result = api_call()
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            raise
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait in OPEN state before trying HALF_OPEN
            success_threshold: Successes needed in HALF_OPEN to close circuit
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
            success_threshold=success_threshold,
        )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()

    def can_execute(self) -> bool:
        """Check if request can proceed.

        Returns:
            True if request should proceed, False if blocked
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.last_failure_time is not None:
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure >= self.config.timeout_seconds:
                    # Transition to HALF_OPEN
                    self._transition_to_half_open()
                    return True
            return False

        # HALF_OPEN state - allow request to test recovery
        return True

    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                # Service recovered, close circuit
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed operation."""
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                # Too many failures, open circuit
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # Service still failing, back to OPEN
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.last_state_change = time.time()

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()

    def get_status(self) -> dict:
        """Get current circuit breaker status.

        Returns:
            Dictionary with current state and metrics
        """
        status = {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_in_current_state": time.time() - self.last_state_change,
        }

        if self.state == CircuitState.OPEN and self.last_failure_time:
            time_until_retry = self.config.timeout_seconds - (
                time.time() - self.last_failure_time
            )
            status["next_attempt_in_seconds"] = max(0, time_until_retry)

        return status

    def reset(self) -> None:
        """Reset circuit breaker to initial state (for testing)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
