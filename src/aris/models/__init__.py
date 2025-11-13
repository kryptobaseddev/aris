"""ARIS Data Models

Core Pydantic models for research documents, sessions, and metadata.
"""

from .document import Document, DocumentMetadata, DocumentStatus
from .research import ResearchQuery, ResearchSession, ResearchHop, ResearchResult
from .source import Source, SourceTier, SourceType
from .config import ArisConfig, LLMProvider
from .quality import (
    QualityGateLevel,
    SourceCredibilityTier,
    ConfidenceComponent,
    ConfidenceBreakdown,
    Contradiction,
    PreExecutionReport,
    PostExecutionReport,
    SourceCredibilityRecord,
    QualityMetrics,
    ValidationRule,
    ValidationGate,
)

__all__ = [
    # Document models
    "Document",
    "DocumentMetadata",
    "DocumentStatus",
    # Research models
    "ResearchQuery",
    "ResearchSession",
    "ResearchHop",
    "ResearchResult",
    # Source models
    "Source",
    "SourceTier",
    "SourceType",
    # Quality models
    "QualityGateLevel",
    "SourceCredibilityTier",
    "ConfidenceComponent",
    "ConfidenceBreakdown",
    "Contradiction",
    "PreExecutionReport",
    "PostExecutionReport",
    "SourceCredibilityRecord",
    "QualityMetrics",
    "ValidationRule",
    "ValidationGate",
    # Config models
    "ArisConfig",
    "LLMProvider",
]
