"""Progress tracking for real-time CLI updates during research operations.

Provides event-driven progress tracking with callback support for streaming
updates to CLI interfaces or other consumers.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProgressEventType(str, Enum):
    """Types of progress events during research."""

    STARTED = "started"
    PLANNING = "planning"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ProgressEvent(BaseModel):
    """A single progress event with metadata."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: ProgressEventType
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

    # Optional progress indicators
    current: Optional[int] = None
    total: Optional[int] = None
    percentage: Optional[float] = None


class ProgressTracker:
    """Tracks and broadcasts progress events for research operations.

    Allows registration of callbacks for real-time progress updates,
    particularly useful for CLI streaming interfaces.

    Example:
        tracker = ProgressTracker()

        def print_progress(event: ProgressEvent):
            print(f"[{event.event_type}] {event.message}")

        tracker.register_callback(print_progress)
        tracker.update("Planning research...", ProgressEventType.PLANNING)
    """

    def __init__(self):
        """Initialize progress tracker."""
        self.events: list[ProgressEvent] = []
        self.callbacks: list[Callable[[ProgressEvent], None]] = []
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

    def register_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """Register a callback to receive progress events.

        Args:
            callback: Function that accepts ProgressEvent
        """
        self.callbacks.append(callback)
        logger.debug(f"Registered progress callback: {callback.__name__}")

    def unregister_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """Unregister a progress callback.

        Args:
            callback: Previously registered callback function
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.debug(f"Unregistered progress callback: {callback.__name__}")

    def update(
        self,
        message: str,
        event_type: ProgressEventType = ProgressEventType.INFO,
        data: Optional[dict[str, Any]] = None,
        current: Optional[int] = None,
        total: Optional[int] = None
    ) -> None:
        """Emit a progress update event.

        Args:
            message: Human-readable progress message
            event_type: Type of progress event
            data: Additional event data
            current: Current progress value (for percentage calculation)
            total: Total progress value (for percentage calculation)
        """
        # Calculate percentage if both current and total provided
        percentage = None
        if current is not None and total is not None and total > 0:
            percentage = (current / total) * 100.0

        event = ProgressEvent(
            event_type=event_type,
            message=message,
            data=data or {},
            current=current,
            total=total,
            percentage=percentage
        )

        self.events.append(event)
        logger.debug(f"Progress: [{event_type}] {message}")

        # Notify all callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in progress callback {callback.__name__}: {e}")

    def start(self, message: str = "Starting research...") -> None:
        """Mark the start of a tracked operation.

        Args:
            message: Start message
        """
        self._started_at = datetime.utcnow()
        self.update(message, ProgressEventType.STARTED)

    def complete(self, message: str = "Research complete") -> None:
        """Mark the completion of a tracked operation.

        Args:
            message: Completion message
        """
        self._completed_at = datetime.utcnow()
        self.update(message, ProgressEventType.COMPLETED)

    def error(self, message: str, error: Optional[Exception] = None) -> None:
        """Report an error event.

        Args:
            message: Error description
            error: Optional exception object
        """
        data = {}
        if error:
            data["error_type"] = type(error).__name__
            data["error_message"] = str(error)

        self.update(message, ProgressEventType.ERROR, data=data)

    def warning(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """Report a warning event.

        Args:
            message: Warning description
            data: Additional warning data
        """
        self.update(message, ProgressEventType.WARNING, data=data)

    def hop_progress(self, hop_number: int, max_hops: int, message: str) -> None:
        """Report progress for a research hop.

        Args:
            hop_number: Current hop number (1-indexed)
            max_hops: Maximum number of hops
            message: Hop status message
        """
        self.update(
            f"Hop {hop_number}/{max_hops}: {message}",
            ProgressEventType.SEARCHING,
            current=hop_number,
            total=max_hops
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get duration of tracked operation in seconds.

        Returns:
            Duration in seconds, or None if not yet completed
        """
        if self._started_at and self._completed_at:
            return (self._completed_at - self._started_at).total_seconds()
        elif self._started_at:
            return (datetime.utcnow() - self._started_at).total_seconds()
        return None

    @property
    def has_errors(self) -> bool:
        """Check if any error events were recorded.

        Returns:
            True if errors occurred
        """
        return any(e.event_type == ProgressEventType.ERROR for e in self.events)

    @property
    def has_warnings(self) -> bool:
        """Check if any warning events were recorded.

        Returns:
            True if warnings occurred
        """
        return any(e.event_type == ProgressEventType.WARNING for e in self.events)

    def get_events_by_type(self, event_type: ProgressEventType) -> list[ProgressEvent]:
        """Get all events of a specific type.

        Args:
            event_type: Type of events to retrieve

        Returns:
            List of matching events
        """
        return [e for e in self.events if e.event_type == event_type]

    def clear(self) -> None:
        """Clear all tracked events and reset state."""
        self.events.clear()
        self._started_at = None
        self._completed_at = None
        logger.debug("Progress tracker cleared")
