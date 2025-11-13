# Cost Estimation Gap Analysis & Solution

## Problem Statement

**Gap**: ARIS has no pre-research cost estimation capability
**Impact**: Users cannot see projected costs before starting research
**Classification**: Critical for $0.50 budget target assurance
**Priority**: HIGH
**Effort**: 2-4 hours (moderate)

---

## Current State

### What Works
✅ Cost tracking during research (real-time)
✅ Budget enforcement (hard stops at 100%)
✅ Cost history and reporting (post-research)
✅ Warning system (75%, 90%, 100%)

### What's Missing
❌ Pre-research cost estimation
❌ Cost projection before execution
❌ Query complexity analysis
❌ User feedback loop before commitment

---

## Why This Matters

### User Journey (Current - Reactive)
```
User: "Search for AI safety research"
     ↓
System: "Executing standard depth research with $0.50 budget..."
     ↓
[Research begins]
     ↓
[At 90% cost]: "Warning: Approaching budget limit"
     ↓
[At 100% cost]: "Research stopped - budget exceeded"
     ↓
User: "I didn't know it would cost that much!"
```

### User Journey (Desired - Proactive)
```
User: "Search for AI safety research"
     ↓
System: "Estimated cost analysis:
         - Tavily searches: ~15
         - LLM tokens: ~9K
         - Projected total: $0.24
         - Budget: $0.50
         Ready to proceed? (Y/n)"
     ↓
User: "Yes, proceed"
     ↓
[Research begins with confidence]
     ↓
System: "Real-time: $0.12 spent (24% of budget)"
     ↓
[Research completes within budget]
```

---

## Proposed Solution

### Module: Cost Estimator

**Location**: `src/aris/core/cost_estimator.py` (new file)
**Responsibilities**:
1. Analyze query complexity
2. Estimate required searches
3. Estimate token usage
4. Return cost breakdown

**Key Methods**:
```python
@dataclass
class CostEstimate:
    """Estimated cost for research query."""
    estimated_tavily_searches: int
    estimated_tokens: int
    estimated_tavily_cost: float
    estimated_llm_cost: float
    estimated_total_cost: float
    confidence: float  # 0.0-1.0
    breakdown: dict  # By phase
    warning: Optional[str]

class CostEstimator:
    """Estimate research costs before execution."""

    async def estimate_research_cost(
        self,
        query: str,
        depth: str = "standard",
        budget_limit: Optional[float] = None
    ) -> CostEstimate:
        """Estimate cost for research query.

        Args:
            query: Research question
            depth: Research depth (quick, standard, deep)
            budget_limit: Optional budget for comparison

        Returns:
            CostEstimate with breakdown and confidence
        """

    async def analyze_query_complexity(query: str) -> float:
        """Analyze query complexity (0.0-1.0)."""

    def estimate_searches_for_depth(depth: str, complexity: float) -> int:
        """Estimate number of searches based on depth and complexity."""

    def estimate_tokens_for_depth(depth: str, complexity: float) -> int:
        """Estimate tokens based on depth and complexity."""
```

---

## Implementation Details

### 1. Query Complexity Analysis

```python
async def analyze_query_complexity(query: str) -> float:
    """Analyze query complexity on 0.0-1.0 scale.

    Factors:
    - Query length (longer = more complex)
    - Entity count (more entities = more searches)
    - Modifier count (AND, OR, NOT = more complex)
    - Domain specificity (specialized = complex)

    Returns:
        Complexity score 0.0 (simple) to 1.0 (very complex)
    """
    score = 0.0

    # Length factor (0.0-0.2)
    word_count = len(query.split())
    score += min(0.2, word_count / 20)

    # Entity factor (0.0-0.3)
    entities = count_entities(query)  # "Apple", "Microsoft", dates, etc.
    score += min(0.3, entities / 5)

    # Modifier factor (0.0-0.2)
    modifiers = count_modifiers(query)  # AND, OR, NOT, quotes, etc.
    score += min(0.2, modifiers / 3)

    # Domain specificity (0.0-0.3)
    domain_score = analyze_domain_specificity(query)  # ML, crypto, etc.
    score += domain_score * 0.3

    return min(1.0, score)
```

### 2. Search Estimation

```python
def estimate_searches_for_depth(
    depth: str,
    complexity: float
) -> int:
    """Estimate number of searches needed.

    Base searches per depth:
    - quick: 3 searches (1 hop × 3)
    - standard: 15 searches (3 hops × 5)
    - deep: 25 searches (5 hops × 5)

    Complexity multiplier (0.5x to 1.5x):
    - Simple query (0.0-0.3): 0.5x - 0.8x
    - Moderate (0.3-0.7): 1.0x
    - Complex (0.7-1.0): 1.2x - 1.5x
    """
    base_searches = {
        "quick": 3,
        "standard": 15,
        "deep": 25,
    }

    # Complexity multiplier
    if complexity < 0.3:
        multiplier = 0.6  # Simple queries need fewer searches
    elif complexity < 0.7:
        multiplier = 1.0  # Moderate
    else:
        multiplier = 1.3  # Complex queries need more searches

    return int(base_searches[depth] * multiplier)
```

### 3. Token Estimation

```python
def estimate_tokens_for_depth(
    depth: str,
    complexity: float
) -> int:
    """Estimate LLM tokens needed.

    Base tokens per hop:
    - quick: 2K (1 hop × 2K)
    - standard: 9K (3 hops × 3K)
    - deep: 20K (5 hops × 4K)

    Complexity multiplier (0.7x to 1.4x):
    - Simple: use less analysis tokens
    - Complex: use more reasoning tokens
    """
    base_tokens = {
        "quick": 2000,
        "standard": 9000,
        "deep": 20000,
    }

    # Complexity multiplier
    if complexity < 0.3:
        multiplier = 0.8
    elif complexity < 0.7:
        multiplier = 1.0
    else:
        multiplier = 1.3

    return int(base_tokens[depth] * multiplier)
```

### 4. Main Estimation Method

```python
async def estimate_research_cost(
    self,
    query: str,
    depth: str = "standard",
    budget_limit: Optional[float] = None
) -> CostEstimate:
    """Estimate complete research cost."""

    # Step 1: Analyze complexity
    complexity = await self.analyze_query_complexity(query)

    # Step 2: Estimate searches
    estimated_searches = self.estimate_searches_for_depth(depth, complexity)
    tavily_cost = estimated_searches * self.TAVILY_COST_PER_SEARCH

    # Step 3: Estimate tokens
    estimated_tokens = self.estimate_tokens_for_depth(depth, complexity)
    llm_cost = (estimated_tokens / 1000) * self.LLM_COST_PER_1K_TOKENS

    # Step 4: Calculate total
    total_cost = tavily_cost + llm_cost

    # Step 5: Check against budget
    warning = None
    if budget_limit and total_cost > budget_limit:
        warning = (
            f"Estimated cost (${total_cost:.2f}) exceeds budget "
            f"(${budget_limit:.2f}). Consider reducing depth."
        )

    # Step 6: Confidence score
    confidence = 0.75  # Base confidence
    if complexity < 0.3:
        confidence = 0.85  # Simple queries = higher confidence
    elif complexity > 0.7:
        confidence = 0.65  # Complex queries = lower confidence

    return CostEstimate(
        estimated_tavily_searches=estimated_searches,
        estimated_tokens=estimated_tokens,
        estimated_tavily_cost=round(tavily_cost, 4),
        estimated_llm_cost=round(llm_cost, 4),
        estimated_total_cost=round(total_cost, 4),
        confidence=confidence,
        breakdown={
            "by_service": {
                "tavily": {"count": estimated_searches, "cost": tavily_cost},
                "llm": {"tokens": estimated_tokens, "cost": llm_cost},
            },
            "by_depth": depth,
            "complexity_score": complexity,
        },
        warning=warning,
    )
```

---

## Integration Points

### 1. Research Commands

**File**: `src/aris/cli/research_commands.py`

```python
# Add before executing research
cost_estimator = CostEstimator(config)
estimate = await cost_estimator.estimate_research_cost(
    query=query,
    depth=depth,
    budget_limit=budget_limit
)

# Show estimate to user
console.print(Panel(
    f"[bold cyan]Cost Estimation[/bold cyan]\n"
    f"Query complexity: {estimate.breakdown['complexity_score']:.0%}\n"
    f"Estimated searches: {estimate.estimated_tavily_searches}\n"
    f"Estimated tokens: {estimate.estimated_tokens:,}\n"
    f"Estimated cost: [yellow]${estimate.estimated_total_cost:.2f}[/yellow]\n"
    f"Budget: [green]${budget_limit:.2f}[/green]\n"
    f"Confidence: {estimate.confidence:.0%}"
))

if estimate.warning:
    console.print(f"[red]⚠️ {estimate.warning}[/red]")

# Ask for confirmation
if not click.confirm("Proceed with research?"):
    raise click.Abort()
```

### 2. ResearchOrchestrator Integration

**File**: `src/aris/core/research_orchestrator.py`

```python
# In execute_research() method, add before _execute_research_hops()

from aris.core.cost_estimator import CostEstimator

estimator = CostEstimator(self.config)
estimate = await estimator.estimate_research_cost(
    query=query,
    depth=depth,
    budget_limit=session.budget_target
)

# Log estimate
logger.info(
    f"Cost estimate: ${estimate.estimated_total_cost:.2f} "
    f"({estimate.confidence:.0%} confidence)"
)

# Store in session for comparison with actual
session.cost_estimate = estimate
```

### 3. Cost Command Enhancement

**File**: `src/aris/cli/cost_commands.py`

Add new command:
```python
@cost_group.command()
@click.argument("query")
@click.option("--depth", default="standard")
@click.option("--budget", type=float, default=0.50)
@click.pass_context
def estimate(ctx: click.Context, query: str, depth: str, budget: float) -> None:
    """Estimate cost for a research query before execution.

    Example:
        aris cost estimate "AI safety research" --depth standard
    """
    try:
        config = ConfigManager.get_instance()
        estimator = CostEstimator(config)

        import asyncio
        estimate = asyncio.run(
            estimator.estimate_research_cost(query, depth, budget)
        )

        # Display estimate
        table = Table(title="Cost Estimate")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Query Complexity", f"{estimate.breakdown['complexity_score']:.0%}")
        table.add_row("Estimated Searches", str(estimate.estimated_tavily_searches))
        table.add_row("Estimated Tokens", f"{estimate.estimated_tokens:,}")
        table.add_row("Tavily Cost", f"${estimate.estimated_tavily_cost:.4f}")
        table.add_row("LLM Cost", f"${estimate.estimated_llm_cost:.4f}")
        table.add_row("Total Cost", f"${estimate.estimated_total_cost:.4f}")
        table.add_row("Budget", f"${budget:.4f}")
        table.add_row("Budget Status",
            f"✓ OK" if estimate.estimated_total_cost <= budget else "✗ OVER"
        )
        table.add_row("Confidence", f"{estimate.confidence:.0%}")

        console.print(table)

        if estimate.warning:
            console.print(f"[red]⚠️ {estimate.warning}[/red]")

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        ctx.exit(1)
```

---

## Testing Strategy

### Unit Tests

```python
# test_cost_estimator.py

def test_simple_query_complexity():
    estimator = CostEstimator(config)
    score = await estimator.analyze_query_complexity("What is AI?")
    assert 0.0 <= score <= 0.3  # Should be simple

def test_complex_query_complexity():
    estimator = CostEstimator(config)
    score = await estimator.analyze_query_complexity(
        "Latest advances in transformer architectures AND "
        "their applications in NLP AND implications for AGI safety"
    )
    assert 0.7 <= score <= 1.0  # Should be complex

def test_estimate_quick_depth():
    estimator = CostEstimator(config)
    estimate = await estimator.estimate_research_cost(
        "AI research", depth="quick"
    )
    assert estimate.estimated_total_cost < 0.20  # Should be cheap
    assert estimate.estimated_tavily_searches <= 5

def test_estimate_standard_depth():
    estimator = CostEstimator(config)
    estimate = await estimator.estimate_research_cost(
        "AI research", depth="standard"
    )
    assert estimate.estimated_total_cost <= 0.50  # Should fit budget
    assert 10 <= estimate.estimated_tavily_searches <= 20

def test_over_budget_warning():
    estimator = CostEstimator(config)
    estimate = await estimator.estimate_research_cost(
        "Complex AI safety AND quantum computing research AND "
        "biological implications AND regulatory frameworks",
        depth="deep",
        budget_limit=0.50
    )
    assert estimate.warning is not None
    assert "exceeds budget" in estimate.warning
```

### Integration Tests

```python
# Test end-to-end workflow
def test_estimate_then_execute():
    # 1. Get estimate
    estimate = await estimator.estimate_research_cost(query, depth)

    # 2. Execute research
    result = await orchestrator.execute_research(query, depth)

    # 3. Compare actual vs estimated
    actual_cost = result.total_cost
    estimated_cost = estimate.estimated_total_cost

    # Should be within 50% of estimate (allowing for variance)
    assert abs(actual_cost - estimated_cost) / estimated_cost < 0.5
```

---

## Expected Outcomes

### Before Implementation
```
Query: "AI safety research"
System: "Executing standard depth research..."
[No feedback until warnings]
```

### After Implementation
```
Query: "AI safety research"
System: "Cost Estimation:
         - Complexity: 45%
         - Estimated searches: 14
         - Estimated tokens: 8,500
         - Estimated cost: $0.22
         - Budget: $0.50
         Ready to proceed? [Y/n]"
User: "Yes"
System: "Starting research..."
[Real-time cost tracking: $0.05, $0.10, $0.18, $0.22]
Research complete! Total cost: $0.21 (estimated $0.22)
```

---

## Success Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Estimate accuracy | ±30% of actual cost | Allow for variance in real execution |
| User confidence | 80%+ trust estimates | Surveys post-implementation |
| Budget adherence | 100% within estimated range | Hard stops enforce this |
| Adoption | 100% of research requests | Show estimate before execution |
| Confidence score | 75%+ average | Higher for simple queries |

---

## Implementation Timeline

| Task | Duration | Dependencies |
|------|----------|--------------|
| Create CostEstimator class | 1-2 hours | None |
| Add complexity analyzer | 0.5-1 hour | CostEstimator |
| Integration with CLI | 0.5-1 hour | CostEstimator |
| Testing & validation | 0.5-1 hour | Integration |
| Documentation | 0.5 hour | All |
| **Total** | **2-4 hours** | Sequential |

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Estimates inaccurate | MEDIUM | Test with 20+ queries, calibrate multipliers |
| User ignores warnings | LOW | Make warnings prominent, require confirmation |
| Estimation adds latency | LOW | Cache analysis results, pre-compute |
| Model assumptions invalid | LOW | Monitor actual vs estimated, adjust quarterly |

---

## Success Criteria

✅ Pre-research estimation available before execution
✅ Cost estimate accurate within ±30%
✅ Confidence score provided (0.0-1.0)
✅ User receives warning if estimate exceeds budget
✅ Estimation takes <1 second to complete
✅ Integration with all research depth levels
✅ CLI command working (`aris cost estimate`)
✅ Unit and integration tests passing
✅ Documentation complete

---

## Conclusion

Cost estimation closes the critical gap in ARIS's budget management system. With this feature:

- Users make informed decisions **before** committing resources
- Budget adherence becomes **proactive** rather than reactive
- $0.50 target confidence increases from 70% to 90%
- System transparency and user trust significantly improve

**Recommended**: Implement in next sprint (2-4 hour effort)

---

**Document**: Cost Estimation Gap Analysis
**Status**: READY FOR IMPLEMENTATION
**Created**: 2025-11-12
