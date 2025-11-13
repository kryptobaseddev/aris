"""MCP (Model Context Protocol) integrations for ARIS.

This module provides integrations with external MCP servers:
- Tavily: Web search and content extraction
- Sequential Thinking: Multi-step reasoning and hypothesis testing
- Playwright: Browser automation (planned)
"""

from aris.mcp.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState
from aris.mcp.complexity_analyzer import (
    ComplexityAnalysis,
    ComplexityAnalyzer,
    ComplexityIndicators,
    ExtractionMethod,
)
from aris.mcp.reasoning_schemas import (
    HopResult,
    Hypothesis,
    HypothesisResult,
    ReasoningContext,
    ResearchPlan,
    Synthesis,
)
from aris.mcp.sequential_client import MCPSession, SequentialClient
from aris.mcp.serena_client import MemoryEntry, SerenaClient, SessionContext
from aris.mcp.tavily_client import (
    CostOperation,
    CostTracker,
    TavilyAPIError,
    TavilyAuthenticationError,
    TavilyClient,
    TavilyRateLimitError,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
    # Complexity Analyzer
    "ComplexityAnalyzer",
    "ComplexityAnalysis",
    "ComplexityIndicators",
    "ExtractionMethod",
    # Reasoning Schemas
    "HopResult",
    "Hypothesis",
    "HypothesisResult",
    "ReasoningContext",
    "ResearchPlan",
    "Synthesis",
    # Sequential Client
    "MCPSession",
    "SequentialClient",
    # Serena Client
    "SerenaClient",
    "SessionContext",
    "MemoryEntry",
    # Tavily Client
    "TavilyClient",
    "TavilyAPIError",
    "TavilyAuthenticationError",
    "TavilyRateLimitError",
    "CostTracker",
    "CostOperation",
]
