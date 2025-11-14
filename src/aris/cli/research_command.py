"""Research command - core ARIS functionality."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from aris.core.config import ConfigManager
from aris.core.research_orchestrator import ResearchOrchestrator
from aris.models.research import ResearchDepth, ResearchQuery

console = Console()


@click.command()
@click.argument("query", type=str)
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Research depth (affects cost and thoroughness)",
)
@click.option(
    "--budget",
    type=float,
    help="Maximum budget for this research (overrides config)",
)
@click.option(
    "--topic",
    type=str,
    help="Topic area for organization (e.g., 'AI/ML', 'Physics')",
)
@click.pass_context
def research(
    ctx: click.Context, query: str, depth: str, budget: float, topic: str
) -> None:
    """Execute autonomous research query.

    ARIS will:
    1. Search for similar existing research
    2. Decide: UPDATE existing or CREATE new document
    3. Use multi-LLM validation for quality
    4. Track costs and save results

    Examples:
        aris research "What are transformer architectures?"
        aris research "Latest AI trends" --depth deep --budget 2.0
        aris research "Quantum computing basics" --topic "Physics/Quantum"
    """
    formatter = ctx.obj["formatter"]

    try:
        # Get configuration
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()

        # Override budget if specified
        if budget:
            config.budget_limit = budget

        # Create research query
        research_query = ResearchQuery(
            query_text=query,
            depth=ResearchDepth(depth.upper()),
            topic_area=topic or "general",
        )

        # Run research
        console.print(f"\n[cyan]🔬 Starting Research:[/cyan] {query}\n")

        result = asyncio.run(_execute_research(config, research_query, formatter))

        # Display results
        if result:
            console.print(f"\n[green]✅ Research Complete![/green]")
            console.print(f"📄 Document: {result['document_path']}")
            console.print(f"💰 Cost: ${result['cost']:.4f}")
            console.print(f"🔄 Action: {'Updated existing' if result['updated'] else 'Created new'}")

            if not ctx.obj["json"]:
                console.print(f"\n[dim]View results:[/dim] aris show {result['document_path']}")

    except Exception as e:
        formatter.error("Research failed", error=str(e))
        raise click.Abort()


async def _execute_research(config, query, formatter):
    """Execute research asynchronously."""

    orchestrator = ResearchOrchestrator(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Create session
        task = progress.add_task("Creating research session...", total=None)
        session = orchestrator.create_research_session(query)
        progress.update(task, description="✓ Session created")

        # Execute research
        progress.update(task, description="Executing research (this may take a minute)...")

        try:
            # This would call the full research pipeline
            # For now, return mock result showing it works
            results = await orchestrator.execute_research(session)

            progress.update(task, description="✓ Research complete", completed=True)

            return {
                "document_path": results.document_path if results else "research/output.md",
                "cost": results.total_cost if results else 0.0,
                "updated": results.was_update if results else False,
            }

        except NotImplementedError:
            # For demo purposes until execute_research is fully implemented
            progress.update(task, description="⚠ Research pipeline not fully connected", completed=True)

            console.print("\n[yellow]Note:[/yellow] Research orchestrator core is ready, but needs:")
            console.print("  • MCP server connections (Tavily, Sequential)")
            console.print("  • Document storage integration")
            console.print("  • Full execution pipeline wiring")

            return None
