"""Tavily API client with circuit breaker and cost tracking.

Provides complete integration with Tavily's 4 APIs:
1. Search API - Multi-source web search
2. Extract API - Full-text extraction from URLs
3. Crawl API - Structured website crawling
4. Map API - Site structure mapping

Features:
- Circuit breaker pattern for resilience
- Retry logic with exponential backoff
- Cost tracking ($0.01 per operation)
- Intelligent fallbacks
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

import httpx

from aris.mcp.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from aris.mcp.complexity_analyzer import ComplexityAnalyzer, ExtractionMethod


@dataclass
class CostOperation:
    """Single cost operation record."""

    operation_type: str
    cost: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class CostTracker:
    """Track API operation costs.

    Example:
        tracker = CostTracker()
        tracker.record_operation("search", 0.01, {"query": "AI research"})
        summary = tracker.get_summary()
        print(f"Total cost: ${summary['total_cost']:.2f}")
    """

    def __init__(self, budget_limit: Optional[float] = None):
        """Initialize cost tracker.

        Args:
            budget_limit: Optional budget limit in dollars
        """
        self.operations: list[CostOperation] = []
        self.total_cost: float = 0.0
        self.budget_limit: Optional[float] = budget_limit

    def record_operation(
        self, operation_type: str, cost: float, metadata: Optional[dict] = None
    ) -> None:
        """Record an operation and its cost.

        Args:
            operation_type: Type of operation (search, extract, crawl, map)
            cost: Cost in dollars
            metadata: Optional metadata about the operation

        Raises:
            BudgetExceededError: If budget_limit is set and total_cost exceeds it
        """
        operation = CostOperation(
            operation_type=operation_type,
            cost=cost,
            metadata=metadata or {},
        )
        self.operations.append(operation)
        self.total_cost += cost

        # Enforce budget limit if set
        if self.budget_limit is not None and self.total_cost > self.budget_limit:
            raise BudgetExceededError(
                f"Budget limit ${self.budget_limit:.2f} exceeded: "
                f"current cost ${self.total_cost:.2f}"
            )

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary.

        Returns:
            Dictionary with total cost and breakdown by type
        """
        by_type: dict[str, dict[str, Any]] = {}
        for op in self.operations:
            if op.operation_type not in by_type:
                by_type[op.operation_type] = {"count": 0, "cost": 0.0}
            by_type[op.operation_type]["count"] += 1
            by_type[op.operation_type]["cost"] += op.cost

        return {
            "total_cost": self.total_cost,
            "operation_count": len(self.operations),
            "by_type": by_type,
        }

    def reset(self) -> None:
        """Reset cost tracker (for testing)."""
        self.operations = []
        self.total_cost = 0.0

    # Alias for backward compatibility
    track_operation = record_operation


class TavilyAPIError(Exception):
    """Base exception for Tavily API errors."""

    pass


class TavilyRateLimitError(TavilyAPIError):
    """Rate limit exceeded."""

    pass


class TavilyAuthenticationError(TavilyAPIError):
    """Authentication failed."""

    pass


class BudgetExceededError(TavilyAPIError):
    """Budget limit exceeded."""

    pass


def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    if attempt == max_attempts - 1:
                        raise TavilyAPIError(
                            f"Request failed after {max_attempts} attempts: {e}"
                        ) from e
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                except httpx.HTTPStatusError as e:
                    # Don't retry on 4xx errors (except 429 rate limit)
                    if 400 <= e.response.status_code < 500:
                        if e.response.status_code == 429:
                            raise TavilyRateLimitError("Rate limit exceeded") from e
                        if e.response.status_code == 401:
                            raise TavilyAuthenticationError("Invalid API key") from e
                        raise TavilyAPIError(f"API error: {e}") from e
                    # Retry on 5xx errors
                    if attempt == max_attempts - 1:
                        raise TavilyAPIError(f"API error after {max_attempts} attempts: {e}") from e
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


class TavilyClient:
    """Complete Tavily API client with resilience and cost tracking.

    Example:
        client = TavilyClient(api_key="tvly-...")

        # Search
        results = await client.search("AI research", max_results=5)

        # Extract
        content = await client.extract(["https://example.com"])

        # Crawl
        pages = await client.crawl("https://example.com", depth=2)

        # Map
        sitemap = await client.map("https://example.com")

        # Check costs
        print(client.cost_tracker.get_summary())
    """

    BASE_URL = "https://api.tavily.com"
    COST_PER_OPERATION = 0.01  # $0.01 per operation

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
    ):
        """Initialize Tavily client.

        Args:
            api_key: Tavily API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            circuit_breaker_threshold: Failures before opening circuit
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(failure_threshold=circuit_breaker_threshold)
        self.cost_tracker = CostTracker()
        self.complexity_analyzer = ComplexityAnalyzer()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @retry_with_backoff(max_attempts=3)
    async def _make_request(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to Tavily API.

        Args:
            endpoint: API endpoint (e.g., "/search")
            payload: Request payload

        Returns:
            Response JSON

        Raises:
            CircuitBreakerOpen: If circuit breaker is OPEN
            TavilyAPIError: On API errors
        """
        if not self.circuit_breaker.can_execute():
            status = self.circuit_breaker.get_status()
            next_attempt = status.get("next_attempt_in_seconds", 0)
            raise CircuitBreakerOpen(
                "Tavily circuit breaker is OPEN", next_attempt_in=next_attempt
            )

        client = self._get_client()
        url = f"{self.BASE_URL}{endpoint}"

        # Add API key to payload
        payload["api_key"] = self.api_key

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response.json()
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute web search using Tavily Search API.

        Args:
            query: Search query
            max_results: Maximum number of results (1-20)
            search_depth: "basic" or "advanced"
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            include_raw_content: Include full page content in results

        Returns:
            List of search results with title, url, content, score

        Raises:
            TavilyAPIError: On API errors
        """
        payload = {
            "query": query,
            "max_results": min(max_results, 20),
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        response = await self._make_request("/search", payload)

        # Record cost
        self.cost_tracker.record_operation(
            "search",
            self.COST_PER_OPERATION,
            {"query": query, "max_results": max_results},
        )

        return response.get("results", [])

    async def extract(
        self, urls: list[str], include_raw_content: bool = True
    ) -> dict[str, str]:
        """Extract full content from URLs using Tavily Extract API.

        Args:
            urls: List of URLs to extract (max 10)
            include_raw_content: Include raw HTML content

        Returns:
            Dictionary mapping URL to extracted content

        Raises:
            TavilyAPIError: On API errors
        """
        if len(urls) > 10:
            raise ValueError("Maximum 10 URLs per extract request")

        payload = {
            "urls": urls,
            "include_raw_content": include_raw_content,
        }

        response = await self._make_request("/extract", payload)

        # Record cost (charged per URL)
        for url in urls:
            self.cost_tracker.record_operation(
                "extract", self.COST_PER_OPERATION, {"url": url}
            )

        # Convert response to dict[url -> content]
        results = {}
        for result in response.get("results", []):
            url = result.get("url")
            content = result.get("content", "")
            if url:
                results[url] = content

        return results

    async def crawl(
        self,
        url: str,
        depth: int = 1,
        max_pages: int = 10,
        include_content: bool = True,
    ) -> list[dict[str, Any]]:
        """Crawl website structure using Tavily Crawl API.

        Args:
            url: Starting URL
            depth: Crawl depth (1-3)
            max_pages: Maximum pages to crawl
            include_content: Include page content

        Returns:
            List of crawled pages with URL, title, content

        Raises:
            TavilyAPIError: On API errors
        """
        payload = {
            "url": url,
            "depth": min(depth, 3),
            "max_pages": max_pages,
            "include_content": include_content,
        }

        response = await self._make_request("/crawl", payload)

        # Record cost
        pages_crawled = len(response.get("results", []))
        for _ in range(pages_crawled):
            self.cost_tracker.record_operation(
                "crawl", self.COST_PER_OPERATION, {"url": url, "depth": depth}
            )

        return response.get("results", [])

    async def map(self, url: str) -> dict[str, Any]:
        """Map site structure using Tavily Map API.

        Args:
            url: Website URL to map

        Returns:
            Site structure with pages and links

        Raises:
            TavilyAPIError: On API errors
        """
        payload = {"url": url}

        response = await self._make_request("/map", payload)

        # Record cost
        self.cost_tracker.record_operation("map", self.COST_PER_OPERATION, {"url": url})

        return response

    async def smart_extract(
        self, urls: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Intelligently route URLs to best extraction method.

        Analyzes URL complexity and chooses between:
        - Tavily Extract (simple static content)
        - Playwright (complex JavaScript content)
        - Search snippet (authentication/paywall)

        Args:
            urls: List of URLs to extract

        Returns:
            Dictionary mapping URL to:
            {
                "content": str,
                "method": str,
                "complexity": ComplexityAnalysis
            }
        """
        # Analyze all URLs
        analyses = self.complexity_analyzer.batch_analyze(urls)

        results = {}
        tavily_urls = []
        playwright_urls = []
        search_urls = []

        # Route by complexity
        for url, analysis in analyses.items():
            if analysis.recommended_method == ExtractionMethod.TAVILY_EXTRACT:
                tavily_urls.append(url)
            elif analysis.recommended_method == ExtractionMethod.PLAYWRIGHT:
                playwright_urls.append(url)
            else:  # TAVILY_SEARCH
                search_urls.append(url)

        # Extract using Tavily
        if tavily_urls:
            extracted = await self.extract(tavily_urls)
            for url, content in extracted.items():
                results[url] = {
                    "content": content,
                    "method": "tavily_extract",
                    "complexity": analyses[url],
                }

        # For Playwright URLs, return analysis only (actual extraction requires Playwright MCP)
        for url in playwright_urls:
            results[url] = {
                "content": None,
                "method": "playwright_required",
                "complexity": analyses[url],
                "message": "Requires Playwright MCP for extraction",
            }

        # For search URLs, return analysis only
        for url in search_urls:
            results[url] = {
                "content": None,
                "method": "search_snippet",
                "complexity": analyses[url],
                "message": "Use search snippet instead of full extraction",
            }

        return results

    async def search_with_fallback(
        self, query: str, max_results: int = 10, fallback_queries: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Search with intelligent fallback to alternative queries.

        Args:
            query: Primary search query
            max_results: Maximum results
            fallback_queries: Alternative queries if primary fails

        Returns:
            Search results from primary or fallback query
        """
        try:
            results = await self.search(query, max_results=max_results)
            if results:
                return results
        except TavilyAPIError:
            pass

        # Try fallback queries
        if fallback_queries:
            for fallback in fallback_queries:
                try:
                    results = await self.search(fallback, max_results=max_results)
                    if results:
                        return results
                except TavilyAPIError:
                    continue

        return []

    def get_circuit_status(self) -> dict[str, Any]:
        """Get circuit breaker status.

        Returns:
            Circuit breaker status dictionary
        """
        return self.circuit_breaker.get_status()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
