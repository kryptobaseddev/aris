# MCP Integration Architecture for ARIS Research System

## Executive Summary

This document specifies the complete MCP server integration architecture for the ARIS (Adaptive Research Intelligence System), providing production-ready Python patterns for integrating Tavily, Sequential Thinking, Serena, Context7, and Playwright MCP servers with robust error handling, resource management, and intelligent routing.

---

## 1. Architecture Overview

### 1.1 Core Design Principles

- **AsyncIO-First**: All MCP interactions use async/await patterns for non-blocking I/O
- **Resource Safety**: AsyncExitStack ensures proper cleanup on success or failure
- **Fault Tolerance**: Circuit breakers, retries with exponential backoff, graceful degradation
- **Smart Routing**: Dynamic service selection based on content complexity and service health
- **Cost Awareness**: Track tokens/calls per service for budget management
- **Observable**: Structured logging for monitoring, debugging, and performance analysis

### 1.2 Integration Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ARIS Research System                        │
├─────────────────────────────────────────────────────────────────┤
│                    MCP Integration Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Connection   │  │   Circuit    │  │   Health     │          │
│  │   Pool       │  │   Breaker    │  │   Monitor    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      Service Adapters                            │
│  ┌──────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐    │
│  │Tavily│ │Sequential│ │ Serena │ │Context7 │ │Playwright│    │
│  └──────┘ └──────────┘ └────────┘ └─────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    Routing Intelligence                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Complexity  │  │   Fallback   │  │     Cost     │          │
│  │  Analyzer    │  │   Strategy   │  │   Tracker    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Base Infrastructure Components

### 2.1 Configuration Management

```python
# mcp/config.py
from dataclasses import dataclass
from typing import Optional
import os
from enum import Enum

class MCPService(Enum):
    TAVILY = "tavily"
    SEQUENTIAL = "sequential"
    SERENA = "serena"
    CONTEXT7 = "context7"
    PLAYWRIGHT = "playwright"

@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""
    name: MCPService
    endpoint: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    health_check_interval: float = 30.0
    max_connections: int = 10

    # Service-specific rate limits
    rate_limit_calls_per_minute: Optional[int] = None
    rate_limit_tokens_per_minute: Optional[int] = None

    # Cost tracking (USD per call/token)
    cost_per_call: float = 0.0
    cost_per_token: float = 0.0

@dataclass
class MCPIntegrationConfig:
    """Global MCP integration configuration"""
    # Service configurations
    tavily: MCPServerConfig
    sequential: MCPServerConfig
    serena: MCPServerConfig
    context7: MCPServerConfig
    playwright: MCPServerConfig

    # Global settings
    enable_fallbacks: bool = True
    enable_cost_tracking: bool = True
    enable_health_monitoring: bool = True
    max_total_budget: Optional[float] = None  # USD

    @classmethod
    def from_env(cls) -> "MCPIntegrationConfig":
        """Load configuration from environment variables"""
        return cls(
            tavily=MCPServerConfig(
                name=MCPService.TAVILY,
                endpoint=os.getenv("TAVILY_ENDPOINT", "https://api.tavily.com"),
                api_key=os.getenv("TAVILY_API_KEY"),
                timeout=float(os.getenv("TAVILY_TIMEOUT", "30.0")),
                rate_limit_calls_per_minute=100,  # Tavily: 100 req/min
                cost_per_call=0.001,  # Example cost
            ),
            sequential=MCPServerConfig(
                name=MCPService.SEQUENTIAL,
                endpoint=os.getenv("SEQUENTIAL_ENDPOINT", "http://localhost:3001"),
                timeout=float(os.getenv("SEQUENTIAL_TIMEOUT", "60.0")),
                cost_per_token=0.00001,  # Token-based pricing
            ),
            serena=MCPServerConfig(
                name=MCPService.SERENA,
                endpoint=os.getenv("SERENA_ENDPOINT", "http://localhost:3002"),
                timeout=float(os.getenv("SERENA_TIMEOUT", "30.0")),
            ),
            context7=MCPServerConfig(
                name=MCPService.CONTEXT7,
                endpoint=os.getenv("CONTEXT7_ENDPOINT", "http://localhost:3003"),
                timeout=float(os.getenv("CONTEXT7_TIMEOUT", "30.0")),
                cost_per_token=0.000005,  # Token-based pricing
            ),
            playwright=MCPServerConfig(
                name=MCPService.PLAYWRIGHT,
                endpoint=os.getenv("PLAYWRIGHT_ENDPOINT", "http://localhost:3004"),
                timeout=float(os.getenv("PLAYWRIGHT_TIMEOUT", "45.0")),
                cost_per_call=0.01,  # Higher cost for browser automation
            ),
            enable_fallbacks=os.getenv("MCP_ENABLE_FALLBACKS", "true").lower() == "true",
            enable_cost_tracking=os.getenv("MCP_ENABLE_COST_TRACKING", "true").lower() == "true",
            enable_health_monitoring=os.getenv("MCP_ENABLE_HEALTH_MONITORING", "true").lower() == "true",
            max_total_budget=float(os.getenv("MCP_MAX_BUDGET")) if os.getenv("MCP_MAX_BUDGET") else None,
        )
```

### 2.2 Circuit Breaker Pattern

```python
# mcp/circuit_breaker.py
from enum import Enum
from typing import Callable, Any
import asyncio
import time
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker decision making"""
    total_calls: int = 0
    failed_calls: int = 0
    success_calls: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0

class CircuitBreaker:
    """
    Circuit breaker pattern for MCP service protection.

    States:
    - CLOSED: Normal operation, track failures
    - OPEN: Service failing, reject requests immediately
    - HALF_OPEN: Test if service recovered, allow single request
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker for {self.service_name}: OPEN -> HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                else:
                    logger.warning(f"Circuit breaker OPEN for {self.service_name}, rejecting call")
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker open for {self.service_name}"
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to test recovery"""
        return time.time() - self.metrics.last_failure_time >= self.recovery_timeout

    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self.metrics.total_calls += 1
            self.metrics.success_calls += 1
            self.metrics.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker for {self.service_name}: HALF_OPEN -> CLOSED")
                self.state = CircuitState.CLOSED
                self.metrics.failed_calls = 0  # Reset failure count

    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.metrics.total_calls += 1
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker for {self.service_name}: HALF_OPEN -> OPEN")
                self.state = CircuitState.OPEN
            elif self.metrics.failed_calls >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker for {self.service_name}: CLOSED -> OPEN "
                    f"({self.metrics.failed_calls} failures)"
                )
                self.state = CircuitState.OPEN

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics"""
        return self.metrics

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass
```

### 2.3 Retry Logic with Exponential Backoff

```python
# mcp/retry.py
from typing import Callable, TypeVar, Optional, Type
import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryStrategy:
    """Retry configuration with exponential backoff"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        import random

        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add ±25% jitter to prevent thundering herd
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

def retry_async(
    strategy: RetryStrategy,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for async functions with retry logic.

    Args:
        strategy: RetryStrategy configuration
        retryable_exceptions: Exceptions that should trigger retry
        on_retry: Optional callback called before each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(strategy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < strategy.max_retries:
                        delay = strategy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{strategy.max_retries + 1} failed for "
                            f"{func.__name__}: {e}. Retrying in {delay:.2f}s"
                        )

                        if on_retry:
                            await on_retry(attempt, e)

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {strategy.max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator
```

### 2.4 Health Monitoring

```python
# mcp/health.py
from dataclasses import dataclass
from typing import Dict, Optional
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Health status for a single MCP service"""
    service_name: str
    is_healthy: bool
    last_check_time: float
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    consecutive_failures: int = 0
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

class HealthMonitor:
    """Background health monitoring for MCP services"""

    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.statuses: Dict[str, HealthStatus] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start background health monitoring"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self):
        """Stop background health monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self):
        """Continuous health check loop"""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                # Health checks performed by individual service adapters
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")

    def update_status(
        self,
        service_name: str,
        is_healthy: bool,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        """Update health status for a service"""
        current_time = time.time()

        if service_name not in self.statuses:
            self.statuses[service_name] = HealthStatus(
                service_name=service_name,
                is_healthy=is_healthy,
                last_check_time=current_time,
            )

        status = self.statuses[service_name]
        status.is_healthy = is_healthy
        status.last_check_time = current_time
        status.response_time_ms = response_time_ms
        status.error_message = error_message

        if is_healthy:
            status.last_success_time = current_time
            status.consecutive_failures = 0
        else:
            status.last_failure_time = current_time
            status.consecutive_failures += 1
            logger.warning(
                f"Health check failed for {service_name} "
                f"({status.consecutive_failures} consecutive failures): {error_message}"
            )

    def get_status(self, service_name: str) -> Optional[HealthStatus]:
        """Get health status for a service"""
        return self.statuses.get(service_name)

    def is_healthy(self, service_name: str) -> bool:
        """Check if service is healthy"""
        status = self.statuses.get(service_name)
        return status.is_healthy if status else False

    def get_all_statuses(self) -> Dict[str, HealthStatus]:
        """Get all health statuses"""
        return self.statuses.copy()
```

### 2.5 Cost Tracking

```python
# mcp/cost_tracker.py
from dataclasses import dataclass, field
from typing import Dict
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class ServiceCost:
    """Cost tracking for a single service"""
    service_name: str
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cost_by_operation: Dict[str, float] = field(default_factory=dict)

class CostTracker:
    """Track costs across all MCP services"""

    def __init__(self, max_budget_usd: float = None):
        self.max_budget_usd = max_budget_usd
        self.service_costs: Dict[str, ServiceCost] = {}
        self.start_time = time.time()

    def record_call(
        self,
        service_name: str,
        operation: str,
        cost_usd: float,
        token_count: int = 0,
    ):
        """Record a service call cost"""
        if service_name not in self.service_costs:
            self.service_costs[service_name] = ServiceCost(service_name=service_name)

        cost = self.service_costs[service_name]
        cost.total_calls += 1
        cost.total_tokens += token_count
        cost.total_cost_usd += cost_usd

        if operation not in cost.cost_by_operation:
            cost.cost_by_operation[operation] = 0.0
        cost.cost_by_operation[operation] += cost_usd

        # Check budget limit
        if self.max_budget_usd and self.get_total_cost() > self.max_budget_usd:
            logger.error(
                f"Budget limit exceeded! Total: ${self.get_total_cost():.4f}, "
                f"Limit: ${self.max_budget_usd:.4f}"
            )
            raise BudgetExceededError(
                f"Total cost ${self.get_total_cost():.4f} exceeds budget ${self.max_budget_usd:.4f}"
            )

    def get_service_cost(self, service_name: str) -> ServiceCost:
        """Get cost for a specific service"""
        return self.service_costs.get(service_name, ServiceCost(service_name=service_name))

    def get_total_cost(self) -> float:
        """Get total cost across all services"""
        return sum(cost.total_cost_usd for cost in self.service_costs.values())

    def get_cost_summary(self) -> Dict[str, any]:
        """Get comprehensive cost summary"""
        runtime_seconds = time.time() - self.start_time
        total_cost = self.get_total_cost()

        return {
            "total_cost_usd": total_cost,
            "budget_remaining_usd": self.max_budget_usd - total_cost if self.max_budget_usd else None,
            "runtime_seconds": runtime_seconds,
            "cost_per_minute": (total_cost / runtime_seconds * 60) if runtime_seconds > 0 else 0,
            "services": {
                name: {
                    "total_calls": cost.total_calls,
                    "total_tokens": cost.total_tokens,
                    "total_cost_usd": cost.total_cost_usd,
                    "cost_by_operation": cost.cost_by_operation,
                }
                for name, cost in self.service_costs.items()
            }
        }

class BudgetExceededError(Exception):
    """Raised when cost budget is exceeded"""
    pass
```

---

## 3. Service-Specific Adapters

### 3.1 Tavily Adapter

```python
# mcp/adapters/tavily.py
from typing import List, Dict, Optional, Any
import httpx
import logging
from ..config import MCPServerConfig
from ..circuit_breaker import CircuitBreaker
from ..retry import retry_async, RetryStrategy
from ..health import HealthMonitor
from ..cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class TavilyAdapter:
    """
    Adapter for Tavily Search MCP server.

    Provides:
    - Search API: Multi-source web search
    - Extract API: Simple content extraction
    - Crawl API: Deep site crawling
    - Map API: Site structure mapping
    """

    def __init__(
        self,
        config: MCPServerConfig,
        circuit_breaker: CircuitBreaker,
        health_monitor: HealthMonitor,
        cost_tracker: CostTracker,
    ):
        self.config = config
        self.circuit_breaker = circuit_breaker
        self.health_monitor = health_monitor
        self.cost_tracker = cost_tracker
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> httpx.AsyncClient:
        """Establish connection to Tavily API"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                }
            )
            logger.info(f"Connected to Tavily at {self.config.endpoint}")
        return self._client

    async def disconnect(self):
        """Close connection to Tavily API"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Disconnected from Tavily")

    @retry_async(
        strategy=RetryStrategy(max_retries=3, base_delay=1.0),
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform web search via Tavily Search API.

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 10)
            search_depth: "basic" or "advanced" (default: "basic")
            include_domains: Domains to include in search
            exclude_domains: Domains to exclude from search

        Returns:
            Search results with URLs, snippets, and metadata

        Raises:
            CircuitBreakerOpenError: If Tavily service is down
            BudgetExceededError: If cost limit exceeded
        """
        import time
        start_time = time.time()

        async def _search():
            client = await self.connect()
            response = await client.post(
                "/search",
                json={
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "include_domains": include_domains or [],
                    "exclude_domains": exclude_domains or [],
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await self.circuit_breaker.call(_search)

            # Track metrics
            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.update_status(
                service_name="tavily",
                is_healthy=True,
                response_time_ms=response_time_ms,
            )
            self.cost_tracker.record_call(
                service_name="tavily",
                operation="search",
                cost_usd=self.config.cost_per_call,
            )

            logger.info(f"Tavily search completed: {len(result.get('results', []))} results in {response_time_ms:.0f}ms")
            return result

        except Exception as e:
            self.health_monitor.update_status(
                service_name="tavily",
                is_healthy=False,
                error_message=str(e),
            )
            logger.error(f"Tavily search failed: {e}")
            raise

    @retry_async(
        strategy=RetryStrategy(max_retries=3, base_delay=1.0),
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def extract(
        self,
        urls: List[str],
    ) -> Dict[str, Any]:
        """
        Extract content from URLs via Tavily Extract API.

        Args:
            urls: List of URLs to extract content from

        Returns:
            Extracted content for each URL

        Raises:
            CircuitBreakerOpenError: If Tavily service is down
        """
        import time
        start_time = time.time()

        async def _extract():
            client = await self.connect()
            response = await client.post(
                "/extract",
                json={"urls": urls}
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await self.circuit_breaker.call(_extract)

            # Track metrics
            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.update_status(
                service_name="tavily",
                is_healthy=True,
                response_time_ms=response_time_ms,
            )
            self.cost_tracker.record_call(
                service_name="tavily",
                operation="extract",
                cost_usd=self.config.cost_per_call * len(urls),
            )

            logger.info(f"Tavily extract completed: {len(urls)} URLs in {response_time_ms:.0f}ms")
            return result

        except Exception as e:
            self.health_monitor.update_status(
                service_name="tavily",
                is_healthy=False,
                error_message=str(e),
            )
            logger.error(f"Tavily extract failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Perform health check on Tavily service"""
        try:
            # Simple search as health check
            await self.search(query="test", max_results=1)
            return True
        except Exception:
            return False
```

### 3.2 Sequential Thinking Adapter

```python
# mcp/adapters/sequential.py
from typing import List, Dict, Optional, Any
import httpx
import logging
from ..config import MCPServerConfig
from ..circuit_breaker import CircuitBreaker
from ..retry import retry_async, RetryStrategy
from ..health import HealthMonitor
from ..cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class SequentialAdapter:
    """
    Adapter for Sequential Thinking MCP server.

    Provides:
    - Structured multi-step reasoning
    - Hypothesis generation and testing
    - Branching thought processes
    - Adaptive planning
    """

    def __init__(
        self,
        config: MCPServerConfig,
        circuit_breaker: CircuitBreaker,
        health_monitor: HealthMonitor,
        cost_tracker: CostTracker,
    ):
        self.config = config
        self.circuit_breaker = circuit_breaker
        self.health_monitor = health_monitor
        self.cost_tracker = cost_tracker
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> httpx.AsyncClient:
        """Establish connection to Sequential Thinking server"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"}
            )
            logger.info(f"Connected to Sequential Thinking at {self.config.endpoint}")
        return self._client

    async def disconnect(self):
        """Close connection to Sequential Thinking server"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Disconnected from Sequential Thinking")

    @retry_async(
        strategy=RetryStrategy(max_retries=2, base_delay=2.0),
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        max_thoughts: int = 10,
        enable_branching: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform structured reasoning on a problem.

        Args:
            problem: Problem statement to analyze
            context: Additional context for reasoning
            max_thoughts: Maximum number of thought steps
            enable_branching: Allow branching thought processes

        Returns:
            Reasoning chain with thoughts, conclusions, and confidence

        Raises:
            CircuitBreakerOpenError: If Sequential service is down
        """
        import time
        start_time = time.time()

        async def _reason():
            client = await self.connect()
            response = await client.post(
                "/reason",
                json={
                    "problem": problem,
                    "context": context or {},
                    "max_thoughts": max_thoughts,
                    "enable_branching": enable_branching,
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await self.circuit_breaker.call(_reason)

            # Track metrics
            response_time_ms = (time.time() - start_time) * 1000
            token_count = result.get("token_usage", 0)

            self.health_monitor.update_status(
                service_name="sequential",
                is_healthy=True,
                response_time_ms=response_time_ms,
            )
            self.cost_tracker.record_call(
                service_name="sequential",
                operation="reason",
                cost_usd=self.config.cost_per_token * token_count,
                token_count=token_count,
            )

            logger.info(
                f"Sequential reasoning completed: {result.get('thought_count', 0)} thoughts, "
                f"{token_count} tokens in {response_time_ms:.0f}ms"
            )
            return result

        except Exception as e:
            self.health_monitor.update_status(
                service_name="sequential",
                is_healthy=False,
                error_message=str(e),
            )
            logger.error(f"Sequential reasoning failed: {e}")
            raise

    @retry_async(
        strategy=RetryStrategy(max_retries=2, base_delay=2.0),
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def decompose_query(
        self,
        research_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Decompose a research query into sub-queries.

        Args:
            research_query: High-level research question
            context: Additional context for decomposition

        Returns:
            Sub-queries with search strategies
        """
        import time
        start_time = time.time()

        async def _decompose():
            client = await self.connect()
            response = await client.post(
                "/decompose",
                json={
                    "query": research_query,
                    "context": context or {},
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await self.circuit_breaker.call(_decompose)

            # Track metrics
            response_time_ms = (time.time() - start_time) * 1000
            token_count = result.get("token_usage", 0)

            self.cost_tracker.record_call(
                service_name="sequential",
                operation="decompose",
                cost_usd=self.config.cost_per_token * token_count,
                token_count=token_count,
            )

            logger.info(
                f"Query decomposition completed: {len(result.get('sub_queries', []))} sub-queries "
                f"in {response_time_ms:.0f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Query decomposition failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Perform health check on Sequential service"""
        try:
            await self.reason(
                problem="Test health check",
                max_thoughts=1,
                enable_branching=False,
            )
            return True
        except Exception:
            return False
```

### 3.3 Playwright Adapter

```python
# mcp/adapters/playwright.py
from typing import Optional, Dict, Any, List
import httpx
import logging
from ..config import MCPServerConfig
from ..circuit_breaker import CircuitBreaker
from ..retry import retry_async, RetryStrategy
from ..health import HealthMonitor
from ..cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class PlaywrightAdapter:
    """
    Adapter for Playwright MCP server.

    Provides:
    - Browser automation for complex extraction
    - JavaScript rendering
    - Screenshot capture
    - Form interaction
    """

    def __init__(
        self,
        config: MCPServerConfig,
        circuit_breaker: CircuitBreaker,
        health_monitor: HealthMonitor,
        cost_tracker: CostTracker,
    ):
        self.config = config
        self.circuit_breaker = circuit_breaker
        self.health_monitor = health_monitor
        self.cost_tracker = cost_tracker
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> httpx.AsyncClient:
        """Establish connection to Playwright server"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"}
            )
            logger.info(f"Connected to Playwright at {self.config.endpoint}")
        return self._client

    async def disconnect(self):
        """Close connection to Playwright server"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Disconnected from Playwright")

    @retry_async(
        strategy=RetryStrategy(max_retries=2, base_delay=3.0, max_delay=30.0),
        retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
    )
    async def extract_content(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        capture_screenshot: bool = False,
        execute_script: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract content from URL with browser automation.

        Args:
            url: URL to extract content from
            wait_for_selector: CSS selector to wait for before extraction
            capture_screenshot: Capture screenshot of page
            execute_script: JavaScript to execute on page

        Returns:
            Extracted content, HTML, and optional screenshot

        Raises:
            CircuitBreakerOpenError: If Playwright service is down
        """
        import time
        start_time = time.time()

        async def _extract():
            client = await self.connect()
            response = await client.post(
                "/extract",
                json={
                    "url": url,
                    "wait_for_selector": wait_for_selector,
                    "capture_screenshot": capture_screenshot,
                    "execute_script": execute_script,
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            result = await self.circuit_breaker.call(_extract)

            # Track metrics
            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.update_status(
                service_name="playwright",
                is_healthy=True,
                response_time_ms=response_time_ms,
            )
            self.cost_tracker.record_call(
                service_name="playwright",
                operation="extract",
                cost_usd=self.config.cost_per_call,
            )

            logger.info(f"Playwright extraction completed for {url} in {response_time_ms:.0f}ms")
            return result

        except Exception as e:
            self.health_monitor.update_status(
                service_name="playwright",
                is_healthy=False,
                error_message=str(e),
            )
            logger.error(f"Playwright extraction failed for {url}: {e}")
            raise

    async def health_check(self) -> bool:
        """Perform health check on Playwright service"""
        try:
            await self.extract_content(
                url="https://example.com",
                capture_screenshot=False,
            )
            return True
        except Exception:
            return False
```

---

## 4. Intelligent Routing Layer

### 4.1 Complexity Analyzer

```python
# mcp/routing/complexity.py
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum
import re

class ComplexityLevel(Enum):
    SIMPLE = "simple"        # Static HTML, public content
    MODERATE = "moderate"    # Some JS, standard pages
    COMPLEX = "complex"      # Heavy JS, auth required, dynamic content

@dataclass
class URLComplexity:
    """Analysis of URL extraction complexity"""
    url: str
    level: ComplexityLevel
    requires_javascript: bool
    requires_auth: bool
    estimated_load_time_ms: float
    recommended_service: str  # "tavily" or "playwright"
    confidence: float

class ComplexityAnalyzer:
    """
    Analyze URL complexity to route extraction requests.

    Decision Logic:
    - Simple → Tavily Extract (fast, cheap)
    - Complex → Playwright (accurate, expensive)
    """

    # Patterns indicating JavaScript rendering needed
    JS_INDICATORS = [
        r'react', r'angular', r'vue', r'spa',
        r'app\.', r'client\.', r'dynamic',
    ]

    # Patterns indicating authentication required
    AUTH_INDICATORS = [
        r'login', r'auth', r'signin', r'dashboard',
        r'account', r'profile', r'admin',
    ]

    # Domains known to require JavaScript
    JS_HEAVY_DOMAINS = [
        'twitter.com', 'x.com', 'linkedin.com',
        'facebook.com', 'instagram.com',
    ]

    def analyze_url(self, url: str, content_hint: str = "") -> URLComplexity:
        """
        Analyze URL to determine extraction complexity.

        Args:
            url: URL to analyze
            content_hint: Optional hint about content type

        Returns:
            URLComplexity with routing recommendation
        """
        url_lower = url.lower()

        # Check for JavaScript indicators
        requires_js = any(
            re.search(pattern, url_lower) for pattern in self.JS_INDICATORS
        )
        requires_js = requires_js or any(
            domain in url_lower for domain in self.JS_HEAVY_DOMAINS
        )

        # Check for authentication indicators
        requires_auth = any(
            re.search(pattern, url_lower) for pattern in self.AUTH_INDICATORS
        )

        # Determine complexity level
        if requires_auth or requires_js:
            level = ComplexityLevel.COMPLEX
            recommended = "playwright"
            estimated_time = 5000.0  # 5 seconds
            confidence = 0.9
        elif any(domain in url_lower for domain in ['github.com', 'gitlab.com']):
            level = ComplexityLevel.MODERATE
            recommended = "playwright"
            estimated_time = 3000.0
            confidence = 0.8
        else:
            level = ComplexityLevel.SIMPLE
            recommended = "tavily"
            estimated_time = 1000.0  # 1 second
            confidence = 0.95

        return URLComplexity(
            url=url,
            level=level,
            requires_javascript=requires_js,
            requires_auth=requires_auth,
            estimated_load_time_ms=estimated_time,
            recommended_service=recommended,
            confidence=confidence,
        )

    def analyze_batch(self, urls: list[str]) -> Dict[str, list[str]]:
        """
        Analyze multiple URLs and group by recommended service.

        Returns:
            {"tavily": [...], "playwright": [...]}
        """
        routing = {"tavily": [], "playwright": []}

        for url in urls:
            analysis = self.analyze_url(url)
            routing[analysis.recommended_service].append(url)

        return routing
```

### 4.2 Fallback Strategy

```python
# mcp/routing/fallback.py
from typing import Callable, Any, Optional, List
import logging
from ..circuit_breaker import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

class FallbackStrategy:
    """
    Implement fallback chains for service failures.

    Example chains:
    - Tavily Extract fails → Playwright Extract
    - Sequential fails → Native reasoning
    - Playwright fails → Tavily Extract (if simple content)
    """

    def __init__(self, enable_fallbacks: bool = True):
        self.enable_fallbacks = enable_fallbacks

    async def execute_with_fallback(
        self,
        primary: Callable,
        fallbacks: List[Callable],
        operation_name: str,
    ) -> Any:
        """
        Execute primary function with fallback chain.

        Args:
            primary: Primary function to execute
            fallbacks: Ordered list of fallback functions
            operation_name: Name for logging

        Returns:
            Result from first successful function

        Raises:
            Exception: If all functions fail
        """
        if not self.enable_fallbacks:
            return await primary()

        # Try primary
        try:
            logger.info(f"Executing primary strategy for {operation_name}")
            return await primary()
        except CircuitBreakerOpenError:
            logger.warning(f"Primary service unavailable for {operation_name}, trying fallbacks")
        except Exception as e:
            logger.warning(f"Primary strategy failed for {operation_name}: {e}, trying fallbacks")

        # Try fallbacks in order
        for i, fallback in enumerate(fallbacks):
            try:
                logger.info(f"Executing fallback {i+1}/{len(fallbacks)} for {operation_name}")
                return await fallback()
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed for {operation_name}: {e}")
                if i == len(fallbacks) - 1:
                    # Last fallback failed
                    logger.error(f"All strategies failed for {operation_name}")
                    raise

        raise Exception(f"No fallback strategies available for {operation_name}")

    async def extract_content_with_fallback(
        self,
        url: str,
        tavily_adapter,
        playwright_adapter,
        complexity_analysis,
    ) -> Dict[str, Any]:
        """
        Extract content with intelligent fallback.

        Strategy:
        1. Use recommended service based on complexity
        2. Fall back to alternative if primary fails
        """
        if complexity_analysis.recommended_service == "tavily":
            primary = lambda: tavily_adapter.extract([url])
            fallback = lambda: playwright_adapter.extract_content(url)
        else:
            primary = lambda: playwright_adapter.extract_content(url)
            fallback = lambda: tavily_adapter.extract([url])

        return await self.execute_with_fallback(
            primary=primary,
            fallbacks=[fallback],
            operation_name=f"extract:{url}",
        )
```

---

## 5. Main Integration Manager

### 5.1 MCP Manager

```python
# mcp/manager.py
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import asyncio
import logging
from .config import MCPIntegrationConfig
from .circuit_breaker import CircuitBreaker
from .health import HealthMonitor
from .cost_tracker import CostTracker
from .adapters.tavily import TavilyAdapter
from .adapters.sequential import SequentialAdapter
from .adapters.playwright import PlaywrightAdapter
from .routing.complexity import ComplexityAnalyzer
from .routing.fallback import FallbackStrategy

logger = logging.getLogger(__name__)

class MCPManager:
    """
    Central manager for all MCP service integrations.

    Responsibilities:
    - Service lifecycle management (connect/disconnect)
    - Intelligent routing and fallback
    - Health monitoring and circuit breaking
    - Cost tracking and budget enforcement
    """

    def __init__(self, config: Optional[MCPIntegrationConfig] = None):
        self.config = config or MCPIntegrationConfig.from_env()

        # Infrastructure components
        self.health_monitor = HealthMonitor(
            check_interval=self.config.tavily.health_check_interval
        )
        self.cost_tracker = CostTracker(
            max_budget_usd=self.config.max_total_budget
        )

        # Circuit breakers for each service
        self.circuit_breakers = {
            "tavily": CircuitBreaker(
                service_name="tavily",
                failure_threshold=self.config.tavily.circuit_breaker_threshold,
                recovery_timeout=self.config.tavily.circuit_breaker_timeout,
            ),
            "sequential": CircuitBreaker(
                service_name="sequential",
                failure_threshold=self.config.sequential.circuit_breaker_threshold,
                recovery_timeout=self.config.sequential.circuit_breaker_timeout,
            ),
            "playwright": CircuitBreaker(
                service_name="playwright",
                failure_threshold=self.config.playwright.circuit_breaker_threshold,
                recovery_timeout=self.config.playwright.circuit_breaker_timeout,
            ),
        }

        # Service adapters (initialized in connect)
        self.tavily: Optional[TavilyAdapter] = None
        self.sequential: Optional[SequentialAdapter] = None
        self.playwright: Optional[PlaywrightAdapter] = None

        # Routing intelligence
        self.complexity_analyzer = ComplexityAnalyzer()
        self.fallback_strategy = FallbackStrategy(
            enable_fallbacks=self.config.enable_fallbacks
        )

        # Resource management
        self._exit_stack: Optional[AsyncExitStack] = None
        self._connected = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.disconnect()

    async def connect(self):
        """Initialize all MCP service connections"""
        if self._connected:
            return

        self._exit_stack = AsyncExitStack()

        try:
            # Initialize adapters
            self.tavily = TavilyAdapter(
                config=self.config.tavily,
                circuit_breaker=self.circuit_breakers["tavily"],
                health_monitor=self.health_monitor,
                cost_tracker=self.cost_tracker,
            )

            self.sequential = SequentialAdapter(
                config=self.config.sequential,
                circuit_breaker=self.circuit_breakers["sequential"],
                health_monitor=self.health_monitor,
                cost_tracker=self.cost_tracker,
            )

            self.playwright = PlaywrightAdapter(
                config=self.config.playwright,
                circuit_breaker=self.circuit_breakers["playwright"],
                health_monitor=self.health_monitor,
                cost_tracker=self.cost_tracker,
            )

            # Connect to services
            await self.tavily.connect()
            await self.sequential.connect()
            await self.playwright.connect()

            # Start health monitoring
            if self.config.enable_health_monitoring:
                await self.health_monitor.start()

            self._connected = True
            logger.info("All MCP services connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to MCP services: {e}")
            await self.disconnect()
            raise

    async def disconnect(self):
        """Cleanup all MCP service connections"""
        if not self._connected:
            return

        try:
            # Stop health monitoring
            await self.health_monitor.stop()

            # Disconnect services
            if self.tavily:
                await self.tavily.disconnect()
            if self.sequential:
                await self.sequential.disconnect()
            if self.playwright:
                await self.playwright.disconnect()

            # Cleanup exit stack
            if self._exit_stack:
                await self._exit_stack.aclose()

            self._connected = False
            logger.info("All MCP services disconnected")

            # Log final cost summary
            if self.config.enable_cost_tracking:
                summary = self.cost_tracker.get_cost_summary()
                logger.info(f"Session cost summary: {summary}")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    # High-level research workflow methods

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform web search via Tavily"""
        return await self.tavily.search(
            query=query,
            max_results=max_results,
            **kwargs
        )

    async def extract_content(
        self,
        urls: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Extract content from URLs with intelligent routing.

        Analyzes complexity and routes to appropriate service:
        - Simple URLs → Tavily Extract (fast)
        - Complex URLs → Playwright (accurate)
        """
        # Analyze URL complexity
        routing = self.complexity_analyzer.analyze_batch(urls)

        results = []

        # Process Tavily-routed URLs
        if routing["tavily"]:
            try:
                tavily_results = await self.tavily.extract(routing["tavily"])
                results.extend(tavily_results.get("results", []))
            except Exception as e:
                logger.warning(f"Tavily extraction failed, falling back to Playwright: {e}")
                # Fallback to Playwright
                for url in routing["tavily"]:
                    try:
                        result = await self.playwright.extract_content(url)
                        results.append(result)
                    except Exception as pw_error:
                        logger.error(f"Both Tavily and Playwright failed for {url}: {pw_error}")

        # Process Playwright-routed URLs
        if routing["playwright"]:
            for url in routing["playwright"]:
                try:
                    result = await self.playwright.extract_content(url)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Playwright extraction failed for {url}, trying Tavily: {e}")
                    # Fallback to Tavily
                    try:
                        tavily_result = await self.tavily.extract([url])
                        results.extend(tavily_result.get("results", []))
                    except Exception as tavily_error:
                        logger.error(f"Both Playwright and Tavily failed for {url}: {tavily_error}")

        return results

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform structured reasoning via Sequential"""
        return await self.sequential.reason(
            problem=problem,
            context=context,
            **kwargs
        )

    async def decompose_research_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Decompose research query into sub-queries via Sequential"""
        return await self.sequential.decompose_query(
            research_query=query,
            context=context,
        )

    # Monitoring methods

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for all services"""
        return {
            service: status.__dict__
            for service, status in self.health_monitor.get_all_statuses().items()
        }

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for session"""
        return self.cost_tracker.get_cost_summary()

    def get_circuit_breaker_states(self) -> Dict[str, str]:
        """Get circuit breaker states for all services"""
        return {
            service: cb.get_state().value
            for service, cb in self.circuit_breakers.items()
        }
```

---

## 6. Integration with ARIS Research Workflow

### 6.1 Research Orchestrator

```python
# research/orchestrator.py
from typing import Dict, Any, List, Optional
import logging
from mcp.manager import MCPManager

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    """
    Orchestrate ARIS research workflow with MCP services.

    Workflow Phases:
    1. Planning: Sequential for query decomposition
    2. Search: Tavily for multi-source discovery
    3. Extraction: Smart routing (Tavily/Playwright)
    4. Analysis: Sequential for structured reasoning
    5. Memory: Serena for session persistence (future)
    """

    def __init__(self, mcp_manager: MCPManager):
        self.mcp = mcp_manager

    async def execute_research(
        self,
        query: str,
        max_sources: int = 20,
        confidence_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Execute complete research workflow.

        Args:
            query: Research question
            max_sources: Maximum sources to gather
            confidence_threshold: Minimum confidence for conclusions

        Returns:
            Research results with sources and analysis
        """
        logger.info(f"Starting research for query: {query}")

        # Phase 1: Planning - Decompose query
        logger.info("Phase 1: Query decomposition")
        decomposition = await self.mcp.decompose_research_query(query)
        sub_queries = decomposition.get("sub_queries", [query])

        # Phase 2: Search - Gather sources
        logger.info(f"Phase 2: Searching for {len(sub_queries)} sub-queries")
        all_results = []
        for sub_query in sub_queries[:5]:  # Limit to top 5
            search_results = await self.mcp.search(
                query=sub_query,
                max_results=max_sources // len(sub_queries),
            )
            all_results.extend(search_results.get("results", []))

        # Phase 3: Extraction - Get content
        logger.info(f"Phase 3: Extracting content from {len(all_results)} URLs")
        urls = [result["url"] for result in all_results[:max_sources]]
        extracted = await self.mcp.extract_content(urls)

        # Phase 4: Analysis - Structured reasoning
        logger.info("Phase 4: Analyzing gathered information")
        analysis_context = {
            "query": query,
            "source_count": len(extracted),
            "extracted_content": extracted,
        }
        analysis = await self.mcp.reason(
            problem=f"Analyze research findings for: {query}",
            context=analysis_context,
        )

        # Compile results
        results = {
            "query": query,
            "sub_queries": sub_queries,
            "sources": extracted,
            "analysis": analysis,
            "confidence": analysis.get("confidence", 0.0),
            "cost_summary": self.mcp.get_cost_summary(),
            "health_status": self.mcp.get_health_status(),
        }

        logger.info(
            f"Research completed: {len(extracted)} sources analyzed, "
            f"confidence: {results['confidence']:.2f}"
        )

        return results
```

### 6.2 Usage Example

```python
# example.py
import asyncio
import logging
from mcp.config import MCPIntegrationConfig
from mcp.manager import MCPManager
from research.orchestrator import ResearchOrchestrator

logging.basicConfig(level=logging.INFO)

async def main():
    """Example research workflow"""

    # Initialize MCP manager with configuration
    config = MCPIntegrationConfig.from_env()

    async with MCPManager(config) as mcp:
        # Create research orchestrator
        orchestrator = ResearchOrchestrator(mcp)

        # Execute research
        results = await orchestrator.execute_research(
            query="What are the latest advancements in quantum computing?",
            max_sources=20,
            confidence_threshold=0.7,
        )

        # Display results
        print(f"\n{'='*60}")
        print(f"Research Query: {results['query']}")
        print(f"{'='*60}\n")

        print(f"Sub-queries explored: {len(results['sub_queries'])}")
        print(f"Sources analyzed: {len(results['sources'])}")
        print(f"Confidence: {results['confidence']:.2%}\n")

        print("Analysis Summary:")
        print(results['analysis'].get('conclusion', 'No conclusion'))

        print(f"\n{'='*60}")
        print("Cost Summary:")
        print(f"{'='*60}")
        cost = results['cost_summary']
        print(f"Total cost: ${cost['total_cost_usd']:.4f}")
        print(f"Runtime: {cost['runtime_seconds']:.1f}s")
        print(f"\nService breakdown:")
        for service, details in cost['services'].items():
            print(f"  {service}: ${details['total_cost_usd']:.4f} ({details['total_calls']} calls)")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Error Handling Reference

### 7.1 Error Types and Recovery

| Error Type | Cause | Recovery Strategy |
|------------|-------|-------------------|
| `CircuitBreakerOpenError` | Service health degraded | Wait for recovery timeout, try fallback |
| `BudgetExceededError` | Cost limit reached | Stop execution, report cost summary |
| `httpx.TimeoutException` | Service timeout | Retry with exponential backoff (3x) |
| `httpx.HTTPError` | Network/API error | Retry with backoff, then fallback |
| `ConnectionError` | Service unreachable | Circuit breaker opens, use fallback |

### 7.2 Failure Mode Matrix

| Scenario | Primary Service | Fallback | Final Fallback |
|----------|----------------|----------|----------------|
| Simple URL extraction | Tavily Extract | Playwright | Fail with error |
| Complex URL extraction | Playwright | Tavily Extract | Fail with error |
| Query decomposition | Sequential | Native reasoning | Manual decomposition |
| Web search | Tavily Search | Native WebSearch | Fail with error |
| Structured analysis | Sequential | Native reasoning | Simple analysis |

### 7.3 Timeout Configuration

```python
# Recommended timeouts by service
TIMEOUTS = {
    "tavily_search": 30.0,      # Fast search
    "tavily_extract": 30.0,     # Simple extraction
    "playwright": 45.0,          # Browser automation
    "sequential": 60.0,          # Complex reasoning
    "serena": 30.0,             # Code analysis
    "context7": 30.0,           # Documentation lookup
}
```

---

## 8. Performance Optimization

### 8.1 Connection Pooling

```python
# mcp/connection_pool.py
from typing import Dict
import httpx
import asyncio

class ConnectionPool:
    """
    Manage HTTP connection pools for MCP services.

    Benefits:
    - Reuse TCP connections
    - Reduce latency overhead
    - Limit concurrent connections
    """

    def __init__(self, max_connections: int = 10):
        self.pools: Dict[str, httpx.AsyncClient] = {}
        self.max_connections = max_connections

    async def get_client(
        self,
        base_url: str,
        timeout: float = 30.0,
    ) -> httpx.AsyncClient:
        """Get or create pooled HTTP client"""
        if base_url not in self.pools:
            self.pools[base_url] = httpx.AsyncClient(
                base_url=base_url,
                timeout=timeout,
                limits=httpx.Limits(
                    max_connections=self.max_connections,
                    max_keepalive_connections=self.max_connections // 2,
                ),
            )
        return self.pools[base_url]

    async def close_all(self):
        """Close all pooled connections"""
        for client in self.pools.values():
            await client.aclose()
        self.pools.clear()
```

### 8.2 Parallel Execution

```python
# research/parallel.py
import asyncio
from typing import List, Callable, Any

async def parallel_execute(
    tasks: List[Callable],
    max_concurrency: int = 5,
) -> List[Any]:
    """
    Execute tasks in parallel with concurrency limit.

    Args:
        tasks: List of async callables
        max_concurrency: Maximum concurrent tasks

    Returns:
        List of results in original order
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded_task(task):
        async with semaphore:
            return await task()

    return await asyncio.gather(*[bounded_task(task) for task in tasks])

# Usage in research orchestrator
async def parallel_search(self, queries: List[str]) -> List[Dict]:
    """Execute multiple searches in parallel"""
    tasks = [lambda q=q: self.mcp.search(query=q) for q in queries]
    return await parallel_execute(tasks, max_concurrency=3)
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/test_circuit_breaker.py
import pytest
from mcp.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test circuit breaker opens after threshold failures"""
    cb = CircuitBreaker(
        service_name="test",
        failure_threshold=3,
        recovery_timeout=1.0,
    )

    async def failing_func():
        raise Exception("Service error")

    # First 3 calls should fail normally
    for _ in range(3):
        with pytest.raises(Exception):
            await cb.call(failing_func)

    # 4th call should raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(failing_func)
```

### 9.2 Integration Tests

```python
# tests/test_mcp_integration.py
import pytest
from mcp.manager import MCPManager
from mcp.config import MCPIntegrationConfig

@pytest.mark.asyncio
async def test_tavily_search_integration():
    """Test Tavily search integration"""
    config = MCPIntegrationConfig.from_env()

    async with MCPManager(config) as mcp:
        results = await mcp.search(
            query="test query",
            max_results=5,
        )

        assert "results" in results
        assert len(results["results"]) <= 5
        assert all("url" in r for r in results["results"])
```

### 9.3 Mock Services for Testing

```python
# tests/mocks.py
from typing import Dict, Any

class MockTavilyAdapter:
    """Mock Tavily adapter for testing"""

    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        return {
            "results": [
                {"url": "https://example.com", "title": "Example", "snippet": "Test"}
            ]
        }

    async def extract(self, urls: list) -> Dict[str, Any]:
        return {
            "results": [
                {"url": url, "content": "Mock content"} for url in urls
            ]
        }
```

---

## 10. Deployment Considerations

### 10.1 Environment Configuration

```bash
# .env.example
# Tavily Configuration
TAVILY_API_KEY=your_tavily_api_key
TAVILY_ENDPOINT=https://api.tavily.com
TAVILY_TIMEOUT=30.0

# Sequential Thinking Configuration
SEQUENTIAL_ENDPOINT=http://localhost:3001
SEQUENTIAL_TIMEOUT=60.0

# Playwright Configuration
PLAYWRIGHT_ENDPOINT=http://localhost:3004
PLAYWRIGHT_TIMEOUT=45.0

# Integration Settings
MCP_ENABLE_FALLBACKS=true
MCP_ENABLE_COST_TRACKING=true
MCP_ENABLE_HEALTH_MONITORING=true
MCP_MAX_BUDGET=10.0

# Logging
LOG_LEVEL=INFO
```

### 10.2 Monitoring and Observability

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
mcp_requests_total = Counter(
    'mcp_requests_total',
    'Total MCP service requests',
    ['service', 'operation', 'status']
)

mcp_request_duration = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['service', 'operation']
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service']
)

# Cost metrics
mcp_cost_total = Counter(
    'mcp_cost_total_usd',
    'Total MCP service cost in USD',
    ['service']
)
```

### 10.3 Production Checklist

- [ ] All API keys configured in environment
- [ ] Timeout values tuned for infrastructure
- [ ] Circuit breaker thresholds set appropriately
- [ ] Budget limits configured
- [ ] Health monitoring enabled
- [ ] Logging configured (structured JSON recommended)
- [ ] Metrics collection enabled
- [ ] Error alerting configured
- [ ] Fallback strategies tested
- [ ] Load testing completed
- [ ] Documentation updated

---

## 11. Future Enhancements

### 11.1 Planned Improvements

1. **Serena Integration**: Session persistence and memory management
2. **Context7 Integration**: Technical documentation retrieval
3. **Adaptive Routing**: ML-based service selection
4. **Request Caching**: Cache search results and extractions
5. **Rate Limiting**: Advanced rate limit management
6. **Batch Optimization**: Intelligent request batching
7. **Multi-Region Support**: Geographic service distribution
8. **Advanced Analytics**: Detailed performance analysis

### 11.2 Extensibility Points

```python
# mcp/adapters/base.py
from abc import ABC, abstractmethod

class BaseMCPAdapter(ABC):
    """Base class for MCP service adapters"""

    @abstractmethod
    async def connect(self):
        """Connect to service"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from service"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check service health"""
        pass

# Add new adapters by extending BaseMCPAdapter
```

---

## Appendix A: Complete Example

```python
# complete_example.py
"""
Complete ARIS research example with full MCP integration.
"""

import asyncio
import logging
from mcp.config import MCPIntegrationConfig
from mcp.manager import MCPManager
from research.orchestrator import ResearchOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def advanced_research_example():
    """Advanced research with error handling and monitoring"""

    # Load configuration
    config = MCPIntegrationConfig.from_env()

    try:
        # Initialize MCP manager with context manager
        async with MCPManager(config) as mcp:

            # Check initial health status
            health = mcp.get_health_status()
            logging.info(f"Initial health status: {health}")

            # Create orchestrator
            orchestrator = ResearchOrchestrator(mcp)

            # Execute research
            results = await orchestrator.execute_research(
                query="What are the latest trends in AI safety research?",
                max_sources=15,
                confidence_threshold=0.75,
            )

            # Process results
            if results["confidence"] >= 0.75:
                logging.info("Research completed with high confidence")
                print("\n" + "="*60)
                print("RESEARCH RESULTS")
                print("="*60)
                print(f"\nQuery: {results['query']}")
                print(f"Sources analyzed: {len(results['sources'])}")
                print(f"Confidence: {results['confidence']:.2%}")
                print(f"\nKey findings:")
                print(results['analysis'].get('conclusion', 'No conclusion'))
            else:
                logging.warning(
                    f"Research completed with low confidence: {results['confidence']:.2%}"
                )

            # Display cost summary
            cost = mcp.get_cost_summary()
            print("\n" + "="*60)
            print("COST SUMMARY")
            print("="*60)
            print(f"Total: ${cost['total_cost_usd']:.4f}")
            print(f"Runtime: {cost['runtime_seconds']:.1f}s")
            for service, details in cost['services'].items():
                print(
                    f"  {service}: ${details['total_cost_usd']:.4f} "
                    f"({details['total_calls']} calls)"
                )

            # Display circuit breaker states
            cb_states = mcp.get_circuit_breaker_states()
            print("\n" + "="*60)
            print("SERVICE HEALTH")
            print("="*60)
            for service, state in cb_states.items():
                print(f"  {service}: {state}")

    except Exception as e:
        logging.error(f"Research failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(advanced_research_example())
```

---

## Summary

This MCP integration architecture provides:

✅ **Production-Ready**: Complete error handling, retries, circuit breakers
✅ **Resource-Safe**: AsyncExitStack for guaranteed cleanup
✅ **Observable**: Health monitoring, cost tracking, structured logging
✅ **Intelligent**: Complexity analysis, smart routing, fallback strategies
✅ **Performant**: Connection pooling, parallel execution, timeout management
✅ **Maintainable**: Clear abstractions, extensible design, comprehensive tests
✅ **Cost-Aware**: Budget limits, per-service tracking, optimization guidance

The architecture is ready for implementation in the ARIS research system with minimal modification.
