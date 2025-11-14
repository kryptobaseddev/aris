# ARIS Quick Start

**ARIS** - Autonomous Research Intelligence System
**Purpose**: Prevent document proliferation through semantic deduplication

---

## Installation

```bash
# Clone repository
git clone <repo-url>
cd aris-tool

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

---

## Usage (Python API)

ARIS is designed to be used as a **Python package** by AI agents:

```python
from pathlib import Path
from aris.models.config import ArisConfig
from aris.models.research import ResearchQuery, ResearchDepth

# 1. Configure ARIS
config = ArisConfig(
    research_dir=Path("./research"),
    database_path=Path("./.aris/metadata.db"),
    budget_limit=1.0  # $1 max per session
)
config.ensure_directories()

# 2. Create research query
query = ResearchQuery(
    query_text="What are transformer architectures?",
    depth=ResearchDepth.STANDARD,
    topic_area="AI/ML"
)

# 3. Execute research (requires API keys)
from aris.core.research_orchestrator import ResearchOrchestrator

async def run_research():
    orchestrator = ResearchOrchestrator(config)
    async with orchestrator as orch:
        session = orch.create_research_session(query)
        results = await orch.execute_research(session)
        return results

# Run
import asyncio
results = asyncio.run(run_research())
```

---

## Required API Keys

Set as environment variables:

```bash
export ARIS_TAVILY_API_KEY="your-tavily-key"       # For web search
export ARIS_ANTHROPIC_API_KEY="your-anthropic-key" # For reasoning
export ARIS_OPENAI_API_KEY="your-openai-key"       # For validation
```

---

## Core Features

✅ **Semantic Deduplication**: Similarity >0.85 → UPDATE existing document
✅ **Multi-Model Validation**: 2+ LLMs validate claims
✅ **Cost Tracking**: Budget limits per session
✅ **Git Versioning**: All document changes tracked
✅ **Session Persistence**: Resume research across runs

---

## Architecture

```
ResearchOrchestrator
├── DocumentFinder (semantic search)
├── QualityValidator (multi-model consensus)
├── DeduplicationGate (similarity checking)
├── DatabaseManager (metadata storage)
└── GitManager (version control)
```

---

## Testing

```bash
# Run unit tests (95%+ pass rate)
pytest tests/unit/ --ignore=tests/unit/storage/test_vector_store.py -v

# Run specific test category
pytest tests/unit/test_research_orchestrator.py -v
pytest tests/unit/test_quality_validator.py -v
pytest tests/unit/test_document_finder.py -v
```

---

## Project Status

- **Test Coverage**: 95.4% (289/303 unit tests passing)
- **Production Readiness**: Core functionality stable
- **Known Issues**: 14 research orchestrator tests (complex mocks)
- **Integration Tests**: Deferred (ChromaDB isolation needs work)

---

## For AI Agents

ARIS is designed to be called by AI agents as a library:

```python
# Minimal example for agent integration
from aris import research

result = await research.execute(
    query="Your research question",
    max_budget=0.50,
    update_existing=True  # Semantic deduplication
)

print(result.document_path)  # Where results were saved
print(result.was_updated)    # True if existing doc updated
print(result.cost)           # Actual cost incurred
```

---

## Documentation Structure

- `README.md` - Full project overview
- `QUICKSTART.md` - This file (how to use)
- `docs/architecture.md` - System design
- `docs/api.md` - Python API reference

---

## License

MIT - See LICENSE file
