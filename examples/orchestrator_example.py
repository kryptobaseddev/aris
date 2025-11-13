"""Example usage of ResearchOrchestrator for complete research workflows.

This demonstrates the end-to-end research capability integrating:
- Tavily MCP for web search
- Sequential MCP for reasoning
- Document Store for Git versioning
- Progress tracking for CLI updates
"""

import asyncio
import logging
from pathlib import Path

from aris.core.config import ConfigManager
from aris.core.progress_tracker import ProgressEvent, ProgressEventType
from aris.core.research_orchestrator import ResearchOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def basic_research_example():
    """Basic research workflow."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Research")
    print("="*60 + "\n")

    # Get configuration
    config = ConfigManager.get_instance().get_config()
    orchestrator = ResearchOrchestrator(config)

    # Execute research
    result = await orchestrator.execute_research(
        query="What is quantum computing?",
        depth="quick",
        max_cost=0.20
    )

    # Display results
    print(f"\nResearch Complete!")
    print(f"  Document: {result.document_path}")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Cost: ${result.total_cost:.2f}")
    print(f"  Hops: {result.hops_executed}")
    print(f"  Sources: {result.sources_analyzed}")
    print(f"  Duration: {result.duration_seconds:.1f}s")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


async def research_with_streaming():
    """Research with real-time progress updates."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Research with Progress Streaming")
    print("="*60 + "\n")

    config = ConfigManager.get_instance().get_config()
    orchestrator = ResearchOrchestrator(config)

    # Register progress callback
    def show_progress(event: ProgressEvent):
        icon_map = {
            ProgressEventType.STARTED: "🚀",
            ProgressEventType.PLANNING: "📋",
            ProgressEventType.SEARCHING: "🔍",
            ProgressEventType.ANALYZING: "🤔",
            ProgressEventType.SYNTHESIZING: "🧩",
            ProgressEventType.SAVING: "💾",
            ProgressEventType.COMPLETED: "✅",
            ProgressEventType.ERROR: "❌",
            ProgressEventType.WARNING: "⚠️",
        }
        icon = icon_map.get(event.event_type, "•")

        if event.percentage:
            print(f"{icon} {event.message} ({event.percentage:.0f}%)")
        else:
            print(f"{icon} {event.message}")

    orchestrator.progress_tracker.register_callback(show_progress)

    # Execute research with streaming
    result = await orchestrator.execute_research(
        query="Latest advances in large language models",
        depth="standard",
        max_cost=0.50
    )

    print(f"\n✅ Research saved to: {result.document_path}")


async def deep_research_example():
    """Deep research with custom budget."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Deep Research with Custom Budget")
    print("="*60 + "\n")

    config = ConfigManager.get_instance().get_config()
    orchestrator = ResearchOrchestrator(config)

    # Track events for analysis
    events = []
    orchestrator.progress_tracker.register_callback(lambda e: events.append(e))

    # Execute deep research
    result = await orchestrator.execute_research(
        query="How do transformer models implement attention mechanisms?",
        depth="deep",
        max_cost=1.00
    )

    # Analyze events
    print(f"Research Statistics:")
    print(f"  Total Events: {len(events)}")
    print(f"  Duration: {orchestrator.progress_tracker.duration_seconds:.1f}s")
    print(f"  Errors: {orchestrator.progress_tracker.has_errors}")
    print(f"  Warnings: {orchestrator.progress_tracker.has_warnings}")

    print(f"\nResearch Outcome:")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Hops: {result.hops_executed}")
    print(f"  Cost: ${result.total_cost:.2f}")
    print(f"  Budget: ${result.total_cost:.2f} / $1.00 ({result.within_budget and '✅' or '❌'})")


async def context_manager_example():
    """Using orchestrator as async context manager."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Async Context Manager")
    print("="*60 + "\n")

    config = ConfigManager.get_instance().get_config()

    async with ResearchOrchestrator(config) as orchestrator:
        result = await orchestrator.execute_research(
            query="Benefits of async programming in Python",
            depth="quick"
        )

        print(f"✅ Research complete: {result.document_path}")
        print(f"   Confidence: {result.confidence:.1%}")

    print("✅ Resources automatically cleaned up")


async def batch_research_example():
    """Execute multiple research queries in batch."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Batch Research")
    print("="*60 + "\n")

    config = ConfigManager.get_instance().get_config()
    orchestrator = ResearchOrchestrator(config)

    queries = [
        "What is machine learning?",
        "What is deep learning?",
        "What is reinforcement learning?"
    ]

    results = []
    for query in queries:
        print(f"\n🔍 Researching: {query}")
        result = await orchestrator.execute_research(
            query=query,
            depth="quick",
            max_cost=0.20
        )
        results.append(result)
        print(f"   ✅ {result.confidence:.0%} confidence, ${result.total_cost:.2f}")

    # Summary
    print(f"\nBatch Summary:")
    print(f"  Total Queries: {len(results)}")
    print(f"  Total Cost: ${sum(r.total_cost for r in results):.2f}")
    print(f"  Avg Confidence: {sum(r.confidence for r in results) / len(results):.1%}")
    print(f"  Total Sources: {sum(r.sources_analyzed for r in results)}")


async def error_handling_example():
    """Demonstrate error handling."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Error Handling")
    print("="*60 + "\n")

    config = ConfigManager.get_instance().get_config()
    orchestrator = ResearchOrchestrator(config)

    try:
        # Execute research that might fail
        result = await orchestrator.execute_research(
            query="This is a test query",
            depth="quick",
            max_cost=0.10
        )
        print(f"✅ Success: {result.document_path}")

    except Exception as e:
        print(f"❌ Error occurred: {e}")

        # Check progress tracker for details
        if orchestrator.progress_tracker.has_errors:
            error_events = orchestrator.progress_tracker.get_events_by_type(
                ProgressEventType.ERROR
            )
            print(f"\nError Details:")
            for event in error_events:
                print(f"  - {event.message}")
                if event.data:
                    print(f"    {event.data}")


async def main():
    """Run all examples."""
    examples = [
        ("Basic Research", basic_research_example),
        ("Progress Streaming", research_with_streaming),
        ("Deep Research", deep_research_example),
        ("Context Manager", context_manager_example),
        ("Batch Research", batch_research_example),
        ("Error Handling", error_handling_example),
    ]

    print("\n" + "="*60)
    print("RESEARCH ORCHESTRATOR EXAMPLES")
    print("="*60)
    print("\nThis script demonstrates complete research workflows.")
    print("Make sure you have:")
    print("  - TAVILY_API_KEY set in environment")
    print("  - Sequential MCP installed (npx @modelcontextprotocol/sequential-thinking)")
    print("  - ARIS initialized (aris init)")

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            logger.exception(f"Example {name} failed")

    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
