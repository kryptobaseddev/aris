"""Core ARIS functionality."""

from aris.core.config import ArisConfig, ConfigManager
from aris.core.document_merger import (
    DocumentMerger,
    MergeStrategy,
    Conflict,
    ConflictType,
)
from aris.core.progress_tracker import ProgressEventType, ProgressEvent, ProgressTracker
from aris.core.reasoning_engine import ReasoningEngine
from aris.core.research_orchestrator import ResearchOrchestrator, ResearchOrchestratorError

__all__ = [
    # Config
    "ArisConfig",
    "ConfigManager",
    # Document merging
    "DocumentMerger",
    "MergeStrategy",
    "Conflict",
    "ConflictType",
    # Progress tracking
    "ProgressEventType",
    "ProgressEvent",
    "ProgressTracker",
    # Reasoning
    "ReasoningEngine",
    # Orchestration
    "ResearchOrchestrator",
    "ResearchOrchestratorError",
]
