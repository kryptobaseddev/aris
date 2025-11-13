"""ARIS configuration models."""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    CLAUDE = "claude_sonnet_4.5"
    GPT = "gpt_5"
    GEMINI = "gemini_pro_2.0"


class ArisConfig(BaseSettings):
    """ARIS system configuration (loads from environment and config file)."""

    model_config = SettingsConfigDict(
        env_prefix="ARIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Project paths
    project_root: Path = Field(default=Path.cwd())
    research_dir: Path = Field(default=Path.cwd() / "research")
    database_path: Path = Field(default=Path.cwd() / ".aris" / "metadata.db")
    cache_dir: Path = Field(default=Path.cwd() / ".aris" / "cache")

    # LLM Configuration
    preferred_llm: LLMProvider = LLMProvider.GEMINI  # Cost-optimized default
    fallback_llm: Optional[LLMProvider] = LLMProvider.CLAUDE

    # API Keys (loaded from OS keyring, not stored here)
    tavily_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Budget defaults
    default_budget_quick: float = 0.20
    default_budget_standard: float = 0.50
    default_budget_deep: float = 2.00
    monthly_budget_limit: float = 50.00

    # Research parameters
    max_hops: int = 5
    semantic_similarity_threshold: float = 0.85  # For deduplication
    confidence_target: float = 0.70
    early_stop_confidence: float = 0.85

    # MCP Server endpoints (local by default)
    tavily_endpoint: Optional[str] = None  # Uses API directly
    sequential_mcp_path: str = "npx"  # Local Sequential MCP
    serena_mcp_path: str = "npx"  # Local Serena MCP
    playwright_mcp_path: str = "npx"  # Local Playwright MCP

    # Performance
    cache_ttl_seconds: int = 3600  # 1 hour
    max_parallel_searches: int = 5
    request_timeout_seconds: int = 30

    # Quality
    min_source_credibility: float = 0.5
    require_validation_below_confidence: float = 0.6

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def git_repo_path(self) -> Path:
        """Git repository for research documents."""
        return self.research_dir
