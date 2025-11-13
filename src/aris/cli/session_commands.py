"""Session management commands for ARIS CLI."""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from aris.core.config import ConfigManager
from aris.storage.database import DatabaseManager
from aris.storage.session_manager import SessionManager

console = Console()


@click.group()
def session() -> None:
    """Manage research sessions.

    Session commands for tracking, resuming, and analyzing research sessions.
    Sessions persist across multiple runs, allowing interrupted research to be resumed.

    Examples:
        aris session list
        aris session list --status complete
        aris session show <session-id>
        aris session resume <session-id>
        aris session stats
        aris session export <session-id> --format json
        aris session delete <session-id>
    """
    pass


def _get_session_manager() -> SessionManager:
    """Get initialized SessionManager with database connection."""
    config = ConfigManager.get_instance().get_config()
    db_manager = DatabaseManager(config.database_path)
    db_manager.initialize_database()
    db_session = db_manager.get_session()
    return SessionManager(db_session)


@session.command()
@click.option("--status", type=click.Choice(["planning", "searching", "analyzing", "validating", "complete", "error"]), help="Filter by status")
@click.option("--limit", type=int, default=20, help="Maximum sessions to display")
@click.pass_context
def list(ctx: click.Context, status: str, limit: int) -> None:
    """List all research sessions with optional filtering."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        sessions = manager.list_sessions(status=status, limit=limit)

        if ctx.obj["json"]:
            formatter.json_output({
                "status": "success",
                "count": len(sessions),
                "sessions": [
                    {
                        "id": s.id,
                        "query": s.query_text[:100],
                        "depth": s.query_depth,
                        "status": s.status,
                        "cost": round(s.total_cost, 4),
                        "confidence": round(s.final_confidence, 3),
                        "hops_executed": s.current_hop - 1,
                        "created_at": s.started_at.isoformat(),
                        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    }
                    for s in sessions
                ]
            })
        else:
            if not sessions:
                console.print("[yellow]No sessions found[/yellow]")
                return

            table = Table(title=f"Research Sessions ({len(sessions)})" + (f" - Status: {status}" if status else ""))
            table.add_column("Session ID", style="cyan", no_wrap=True)
            table.add_column("Query", style="green")
            table.add_column("Status", style="blue")
            table.add_column("Cost", style="yellow", justify="right")
            table.add_column("Confidence", style="magenta", justify="right")
            table.add_column("Hops", justify="right")
            table.add_column("Created", style="dim")

            for s in sessions:
                table.add_row(
                    str(s.id)[:8],
                    s.query_text[:40] + ("..." if len(s.query_text) > 40 else ""),
                    s.status,
                    f"${s.total_cost:.3f}",
                    f"{s.final_confidence:.2%}",
                    str(s.current_hop - 1),
                    s.started_at.strftime("%Y-%m-%d %H:%M")
                )

            console.print(table)

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error listing sessions: {e}[/red]")
        raise click.Abort()


@session.command()
@click.argument("session_id")
@click.pass_context
def show(ctx: click.Context, session_id: str) -> None:
    """Show detailed information about a research session."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        stats = manager.get_session_statistics(session_id)

        if not stats:
            if ctx.obj["json"]:
                formatter.json_output({"status": "not_found", "session_id": session_id})
            else:
                console.print(f"[red]Session '{session_id}' not found[/red]")
            raise click.Abort()

        if ctx.obj["json"]:
            formatter.json_output({
                "status": "success",
                **stats
            })
        else:
            # Display session info
            session_info = stats["session"]
            timing = stats["timing"]
            cost = stats["cost"]
            confidence = stats["confidence"]
            sources = stats["sources"]

            console.print(Panel(
                f"[bold cyan]Session: {session_info['id'][:8]}[/bold cyan]\n"
                f"Query: {session_info['query']}\n"
                f"Status: [bold]{session_info['status']}[/bold]",
                title="Session Info"
            ))

            console.print("\n[bold]Timing:[/bold]")
            console.print(f"  Created: {session_info['created_at']}")
            if session_info['completed_at']:
                console.print(f"  Completed: {session_info['completed_at']}")
                console.print(f"  Duration: {timing['duration_seconds']:.1f}s" if timing['duration_seconds'] else "")
            console.print(f"  Hops: {timing['hops_executed']}/{timing['max_hops_allowed']}")

            console.print(f"\n[bold]Cost:[/bold]")
            console.print(f"  Total: ${cost['total']:.4f}")
            console.print(f"  Budget: ${cost['budget_target']:.4f}")
            console.print(f"  Remaining: ${cost['budget_remaining']:.4f}")
            console.print(f"  Within Budget: {'✓' if cost['within_budget'] else '✗'}")

            console.print(f"\n[bold]Confidence:[/bold]")
            console.print(f"  Initial: {confidence['initial']:.2%}")
            console.print(f"  Final: {confidence['final']:.2%}")
            console.print(f"  Gain: {confidence['total_gain']:.2%}")

            console.print(f"\n[bold]Sources:[/bold]")
            console.print(f"  Total Found: {sources['total_found']}")
            console.print(f"  Total Added: {sources['total_added']}")

            # Show hops details
            hops = stats["hops"]
            if hops:
                console.print(f"\n[bold]Hops Details:[/bold]")
                hop_table = Table(show_header=True)
                hop_table.add_column("Hop", justify="right")
                hop_table.add_column("Query", style="green")
                hop_table.add_column("Found", justify="right")
                hop_table.add_column("Added", justify="right")
                hop_table.add_column("Confidence Gain", justify="right")
                hop_table.add_column("Cost", justify="right")

                for hop in hops:
                    hop_table.add_row(
                        str(hop["hop_number"]),
                        hop["query"][:30] + ("..." if len(hop["query"]) > 30 else ""),
                        str(hop["sources_found"]),
                        str(hop["sources_added"]),
                        f"{hop['confidence_gain']:.2%}",
                        f"${hop['cost']:.4f}"
                    )

                console.print(hop_table)

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@session.command()
@click.argument("session_id")
@click.pass_context
def resume(ctx: click.Context, session_id: str) -> None:
    """Resume a previously interrupted research session."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        research_session = manager.get_session_with_hops(session_id)

        if not research_session:
            if ctx.obj["json"]:
                formatter.json_output({"status": "not_found", "session_id": session_id})
            else:
                console.print(f"[red]Session '{session_id}' not found[/red]")
            raise click.Abort()

        # Check if resumable
        if research_session.status in ("complete", "error"):
            if ctx.obj["json"]:
                formatter.json_output({
                    "status": "error",
                    "message": f"Cannot resume session with status '{research_session.status}'"
                })
            else:
                console.print(f"[red]Cannot resume session with status '{research_session.status}'[/red]")
            raise click.Abort()

        if ctx.obj["json"]:
            formatter.json_output({
                "status": "resuming",
                "session_id": str(research_session.id),
                "query": research_session.query_text,
                "current_hop": research_session.current_hop,
                "max_hops": research_session.max_hops,
                "hops_completed": len(research_session.hops),
                "cost_so_far": round(research_session.total_cost, 4),
                "confidence": round(research_session.final_confidence, 3),
            })
        else:
            console.print(Panel(
                f"[bold cyan]Resuming Session {str(research_session.id)[:8]}[/bold cyan]\n"
                f"Query: {research_session.query_text}\n"
                f"Current Hop: {research_session.current_hop}/{research_session.max_hops}\n"
                f"Cost So Far: ${research_session.total_cost:.4f}\n"
                f"Confidence: {research_session.final_confidence:.2%}",
                title="Session Resume"
            ))

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@session.command()
@click.argument("session_id")
@click.option("--format", type=click.Choice(["json"]), default="json", help="Export format")
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.pass_context
def export(ctx: click.Context, session_id: str, format: str, output: str) -> None:
    """Export session data for external analysis."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        exported_data = manager.export_session(session_id, format=format)

        if not exported_data:
            if ctx.obj["json"]:
                formatter.json_output({"status": "not_found", "session_id": session_id})
            else:
                console.print(f"[red]Session '{session_id}' not found[/red]")
            raise click.Abort()

        if output:
            output_path = Path(output)
            output_path.write_text(exported_data)
            if ctx.obj["json"]:
                formatter.json_output({
                    "status": "success",
                    "message": f"Exported to {output}",
                    "file": str(output_path.absolute())
                })
            else:
                console.print(f"[green]✓ Exported to {output}[/green]")
        else:
            if ctx.obj["json"]:
                formatter.json_output(json.loads(exported_data))
            else:
                console.print(exported_data)

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@session.command()
@click.argument("session_id")
@click.confirmation_option(prompt="Are you sure you want to delete this session?")
@click.pass_context
def delete(ctx: click.Context, session_id: str) -> None:
    """Delete a research session."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        deleted = manager.delete_session(session_id)

        if not deleted:
            if ctx.obj["json"]:
                formatter.json_output({"status": "not_found", "session_id": session_id})
            else:
                console.print(f"[red]Session '{session_id}' not found[/red]")
            raise click.Abort()

        if ctx.obj["json"]:
            formatter.json_output({
                "status": "success",
                "message": f"Session deleted",
                "session_id": session_id
            })
        else:
            console.print(f"[green]✓ Session {session_id[:8]} deleted[/green]")

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@session.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Display aggregate statistics across all sessions."""
    formatter = ctx.obj["formatter"]

    try:
        manager = _get_session_manager()
        stats_data = manager.get_all_statistics()

        if ctx.obj["json"]:
            formatter.json_output({
                "status": "success",
                **stats_data
            })
        else:
            console.print(Panel(
                f"[bold]Total Sessions: {stats_data['total_sessions']}[/bold]\n"
                f"Completed: {stats_data['completed_sessions']}\n"
                f"Total Cost: ${stats_data['aggregate_cost']:.4f}\n"
                f"Avg Cost/Session: ${stats_data['average_cost_per_session']:.4f}",
                title="Session Statistics"
            ))

            if stats_data["by_status"]:
                console.print("\n[bold]By Status:[/bold]")
                for status, counts in stats_data["by_status"].items():
                    console.print(f"  {status}: {counts['count']} (${counts['total_cost']:.4f})")

            if stats_data["by_depth"]:
                console.print("\n[bold]By Depth:[/bold]")
                for depth, counts in stats_data["by_depth"].items():
                    console.print(f"  {depth}: {counts['count']} (${counts['total_cost']:.4f})")

            console.print(f"\n[bold]Hops:[/bold]")
            console.print(f"  Total Executed: {stats_data['total_hops_executed']}")
            console.print(f"  Average per Session: {stats_data['average_hops_per_session']:.2f}")

    except Exception as e:
        if ctx.obj["json"]:
            formatter.json_output({"status": "error", "message": str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
