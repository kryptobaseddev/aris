# Tavily MCP Integration - Quick Reference

**For developers integrating with Tavily MCP**

---

## Quick Start

```python
from aris.core.config import ConfigManager
from aris.mcp import TavilyClient

# Get API key
config = ConfigManager.get_instance()
config.load()
api_key = config.get_api_key("tavily")

# Initialize client
async with TavilyClient(api_key=api_key) as client:
    # Use APIs
    results = await client.search("query")
```

---

## Search API

```python
results = await client.search(
    query="AI research",
    max_results=10,
    search_depth="advanced",  # or "basic"
    include_domains=["arxiv.org"],
    exclude_domains=["spam.com"],
    include_raw_content=False,
)

# Returns: list[dict] with title, url, content, score
```

---

## Extract API

```python
# Simple extraction
content = await client.extract(["https://example.com"])
# Returns: {"https://example.com": "extracted content"}

# Smart extraction (auto-routes to Tavily/Playwright)
results = await client.smart_extract([
    "https://wikipedia.org/article",  # → Tavily Extract
    "https://twitter.com/status",     # → Playwright
])

# Returns: {url: {content, method, complexity}}
```

---

## Crawl API

```python
pages = await client.crawl(
    url="https://example.com",
    depth=2,
    max_pages=10,
    include_content=True,
)

# Returns: list[dict] with url, title, content
```

---

## Map API

```python
sitemap = await client.map("https://example.com")

# Returns: dict with root, pages, links
```

---

## Circuit Breaker

```python
# Check status
status = client.get_circuit_status()
# {state: "closed|open|half_open", failure_count, ...}

# Circuit auto-manages:
# - CLOSED: Normal operation
# - OPEN: Fail-fast after 5 failures
# - HALF_OPEN: Testing recovery after 60s
```

---

## Cost Tracking

```python
# Get cost summary
summary = client.cost_tracker.get_summary()

# {
#   total_cost: 0.05,
#   operation_count: 5,
#   by_type: {
#     search: {count: 2, cost: 0.02},
#     extract: {count: 3, cost: 0.03}
#   }
# }
```

---

## Complexity Analysis

```python
from aris.mcp import ComplexityAnalyzer

analyzer = ComplexityAnalyzer()
analysis = analyzer.analyze_url("https://example.com")

# analysis.recommended_method:
#   - TAVILY_EXTRACT (simple static)
#   - PLAYWRIGHT (complex JavaScript)
#   - TAVILY_SEARCH (auth/paywall)

# analysis.score: 0-7 (higher = more complex)
# analysis.confidence: 0.0-1.0
# analysis.reasoning: "Why this method"
```

---

## Error Handling

```python
from aris.mcp import (
    TavilyAPIError,
    TavilyAuthenticationError,
    TavilyRateLimitError,
    CircuitBreakerOpen,
)

try:
    results = await client.search("query")
except TavilyAuthenticationError:
    # Invalid API key (401)
    pass
except TavilyRateLimitError:
    # Rate limit exceeded (429)
    pass
except CircuitBreakerOpen as e:
    # Circuit breaker blocking
    # e.next_attempt_in = seconds until retry
    pass
except TavilyAPIError:
    # General API error
    pass
```

---

## Search with Fallback

```python
results = await client.search_with_fallback(
    query="primary query",
    fallback_queries=["fallback 1", "fallback 2"],
    max_results=10,
)

# Automatically tries fallbacks if primary fails
```

---

## Configuration

```python
client = TavilyClient(
    api_key="tvly-...",
    timeout=30,                      # Request timeout
    max_retries=3,                   # Retry attempts
    circuit_breaker_threshold=5,     # Failures before OPEN
)
```

---

## Integration with ResearchHop

```python
from aris.models.research import ResearchHop

hop = ResearchHop(hop_number=1)

# Execute search
results = await client.search("query", max_results=10)

# Update hop metrics
hop.tavily_cost = client.cost_tracker.total_cost
hop.sources_found = len(results)

# Cost tracked automatically per operation
```

---

## Best Practices

1. **Use Context Manager**: `async with TavilyClient(...) as client`
2. **Check Circuit Status**: Monitor `get_circuit_status()` for OPEN state
3. **Track Costs**: Use `cost_tracker.get_summary()` regularly
4. **Smart Routing**: Use `smart_extract()` for unknown URLs
5. **Handle Errors**: Catch specific exceptions for better recovery

---

## Common Patterns

### Batch URL Processing
```python
urls = [...]  # List of URLs
analyses = analyzer.batch_analyze(urls)

# Separate by method
tavily_urls = [u for u, a in analyses.items()
               if a.recommended_method == ExtractionMethod.TAVILY_EXTRACT]
playwright_urls = [u for u, a in analyses.items()
                   if a.recommended_method == ExtractionMethod.PLAYWRIGHT]

# Extract appropriately
tavily_content = await client.extract(tavily_urls)
# Pass playwright_urls to Playwright MCP
```

### Cost Monitoring
```python
# Before operation
initial_cost = client.cost_tracker.total_cost

# Perform operations
await client.search("query1")
await client.search("query2")

# Check cost increase
cost_increase = client.cost_tracker.total_cost - initial_cost
print(f"Operations cost: ${cost_increase:.2f}")
```

### Resilient Search
```python
from aris.mcp import CircuitBreakerOpen

try:
    results = await client.search("query")
except CircuitBreakerOpen as e:
    print(f"Circuit open, retry in {e.next_attempt_in:.0f}s")
    # Wait or use cached results
except TavilyRateLimitError:
    print("Rate limited, using fallback")
    # Use alternative search
```

---

## API Costs

| Operation | Cost | Notes |
|-----------|------|-------|
| Search    | $0.01 | Per search query |
| Extract   | $0.01 | Per URL |
| Crawl     | $0.01 | Per page crawled |
| Map       | $0.01 | Per site map |

**Free Tier**: 1000 credits/month ($10 value)

---

## Complexity Indicators

| Indicator | Examples | Impact |
|-----------|----------|--------|
| JavaScript | `/app`, `/react`, `spa` | +1 to score |
| Auth Required | `/login`, `/dashboard` | +1 to score |
| Social Media | twitter.com, facebook.com | +1 to score |
| Dynamic | `?page=`, `infinite`, `scroll` | +1 to score |
| Paywall | nytimes.com, wsj.com | +1 to score |
| PDF | `.pdf` extension | +1 to score |
| Fragment | URL contains `#` | +1 to score |

**Score Thresholds**:
- 0-1: Tavily Extract (simple)
- 2: Tavily Extract (medium confidence)
- 3+: Playwright (complex)

---

## Files Reference

```
src/aris/mcp/
├── circuit_breaker.py      # Circuit breaker implementation
├── complexity_analyzer.py  # URL complexity analysis
└── tavily_client.py        # Main Tavily client

examples/
└── tavily_integration_example.py  # Complete examples

docs/
├── wave2-agent1-handoff.md        # Detailed handoff docs
└── TAVILY_QUICK_REFERENCE.md      # This file
```

---

## Support

**Documentation**: `/docs/wave2-agent1-handoff.md`
**Examples**: `/examples/tavily_integration_example.py`
**Tests**: `/tests/unit/test_tavily_client.py`

---

**Quick Reference v1.0 - Wave 2 Agent 1**
