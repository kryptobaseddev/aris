"""Example: Complete Tavily MCP integration with ConfigManager.

Demonstrates all Tavily API capabilities:
1. Search API - Multi-source web search
2. Extract API - Full-text extraction
3. Crawl API - Website structure crawling
4. Map API - Site structure mapping

Also demonstrates:
- Circuit breaker resilience
- Cost tracking
- Smart extraction routing
- Search with fallback
"""

import asyncio
from aris.core.config import ConfigManager
from aris.mcp.tavily_client import TavilyClient, CircuitBreakerOpen


async def example_search():
    """Example: Basic web search."""
    print("\n=== Example 1: Web Search ===")

    # Get API key from config
    config = ConfigManager.get_instance()
    config.load()
    api_key = config.get_api_key("tavily")

    if not api_key:
        print("❌ Tavily API key not configured")
        print("Run: aris config set tavily <your-api-key>")
        return

    async with TavilyClient(api_key=api_key) as client:
        # Execute search
        results = await client.search(
            query="latest AI research 2024",
            max_results=5,
            search_depth="advanced",
        )

        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.get('title', 'No title')}")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   Score: {result.get('score', 0):.2f}")
            print(f"   Snippet: {result.get('content', '')[:100]}...")

        # Check cost
        cost_summary = client.cost_tracker.get_summary()
        print(f"\n💰 Cost: ${cost_summary['total_cost']:.2f}")


async def example_extract():
    """Example: Extract full content from URLs."""
    print("\n=== Example 2: URL Extraction ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    async with TavilyClient(api_key=api_key) as client:
        urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://github.com/anthropics/anthropic-sdk-python",
        ]

        content = await client.extract(urls)

        for url, text in content.items():
            print(f"\n📄 {url}")
            print(f"   Content length: {len(text)} characters")
            print(f"   Preview: {text[:200]}...")

        cost_summary = client.cost_tracker.get_summary()
        print(f"\n💰 Cost: ${cost_summary['total_cost']:.2f}")


async def example_smart_extract():
    """Example: Smart extraction routing based on complexity."""
    print("\n=== Example 3: Smart Extraction Routing ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    async with TavilyClient(api_key=api_key) as client:
        urls = [
            "https://wikipedia.org/wiki/Python",  # Static → Tavily Extract
            "https://twitter.com/anthropicai",  # Social → Playwright
            "https://nytimes.com/article",  # Paywall → Search snippet
            "https://example.com/api/docs.pdf",  # PDF → Tavily Extract
        ]

        results = await client.smart_extract(urls)

        for url, result in results.items():
            print(f"\n🔍 {url}")
            print(f"   Method: {result['method']}")
            print(f"   Complexity score: {result['complexity'].score}/7")
            print(f"   Reasoning: {result['complexity'].reasoning}")

            if result.get("content"):
                print(f"   Content: {result['content'][:100]}...")
            else:
                print(f"   Note: {result.get('message', 'N/A')}")


async def example_crawl():
    """Example: Crawl website structure."""
    print("\n=== Example 4: Website Crawling ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    async with TavilyClient(api_key=api_key) as client:
        pages = await client.crawl(
            url="https://docs.python.org/3/",
            depth=2,
            max_pages=5,
        )

        print(f"Crawled {len(pages)} pages:")
        for page in pages:
            print(f"   • {page.get('title', 'No title')}")
            print(f"     {page.get('url', 'N/A')}")

        cost_summary = client.cost_tracker.get_summary()
        print(f"\n💰 Cost: ${cost_summary['total_cost']:.2f}")


async def example_circuit_breaker():
    """Example: Circuit breaker resilience."""
    print("\n=== Example 5: Circuit Breaker ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    # Create client with low failure threshold for demo
    client = TavilyClient(api_key="invalid_key", circuit_breaker_threshold=3)

    try:
        # This will fail 3 times and open the circuit
        for i in range(5):
            try:
                await client.search("test query")
            except Exception as e:
                print(f"Attempt {i+1}: {type(e).__name__}")

                # Check circuit status
                status = client.get_circuit_status()
                print(f"   Circuit state: {status['state']}")

                if status['state'] == 'open':
                    next_attempt = status.get('next_attempt_in_seconds', 0)
                    print(f"   Next attempt in: {next_attempt:.1f}s")

    except CircuitBreakerOpen as e:
        print(f"\n🚨 Circuit breaker opened: {e}")
        print(f"   Next attempt in: {e.next_attempt_in:.1f}s")

    await client.close()


async def example_search_with_fallback():
    """Example: Search with intelligent fallback."""
    print("\n=== Example 6: Search with Fallback ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    async with TavilyClient(api_key=api_key) as client:
        # Try primary query with fallbacks
        results = await client.search_with_fallback(
            query="obscure technical term xyz123",
            fallback_queries=[
                "technical term xyz",
                "xyz documentation",
            ],
        )

        if results:
            print(f"✅ Found {len(results)} results")
            for result in results[:3]:
                print(f"   • {result.get('title', 'No title')}")
        else:
            print("❌ No results found even with fallbacks")


async def example_cost_tracking():
    """Example: Comprehensive cost tracking."""
    print("\n=== Example 7: Cost Tracking ===")

    config = ConfigManager.get_instance()
    api_key = config.get_api_key("tavily")

    if not api_key:
        return

    async with TavilyClient(api_key=api_key) as client:
        # Perform various operations
        await client.search("AI research", max_results=5)
        await client.extract(["https://example.com"])
        await client.map("https://example.com")

        # Get detailed cost breakdown
        summary = client.cost_tracker.get_summary()

        print(f"Total cost: ${summary['total_cost']:.2f}")
        print(f"Total operations: {summary['operation_count']}")
        print("\nBreakdown by type:")
        for op_type, stats in summary['by_type'].items():
            print(f"   {op_type}: {stats['count']} ops, ${stats['cost']:.2f}")


async def main():
    """Run all examples."""
    examples = [
        ("Web Search", example_search),
        ("URL Extraction", example_extract),
        ("Smart Routing", example_smart_extract),
        ("Website Crawling", example_crawl),
        ("Circuit Breaker", example_circuit_breaker),
        ("Search Fallback", example_search_with_fallback),
        ("Cost Tracking", example_cost_tracking),
    ]

    print("=" * 60)
    print("Tavily MCP Integration Examples")
    print("=" * 60)

    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
        print("-" * 60)
        try:
            await func()
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
