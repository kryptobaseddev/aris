# MCP Integration Quick Reference

## Critical Patterns at a Glance

### 1. Basic Usage Pattern

```python
from mcp.manager import MCPManager

async with MCPManager.from_env() as mcp:
    # Search
    results = await mcp.search("query", max_results=10)

    # Extract (smart routing)
    content = await mcp.extract_content(["url1", "url2"])

    # Reason
    analysis = await mcp.reason("problem statement")
```

### 2. Error Handling Hierarchy

```
CircuitBreakerOpenError → Use fallback service
↓
BudgetExceededError → Stop execution, report costs
↓
TimeoutException → Retry with backoff (max 3x)
↓
HTTPError → Retry then fallback
↓
ConnectionError → Circuit breaker opens
```

### 3. Service Selection Decision Tree

```
Need to extract URL content?
├─ Contains JS frameworks/SPA? → Playwright
├─ Requires authentication? → Playwright
├─ Social media domain? → Playwright
└─ Simple HTML? → Tavily Extract
```

### 4. Timeout Values

```python
TIMEOUTS = {
    "tavily_search": 30.0,
    "tavily_extract": 30.0,
    "playwright": 45.0,
    "sequential": 60.0,
}
```

### 5. Circuit Breaker States

```
CLOSED (normal) → Track failures
↓ (5 failures)
OPEN (failing) → Reject immediately, start recovery timer
↓ (60s passed)
HALF_OPEN (testing) → Allow 1 request
↓ (success)
CLOSED (recovered)
```

### 6. Required Environment Variables

```bash
TAVILY_API_KEY=<key>
TAVILY_ENDPOINT=https://api.tavily.com
SEQUENTIAL_ENDPOINT=http://localhost:3001
PLAYWRIGHT_ENDPOINT=http://localhost:3004
MCP_MAX_BUDGET=10.0
```

### 7. Cost Tracking

```python
# Automatic per-service tracking
cost_summary = mcp.get_cost_summary()
# Returns:
# {
#   "total_cost_usd": 0.0234,
#   "services": {
#     "tavily": {"total_calls": 5, "total_cost_usd": 0.005},
#     "sequential": {"total_tokens": 1234, "total_cost_usd": 0.0123}
#   }
# }
```

### 8. Health Monitoring

```python
# Check service health
health = mcp.get_health_status()
# {
#   "tavily": {
#     "is_healthy": true,
#     "response_time_ms": 1234.5,
#     "consecutive_failures": 0
#   }
# }
```

### 9. Fallback Chain Examples

```python
# Extraction fallback
Tavily Extract fails → Playwright Extract

# Reasoning fallback
Sequential fails → Native reasoning

# Search fallback
Tavily Search fails → Native WebSearch
```

### 10. Parallel Execution

```python
# Automatically parallelized in extract_content
urls = ["url1", "url2", "url3"]
results = await mcp.extract_content(urls)  # Parallel by default
```

## Implementation Checklist

- [ ] Install dependencies: `httpx`, `asyncio`
- [ ] Set environment variables
- [ ] Implement base infrastructure (circuit breaker, retry, health)
- [ ] Create service adapters (Tavily, Sequential, Playwright)
- [ ] Build routing intelligence (complexity analyzer, fallback)
- [ ] Integrate MCPManager
- [ ] Add monitoring/logging
- [ ] Write unit tests for circuit breaker
- [ ] Write integration tests for each service
- [ ] Configure production timeouts
- [ ] Set budget limits
- [ ] Deploy and monitor

## Common Pitfalls to Avoid

❌ **Don't**: Forget to use `async with` for MCPManager
✅ **Do**: Use context manager for automatic cleanup

❌ **Don't**: Ignore circuit breaker errors
✅ **Do**: Implement fallback strategies

❌ **Don't**: Set timeouts too low
✅ **Do**: Profile real latencies and add buffer

❌ **Don't**: Skip cost tracking
✅ **Do**: Monitor budget continuously

❌ **Don't**: Disable health monitoring in production
✅ **Do**: Keep health checks running

## Performance Optimization Tips

1. **Connection Pooling**: Reuse HTTP connections
2. **Parallel Execution**: Batch independent operations
3. **Smart Caching**: Cache search results (1 hour)
4. **Retry Strategy**: Exponential backoff with jitter
5. **Timeout Tuning**: Profile and optimize per service

## Monitoring Best Practices

1. Track request latency per service
2. Monitor circuit breaker state changes
3. Alert on budget threshold (80%)
4. Log all fallback activations
5. Dashboard for health status

## Key Metrics to Track

- **Latency**: P50, P95, P99 per service
- **Error Rate**: % of failed requests
- **Circuit Breaker**: State changes per hour
- **Cost**: $ per research session
- **Throughput**: Requests per minute
- **Fallback Rate**: % of requests using fallback

## Quick Debug Commands

```python
# Check health
print(mcp.get_health_status())

# Check costs
print(mcp.get_cost_summary())

# Check circuit breakers
print(mcp.get_circuit_breaker_states())

# Test connection
await mcp.tavily.health_check()
```
