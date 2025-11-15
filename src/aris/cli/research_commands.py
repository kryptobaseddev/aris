"""Research workflow commands for ARIS CLI (Wave 2 implementation)."""

import asyncio
import click
from pathlib import Path
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from aris.core.config import ConfigManager
from aris.core.progress_tracker import ProgressEvent, ProgressEventType
from aris.core.research_orchestrator import ResearchOrchestrator

console = Console()


@click.command()
@click.argument("query")
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Research depth level",
)
@click.option("--max-cost", type=float, help="Maximum cost in dollars (overrides depth default)")
@click.option("--stream/--no-stream", default=True, help="Stream progress updates in real-time")
@click.pass_context
def research(
    ctx: click.Context, query: str, depth: str, max_cost: float, stream: bool
) -> None:
    """Execute research query with multi-hop analysis.

    The research command performs comprehensive research using:
    - Tavily MCP for web search and evidence gathering
    - Sequential MCP for structured reasoning and hypothesis testing
    - Multi-hop iteration with confidence-based early stopping
    - Cost tracking and budget enforcement
    - Document storage with Git versioning

    Examples:
        aris research "What is quantum computing?"
        aris research "Latest AI developments" --depth deep
        aris research "LLM reasoning methods" --max-cost 1.00
        aris research "Machine learning basics" --no-stream
    """
    formatter = ctx.obj["formatter"]

    try:
        # Run async research
        result = asyncio.run(_execute_research(query, depth, max_cost, stream, formatter))

        if ctx.obj["json"]:
            formatter.json_output(
                {
                    "status": "success",
                    "session_id": str(result.session_id),
                    "query": result.query_text,
                    "document_path": result.document_path,
                    "operation": result.operation,
                    "confidence": result.confidence,
                    "sources": result.sources_analyzed,
                    "hops": result.hops_executed,
                    "cost": result.total_cost,
                    "within_budget": result.within_budget,
                    "duration": result.duration_seconds,
                }
            )
        else:
            _display_research_result(result)

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]✗ Research failed: {e}[/red]")
        raise click.Abort()


async def _execute_research(
    query: str, depth: str, max_cost: float, stream: bool, formatter
) -> "ResearchResult":
    """Execute research workflow with progress tracking.

    Args:
        query: Research query
        depth: Research depth level
        max_cost: Maximum cost override
        stream: Enable progress streaming
        formatter: CLI formatter

    Returns:
        ResearchResult with findings and metrics
    """
    # Get config and initialize orchestrator
    config_mgr = ConfigManager.get_instance()
    config = config_mgr.load()
    orchestrator = ResearchOrchestrator(config)

    # Setup progress tracking
    if stream:
        progress_display = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
        current_task = None

        def progress_callback(event: ProgressEvent):
            nonlocal current_task
            if current_task is not None:
                progress_display.update(current_task, description=event.message)
            else:
                current_task = progress_display.add_task(event.message, total=None)

        orchestrator.progress_tracker.register_callback(progress_callback)

        # Execute with live progress display
        with progress_display:
            current_task = progress_display.add_task("Starting research...", total=None)
            result = await orchestrator.execute_research(
                query=query, depth=depth, max_cost=max_cost
            )
    else:
        # Execute without streaming
        result = await orchestrator.execute_research(
            query=query, depth=depth, max_cost=max_cost
        )

    return result


def _display_research_result(result: "ResearchResult") -> None:
    """Display research result with rich formatting.

    Args:
        result: Research result to display
    """
    # Success header
    if result.success:
        status_icon = "✓"
        status_color = "green"
    else:
        status_icon = "✗"
        status_color = "red"

    console.print(
        f"\n[{status_color} bold]{status_icon} Research Complete[/{status_color} bold]\n"
    )

    # Create results table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Query", result.query_text)
    table.add_row("Document", result.document_path or "N/A")
    table.add_row("Operation", result.operation.upper())
    table.add_row("Confidence", f"{result.confidence:.1%}")
    table.add_row("Sources Analyzed", str(result.sources_analyzed))
    table.add_row("Research Hops", str(result.hops_executed))

    # Cost with budget indicator
    cost_display = f"${result.total_cost:.2f}"
    if result.within_budget:
        cost_display += " [green]✓[/green]"
    else:
        cost_display += " [red]✗ Over budget[/red]"
    table.add_row("Total Cost", cost_display)

    table.add_row("Duration", f"{result.duration_seconds:.1f}s")

    console.print(table)

    # Warnings
    if result.warnings:
        console.print("\n[yellow]⚠ Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")

    # Suggestions
    if result.suggestions:
        console.print("\n[blue]💡 Suggestions:[/blue]")
        for suggestion in result.suggestions:
            console.print(f"  • {suggestion}")

    console.print()


@click.command()
@click.argument("session_id")
@click.pass_context
def status(ctx: click.Context, session_id: str) -> None:
    """Check status of a research session.

    Args:
        session_id: Research session UUID

    Examples:
        aris research status abc123...
    """
    formatter = ctx.obj["formatter"]

    try:
        # Get session status
        config_mgr = ConfigManager.get_instance()
        config = config_mgr.load()
        orchestrator = ResearchOrchestrator(config)

        from uuid import UUID

        session_uuid = UUID(session_id)
        session = asyncio.run(orchestrator.get_session_status(session_uuid))

        if not session:
            if ctx.obj["json"]:
                formatter.json_output({"status": "not_found", "session_id": session_id})
            else:
                console.print(f"[red]✗ Session not found: {session_id}[/red]")
            return

        if ctx.obj["json"]:
            formatter.json_output(
                {
                    "status": session.status,
                    "session_id": str(session.id),
                    "query": session.query.query_text,
                    "hops": len(session.hops),
                    "total_cost": session.total_cost,
                    "confidence": session.final_confidence,
                }
            )
        else:
            _display_session_status(session)

    except ValueError as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": "Invalid session ID format"})
        else:
            console.print(f"[red]✗ Invalid session ID format[/red]")
        raise click.Abort()
    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]✗ Error: {e}[/red]")
        raise click.Abort()


def _display_session_status(session) -> None:
    """Display session status with rich formatting.

    Args:
        session: ResearchSession to display
    """
    # Status header
    status_map = {
        "planning": ("⏳", "yellow"),
        "searching": ("🔍", "blue"),
        "analyzing": ("🤔", "cyan"),
        "complete": ("✓", "green"),
        "error": ("✗", "red"),
    }
    icon, color = status_map.get(session.status, ("•", "white"))

    console.print(f"\n[{color} bold]{icon} Session {session.status.upper()}[/{color} bold]\n")

    # Session details
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Session ID", str(session.id))
    table.add_row("Query", session.query.query_text)
    table.add_row("Depth", session.query.depth.value.upper())
    table.add_row("Status", session.status.upper())
    table.add_row("Hops Completed", str(len(session.hops)))
    table.add_row("Total Cost", f"${session.total_cost:.2f}")
    table.add_row("Budget Target", f"${session.budget_target:.2f}")

    if session.final_confidence > 0:
        table.add_row("Confidence", f"{session.final_confidence:.1%}")

    if session.duration_seconds:
        table.add_row("Duration", f"{session.duration_seconds:.1f}s")

    console.print(table)

    # Budget warnings
    if session.budget_warnings_issued:
        console.print("\n[yellow]⚠ Budget Warnings:[/yellow]")
        for warning in session.budget_warnings_issued:
            console.print(f"  • {warning}")

    console.print()


@click.group()
def research_group():
    """Research workflow commands."""
    pass


# Register commands
research_group.add_command(research)
research_group.add_command(status)
