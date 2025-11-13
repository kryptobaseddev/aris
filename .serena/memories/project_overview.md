# ARIS Project Overview

## Purpose
ARIS (Autonomous Research Intelligence System) is a research orchestration system that solves document proliferation by intelligently updating existing documents instead of creating duplicates.

## Core Value Proposition
- Semantic deduplication using vector similarity search
- Multi-model validation for claim verification
- Intelligent document updates with Git-based version history
- Cost-optimized research workflow (<$0.50 per query target)

## Tech Stack
- **Language**: Python 3.11+
- **CLI**: Click + Rich (structured output)
- **Config**: Pydantic + pydantic-settings
- **Security**: keyring (system keyring integration)
- **Database**: SQLite (MVP) → PostgreSQL (future)
- **ORM**: SQLAlchemy + Alembic migrations
- **Testing**: pytest + pytest-cov + pytest-asyncio
- **Code Quality**: Black, Ruff, mypy (strict mode)

## Project Structure
```
aris-tool/
├── src/aris/
│   ├── cli/          # CLI commands
│   ├── core/         # Core system (config, state management)
│   ├── models/       # Pydantic data models
│   ├── storage/      # Database layer
│   ├── mcp/          # MCP client integrations
│   └── utils/        # Utilities
├── tests/
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── e2e/          # End-to-end tests
├── docs/             # MVP requirements
├── claudedocs/       # Original architecture docs
└── pyproject.toml    # Poetry dependencies
```

## Development Status
- **Phase**: Wave 1 - Foundation Implementation
- **Agent 1**: Central Configuration & API Key Management (COMPLETE)
- **Next**: Agent 2 - Database Schema Implementation
