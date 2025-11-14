# ARIS - Autonomous Research Intelligence System

AI-powered research engine that prevents document proliferation through semantic deduplication.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Set API keys in .env file
cp .env.example .env
# Edit .env with your keys:
#   ARIS_TAVILY_API_KEY=your-key
#   ARIS_ANTHROPIC_API_KEY=your-key
#   ARIS_OPENAI_API_KEY=your-key

# 3. Initialize project
aris init --name "My Research"

# 4. Run research
aris research "What are transformer architectures in AI?"
```

## How It Works

1. **Semantic Search**: Checks if similar research exists (>0.85 similarity)
2. **Smart Decision**: UPDATE existing document OR CREATE new one
3. **Multi-LLM Validation**: Uses your LLM providers for quality
4. **Git Tracking**: All changes versioned automatically

## Commands

```bash
aris init              # Initialize project
aris research "query"  # Run autonomous research
aris status            # Show project status
aris show <path>       # Display document
```

## Configuration

Set in `.env`:
- `ARIS_TAVILY_API_KEY` - Web search
- `ARIS_ANTHROPIC_API_KEY` - Primary LLM
- `ARIS_OPENAI_API_KEY` - Validation LLM
- `ARIS_BUDGET_LIMIT` - Max cost per research (default: $0.50)

## For AI Agents

ARIS is designed to be called by LLM agents:

```python
from aris import execute_research

result = await execute_research(
    query="Your research question",
    depth="standard",  # quick|standard|deep
    max_budget=0.50
)
# Returns: document path, cost, whether updated existing doc
```

## Project Status

- **Test Coverage**: 95%+ unit tests passing
- **Ready For**: Autonomous research execution
- **Core Features**: Semantic deduplication, multi-LLM validation, cost tracking

## License

MIT
