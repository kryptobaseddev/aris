# Sequential MCP Quick Start Guide

## Installation

Ensure Sequential Thinking MCP server is available:
```bash
npx @modelcontextprotocol/server-sequential-thinking
```

## Basic Usage

### 1. Simple Query Analysis
```python
from aris.core.config import ConfigManager
from aris.core.reasoning_engine import ReasoningEngine

# Initialize
config = ConfigManager.get_instance().get_config()
engine = ReasoningEngine(config)

# Analyze query
plan = await engine.analyze_query("How do LLMs reason?")
print(plan.topics)        # Key research topics
print(plan.hypotheses)    # Potential hypotheses
print(plan.estimated_hops) # Expected iterations
```

### 2. Execute Single Hop
```python
# Execute one research iteration
hop_result = await engine.execute_research_hop(plan, hop_number=1)

print(f"Confidence: {hop_result.synthesis.confidence:.2f}")
print(f"Evidence: {hop_result.evidence_count}")
print(f"Key findings: {hop_result.synthesis.key_findings}")
```

### 3. Complete Multi-Hop Research
```python
# Full workflow with automatic stopping
async with ReasoningEngine(config) as engine:
    context = await engine.execute_multi_hop_research(
        query="How do LLMs reason?",
        max_hops=5  # Optional, defaults to config.max_hops
    )

    print(f"Hops: {context.current_hop}")
    print(f"Confidence: {context.overall_confidence:.2f}")
    print(f"Findings: {context.final_synthesis.key_findings}")
```

## Key Classes

### ResearchPlan
```python
from aris.mcp import ResearchPlan

plan = ResearchPlan(
    query="Research question",
    topics=["topic1", "topic2"],
    hypotheses=["hypothesis1", "hypothesis2"],
    information_gaps=["gap1"],
    success_criteria=["criteria1"],
    estimated_hops=3
)
```

### Hypothesis
```python
from aris.mcp import Hypothesis

hypothesis = Hypothesis(
    statement="LLMs use attention for reasoning",
    confidence_prior=0.5,  # Initial confidence (0-1)
    evidence_required=["papers", "experiments"],
    test_method="literature review"
)
```

### HypothesisResult
```python
from aris.mcp import HypothesisResult

result = HypothesisResult(
    hypothesis=hypothesis,
    confidence_posterior=0.75,  # Updated confidence
    supporting_evidence=[...],   # Evidence supporting
    contradicting_evidence=[...], # Evidence contradicting
    conclusion="Hypothesis supported by evidence"
)

# Properties
print(result.confidence_change)  # 0.25 (0.75 - 0.5)
print(result.evidence_ratio)     # Ratio of supporting to total
```

### Synthesis
```python
from aris.mcp import Synthesis

synthesis = Synthesis(
    key_findings=["Finding 1", "Finding 2"],
    confidence=0.8,
    gaps_remaining=["Gap 1"],
    recommendations=["Next step"]
)

# Properties
print(synthesis.has_high_confidence)  # True if >= 0.7
print(synthesis.needs_more_research)  # True if low confidence or gaps
```

## Configuration

Required config values (in `.env` or environment):
```bash
# Sequential MCP (local)
ARIS_SEQUENTIAL_MCP_PATH=npx

# Tavily API (for evidence gathering)
ARIS_TAVILY_API_KEY=tvly-...

# Research parameters
ARIS_MAX_HOPS=5
ARIS_CONFIDENCE_TARGET=0.70
ARIS_EARLY_STOP_CONFIDENCE=0.85
```

## Control Flow

```
1. analyze_query() → ResearchPlan
   ↓
2. execute_research_hop() → HopResult
   ├─ generate_hypotheses()
   ├─ gather_evidence() (via Tavily)
   ├─ test_hypothesis() (for each)
   └─ synthesize_findings()
   ↓
3. Check confidence
   ├─ >= early_stop → DONE
   ├─ >= target → DONE
   └─ < target → Next hop
   ↓
4. Max hops reached → DONE
```

## Error Handling

### Tavily Search Errors
```python
# Errors are logged and skipped
evidence = await engine._gather_evidence(topics)
# Returns partial evidence even if some searches fail
```

### Sequential MCP Errors
```python
# Bubble up as RuntimeError
try:
    plan = await client.plan_research(query)
except RuntimeError as e:
    print(f"MCP error: {e}")
```

### Session Management
```python
# Always use async context manager
async with ReasoningEngine(config) as engine:
    # Work with engine
    pass
# Resources automatically cleaned up

# Or manual management
engine = ReasoningEngine(config)
await engine.sequential.start_session()
# ... work ...
await engine.close()
```

## Cost Tracking

```python
# Track Tavily API costs
context = await engine.execute_multi_hop_research(query)

cost_summary = engine.get_cost_summary()
print(f"Total: ${cost_summary['total_cost']:.2f}")
print(f"Operations: {cost_summary['operation_count']}")
print(f"By type: {cost_summary['by_type']}")
```

## Testing

Run tests:
```bash
# All Sequential tests
pytest tests/unit/test_sequential_client.py -v
pytest tests/integration/test_reasoning_workflow.py -v

# With coverage
pytest tests/ -k "sequential or reasoning" --cov=src/aris/mcp --cov=src/aris/core
```

## Common Patterns

### Follow-Up Queries
```python
# Generate follow-up queries from gaps
synthesis = hop_result.synthesis
if synthesis.has_gaps:
    queries = await engine.generate_follow_up_queries(synthesis)
    for query in queries:
        print(f"Follow-up: {query}")
```

### Hypothesis Refinement
```python
# Refine hypothesis with new evidence
new_evidence = [{"title": "New Source", "url": "...", "content": "..."}]
refined_result = await engine.refine_hypothesis(hypothesis, new_evidence)
print(f"Updated confidence: {refined_result.confidence_posterior}")
```

### Context Access
```python
# Access current reasoning state
context = engine.get_context()
if context:
    print(f"Current hop: {context.current_hop}")
    print(f"Total evidence: {context.total_evidence}")
    print(f"Overall confidence: {context.overall_confidence}")
```

## File Structure

```
src/aris/
├── mcp/
│   ├── sequential_client.py       # Sequential MCP client
│   ├── reasoning_schemas.py       # Pydantic models
│   ├── tavily_client.py          # Tavily integration
│   └── __init__.py               # Exports
├── core/
│   └── reasoning_engine.py       # High-level API
└── models/
    └── config.py                 # Configuration

tests/
├── unit/
│   └── test_sequential_client.py
└── integration/
    └── test_reasoning_workflow.py
```

## Next Steps

For Agent 3 (Research Orchestrator):
1. Create research strategies (quick/standard/deep/exhaustive)
2. Implement session persistence with Serena MCP
3. Add CLI commands (`aris research`, etc.)
4. Integrate with document generation
5. Add conflict detection and resolution
6. Implement parallel hypothesis branches

## Troubleshooting

### MCP Server Not Found
```bash
# Install Sequential MCP server
npm install -g @modelcontextprotocol/server-sequential-thinking

# Or use npx (automatic download)
npx @modelcontextprotocol/server-sequential-thinking
```

### Import Errors
```bash
# Ensure dependencies installed
pip install pydantic httpx pytest pytest-asyncio

# Or install ARIS in development mode
pip install -e .
```

### Confidence Too Low
- Increase `max_hops` in config
- Lower `confidence_target`
- Provide better context in query
- Use more specific topics

### Too Many Hops
- Increase `confidence_target`
- Enable `early_stop_confidence`
- Provide clearer success criteria
- Use more focused queries
