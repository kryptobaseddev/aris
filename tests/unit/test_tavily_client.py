"""Unit tests for Tavily client with mocked responses."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from aris.mcp.tavily_client import (
    TavilyClient,
    TavilyAPIError,
    TavilyAuthenticationError,
    TavilyRateLimitError,
    CostTracker,
)
from aris.mcp.circuit_breaker import CircuitBreakerOpen
from aris.mcp.complexity_analyzer import ExtractionMethod


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_record_operation(self):
        """Test recording operations and calculating costs."""
        tracker = CostTracker()
        tracker.record_operation("search", 0.01, {"query": "test"})
        tracker.record_operation("extract", 0.01, {"url": "https://example.com"})

        assert tracker.total_cost == 0.02
        assert len(tracker.operations) == 2

    def test_get_summary(self):
        """Test cost summary generation."""
        tracker = CostTracker()
        tracker.record_operation("search", 0.01)
        tracker.record_operation("search", 0.01)
        tracker.record_operation("extract", 0.01)

        summary = tracker.get_summary()
        assert summary["total_cost"] == 0.03
        assert summary["operation_count"] == 3
        assert summary["by_type"]["search"]["count"] == 2
        assert summary["by_type"]["extract"]["count"] == 1

    def test_reset(self):
        """Test resetting cost tracker."""
        tracker = CostTracker()
        tracker.record_operation("search", 0.01)
        tracker.reset()

        assert tracker.total_cost == 0.0
        assert len(tracker.operations) == 0


class TestTavilyClient:
    """Test Tavily client functionality."""

    @pytest.fixture
    def client(self):
        """Create Tavily client for testing."""
        return TavilyClient(api_key="test_key", timeout=10)

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"results": []}
        return response

    @pytest.mark.asyncio
    async def test_search_success(self, client):
        """Test successful search operation."""
        mock_results = [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Test content",
                "score": 0.9,
            }
        ]

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": mock_results}

            results = await client.search("test query", max_results=5)

            assert len(results) == 1
            assert results[0]["title"] == "Test Result"
            assert client.cost_tracker.total_cost == 0.01

    @pytest.mark.asyncio
    async def test_search_with_filters(self, client):
        """Test search with domain filters."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": []}

            await client.search(
                "test",
                include_domains=["example.com"],
                exclude_domains=["spam.com"],
            )

            # Verify filters were passed
            call_args = mock_request.call_args
            payload = call_args[0][1]
            assert "include_domains" in payload
            assert "exclude_domains" in payload

    @pytest.mark.asyncio
    async def test_extract_success(self, client):
        """Test successful URL extraction."""
        mock_results = [
            {"url": "https://example.com", "content": "Extracted content"}
        ]

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": mock_results}

            results = await client.extract(["https://example.com"])

            assert "https://example.com" in results
            assert results["https://example.com"] == "Extracted content"
            assert client.cost_tracker.total_cost == 0.01

    @pytest.mark.asyncio
    async def test_extract_multiple_urls(self, client):
        """Test extracting multiple URLs."""
        urls = [f"https://example{i}.com" for i in range(5)]
        mock_results = [{"url": url, "content": f"Content {i}"} for i, url in enumerate(urls)]

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": mock_results}

            results = await client.extract(urls)

            assert len(results) == 5
            # Cost should be $0.01 per URL
            assert client.cost_tracker.total_cost == 0.05

    @pytest.mark.asyncio
    async def test_extract_url_limit(self, client):
        """Test extraction enforces 10 URL limit."""
        urls = [f"https://example{i}.com" for i in range(11)]

        with pytest.raises(ValueError, match="Maximum 10 URLs"):
            await client.extract(urls)

    @pytest.mark.asyncio
    async def test_crawl_success(self, client):
        """Test successful website crawl."""
        mock_results = [
            {"url": "https://example.com", "title": "Home"},
            {"url": "https://example.com/about", "title": "About"},
        ]

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"results": mock_results}

            results = await client.crawl("https://example.com", depth=2)

            assert len(results) == 2
            # Cost tracked per page crawled
            assert client.cost_tracker.total_cost == 0.02

    @pytest.mark.asyncio
    async def test_map_success(self, client):
        """Test successful site mapping."""
        mock_map = {
            "root": "https://example.com",
            "pages": ["https://example.com/about", "https://example.com/contact"],
        }

        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_map

            result = await client.map("https://example.com")

            assert "root" in result
            assert client.cost_tracker.total_cost == 0.01

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, client):
        """Test circuit breaker opens after failures."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = TavilyAPIError("API error")

            # Trigger 5 failures to open circuit
            for _ in range(5):
                try:
                    await client.search("test")
                except TavilyAPIError:
                    pass

            # Circuit should now be OPEN
            status = client.get_circuit_status()
            assert status["state"] == "open"

            # Next request should fail immediately
            with pytest.raises(CircuitBreakerOpen):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_retry_logic(self, client):
        """Test retry logic with exponential backoff."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            # Fail twice, succeed third time
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                {"results": []},
            ]

            results = await client.search("test")
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """Test authentication error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(TavilyAuthenticationError):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=mock_response)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(TavilyRateLimitError):
                await client.search("test")

    @pytest.mark.asyncio
    async def test_smart_extract_routing(self, client):
        """Test intelligent extraction routing."""
        urls = [
            "https://wikipedia.org/article",  # Static
            "https://twitter.com/status/123",  # Social media (Playwright)
            "https://nytimes.com/article",  # Paywall (search snippet)
        ]

        with patch.object(client, "extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "https://wikipedia.org/article": "Wikipedia content"
            }

            results = await client.smart_extract(urls)

            # Wikipedia should use Tavily Extract
            assert results["https://wikipedia.org/article"]["method"] == "tavily_extract"
            assert results["https://wikipedia.org/article"]["content"] == "Wikipedia content"

            # Twitter should recommend Playwright
            assert results["https://twitter.com/status/123"]["method"] == "playwright_required"

            # NYTimes should recommend search snippet
            assert results["https://nytimes.com/article"]["method"] == "search_snippet"

    @pytest.mark.asyncio
    async def test_search_with_fallback(self, client):
        """Test search with fallback queries."""
        with patch.object(client, "search", new_callable=AsyncMock) as mock_search:
            # First query returns empty, second succeeds
            mock_search.side_effect = [
                [],  # Primary query fails
                [{"title": "Result", "url": "https://example.com"}],  # Fallback succeeds
            ]

            results = await client.search_with_fallback(
                "primary query",
                fallback_queries=["fallback query"],
            )

            assert len(results) == 1
            assert mock_search.call_count == 2

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with TavilyClient(api_key="test_key") as client:
            assert client._client is not None

        # Client should be closed after context
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test manual client closing."""
        # Create client
        client._get_client()
        assert client._client is not None

        # Close
        await client.close()
        assert client._client is None


class TestComplexityIntegration:
    """Test complexity analyzer integration."""

    @pytest.fixture
    def client(self):
        """Create Tavily client."""
        return TavilyClient(api_key="test_key")

    def test_static_domain_detection(self, client):
        """Test detection of static domains."""
        analysis = client.complexity_analyzer.analyze_url("https://wikipedia.org/article")
        assert analysis.recommended_method == ExtractionMethod.TAVILY_EXTRACT
        assert analysis.confidence > 0.9

    def test_javascript_detection(self, client):
        """Test JavaScript-heavy site detection."""
        analysis = client.complexity_analyzer.analyze_url("https://example.com/react-app")
        assert analysis.indicators.has_javascript

    def test_social_media_detection(self, client):
        """Test social media platform detection."""
        analysis = client.complexity_analyzer.analyze_url("https://twitter.com/status/123")
        assert analysis.indicators.is_social_media
        assert analysis.recommended_method == ExtractionMethod.PLAYWRIGHT

    def test_paywall_detection(self, client):
        """Test paywall detection."""
        analysis = client.complexity_analyzer.analyze_url("https://nytimes.com/article")
        assert analysis.indicators.is_paywall
        assert analysis.recommended_method == ExtractionMethod.TAVILY_SEARCH

    def test_auth_required_detection(self, client):
        """Test authentication requirement detection."""
        analysis = client.complexity_analyzer.analyze_url("https://example.com/dashboard/settings")
        assert analysis.indicators.requires_auth

    def test_pdf_detection(self, client):
        """Test PDF document detection."""
        analysis = client.complexity_analyzer.analyze_url("https://example.com/document.pdf")
        assert analysis.indicators.is_pdf
        assert analysis.recommended_method == ExtractionMethod.TAVILY_EXTRACT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
