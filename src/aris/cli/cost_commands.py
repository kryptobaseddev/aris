"""CLI commands for cost tracking and budget management.

Provides:
- Cost summary reporting
- Cost history analysis
- Budget threshold management
- Cost analytics dashboard
"""

from datetime import datetime
from typing import Optional
import json

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from aris.core.config import ConfigManager
from aris.core.cost_manager import CostManager
from aris.storage.session_manager import SessionManager


console = Console()


@click.group()
def cost_group() -> None:
    """Cost tracking and budget management commands.

    Track research costs, monitor budget usage, and analyze spending patterns.

    Examples:
        aris cost summary <session-id>
        aris cost history --days 30
        aris cost analytics
    """
    pass


@cost_group.command()
@click.argument("session_id", required=False)
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def summary(ctx: click.Context, session_id: Optional[str], json: bool) -> None:
    """Show cost summary for a research session.

    If no session_id provided, shows summary for all recent sessions.

    Args:
        session_id: Optional session ID to show detailed cost breakdown
        json: Output in JSON format
    """
    try:
        config = ConfigManager.get_instance()
        session_manager = SessionManager(config.get_db_engine())
        cost_manager = CostManager(session_manager)

        if session_id:
            # Show detailed summary for specific session
            import asyncio
            summary_data = asyncio.run(cost_manager.get_session_summary(session_id))

            if not summary_data:
                console.print(f"[red]Session {session_id} not found[/red]")
                ctx.exit(1)

            if json:
                click.echo(json.dumps(summary_data, indent=2))
            else:
                # Display as formatted table
                table = Table(title=f"Cost Summary - Session {session_id}")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Status", summary_data["status"])
                table.add_row("Hops Completed", f"{summary_data['hops_completed']}/{summary_data['total_hops']}")
                table.add_row("Tavily Cost", f"${summary_data['tavily_cost']:.4f}")
                table.add_row("LLM Tokens", f"{summary_data['llm_tokens']:,}")
                table.add_row("LLM Cost", f"${summary_data['llm_cost']:.4f}")
                table.add_row("Total Cost", f"${summary_data['total_cost']:.4f}")
                table.add_row("Budget Target", f"${summary_data['budget_target']:.4f}")
                table.add_row("Budget Used", f"{summary_data['budget_used_percentage']:.1f}%")

                within_budget = "✓ Within Budget" if summary_data["within_budget"] else "✗ Over Budget"
                table.add_row("Status", within_budget, style="green" if summary_data["within_budget"] else "red")
                table.add_row("Warnings Issued", str(summary_data["warnings_issued"]))

                console.print(table)
        else:
            # Show summary for all sessions
            import asyncio
            all_summaries = asyncio.run(cost_manager.get_all_sessions_cost_summary())

            if not all_summaries:
                console.print("[yellow]No sessions found[/yellow]")
                ctx.exit(0)

            if json:
                click.echo(json.dumps(all_summaries, indent=2))
            else:
                table = Table(title="Cost Summary - All Sessions")
                table.add_column("Session ID", style="cyan", no_wrap=True)
                table.add_column("Status", style="magenta")
                table.add_column("Hops", justify="right")
                table.add_column("Total Cost", justify="right", style="green")
                table.add_column("Budget %", justify="right")
                table.add_column("Within Budget", justify="center")

                for summary in sorted(all_summaries, key=lambda x: x["started_at"], reverse=True):
                    within_budget = "✓" if summary["within_budget"] else "✗"
                    style = "green" if summary["within_budget"] else "red"

                    table.add_row(
                        summary["session_id"][:8] + "...",
                        summary["status"],
                        f"{summary['hops_completed']}/{summary['total_hops']}",
                        f"${summary['total_cost']:.4f}",
                        f"{summary['budget_used_percentage']:.1f}%",
                        within_budget,
                        style=style,
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        if ctx.obj.get("verbose"):
            raise
        ctx.exit(1)


@cost_group.command()
@click.option("--days", type=int, default=30, help="Number of days to analyze (default: 30)")
@click.option("--topic-id", help="Filter by topic ID")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def history(ctx: click.Context, days: int, topic_id: Optional[str], json: bool) -> None:
    """Show cost history for a time period.

    Displays spending patterns and trends over time.

    Args:
        days: Number of days to look back (default: 30)
        topic_id: Optional filter by topic ID
        json: Output in JSON format
    """
    try:
        config = ConfigManager.get_instance()
        session_manager = SessionManager(config.get_db_engine())
        cost_manager = CostManager(session_manager)

        import asyncio
        history_data = asyncio.run(cost_manager.get_cost_history(days=days, topic_id=topic_id))

        if json:
            click.echo(json.dumps(history_data, indent=2))
        else:
            # Display summary
            console.print(
                Panel(
                    f"[bold cyan]Cost History - Last {days} Days[/bold cyan]\n"
                    f"Total Sessions: [green]{history_data['total_sessions']}[/green]\n"
                    f"Total Cost: [yellow]${history_data['total_cost']:.4f}[/yellow]\n"
                    f"Average Cost/Session: [yellow]${history_data['average_cost_per_session']:.4f}[/yellow]"
                )
            )

            # Daily breakdown
            if history_data["daily_costs"]:
                table = Table(title="Daily Breakdown")
                table.add_column("Date", style="cyan")
                table.add_column("Sessions", justify="right")
                table.add_column("Total Cost", justify="right", style="green")
                table.add_column("Hops", justify="right")

                for day, costs in sorted(history_data["daily_costs"].items()):
                    table.add_row(
                        day,
                        str(costs["sessions"]),
                        f"${costs['total_cost']:.4f}",
                        str(costs["hops"]),
                    )

                console.print(table)

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        if ctx.obj.get("verbose"):
            raise
        ctx.exit(1)


@cost_group.command()
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def analytics(ctx: click.Context, json: bool) -> None:
    """Show cost analytics and trends.

    Provides insights into spending patterns and cost efficiency metrics.
    """
    try:
        config = ConfigManager.get_instance()
        session_manager = SessionManager(config.get_db_engine())
        cost_manager = CostManager(session_manager)

        import asyncio

        # Get various time periods
        period_1week = asyncio.run(cost_manager.get_cost_history(days=7))
        period_30days = asyncio.run(cost_manager.get_cost_history(days=30))

        analytics = {
            "1_week": {
                "total_cost": period_1week["total_cost"],
                "session_count": period_1week["total_sessions"],
                "avg_per_session": period_1week["average_cost_per_session"],
            },
            "30_days": {
                "total_cost": period_30days["total_cost"],
                "session_count": period_30days["total_sessions"],
                "avg_per_session": period_30days["average_cost_per_session"],
            },
        }

        if json:
            click.echo(json.dumps(analytics, indent=2))
        else:
            # Display analytics dashboard
            table = Table(title="Cost Analytics Dashboard")
            table.add_column("Period", style="cyan")
            table.add_column("Sessions", justify="right", style="magenta")
            table.add_column("Total Cost", justify="right", style="green")
            table.add_column("Avg/Session", justify="right", style="yellow")

            table.add_row(
                "Last 7 Days",
                str(analytics["1_week"]["session_count"]),
                f"${analytics['1_week']['total_cost']:.4f}",
                f"${analytics['1_week']['avg_per_session']:.4f}",
            )

            table.add_row(
                "Last 30 Days",
                str(analytics["30_days"]["session_count"]),
                f"${analytics['30_days']['total_cost']:.4f}",
                f"${analytics['30_days']['avg_per_session']:.4f}",
            )

            console.print(table)

            # Trend analysis
            week_vs_month_ratio = (
                analytics["1_week"]["total_cost"] / analytics["30_days"]["total_cost"]
                if analytics["30_days"]["total_cost"] > 0
                else 0
            )

            if week_vs_month_ratio > 0.2:
                trend = "[red]↑ Increasing[/red]"
            elif week_vs_month_ratio < 0.1:
                trend = "[green]↓ Decreasing[/green]"
            else:
                trend = "[yellow]→ Stable[/yellow]"

            console.print(f"\nTrend (7-day vs 30-day avg): {trend}")

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        if ctx.obj.get("verbose"):
            raise
        ctx.exit(1)


@cost_group.command()
@click.option("--days", type=int, default=30, help="Export data from last N days")
@click.option("--format", type=click.Choice(["json", "csv"]), default="json", help="Export format")
@click.pass_context
def export(ctx: click.Context, days: int, format: str) -> None:
    """Export cost history to file.

    Generates a report file for external analysis or archival.

    Args:
        days: Number of days of data to export
        format: Export format (json or csv)
    """
    try:
        config = ConfigManager.get_instance()
        session_manager = SessionManager(config.get_db_engine())
        cost_manager = CostManager(session_manager)

        import asyncio
        export_file = asyncio.run(cost_manager.export_cost_history(format=format))

        console.print(f"[green]✓ Cost history exported to[/green] {export_file}")

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        if ctx.obj.get("verbose"):
            raise
        ctx.exit(1)


@cost_group.command()
@click.option("--tavily-cost", type=float, default=0.01, help="Cost per Tavily search")
@click.option("--llm-cost-per-k-tokens", type=float, default=0.01, help="Cost per 1K LLM tokens")
@click.pass_context
def configure(ctx: click.Context, tavily_cost: float, llm_cost_per_k_tokens: float) -> None:
    """Configure pricing for cost calculations.

    Update the pricing model used for cost tracking.

    Args:
        tavily_cost: Cost per Tavily search operation
        llm_cost_per_k_tokens: Cost per 1000 LLM tokens
    """
    try:
        config = ConfigManager.get_instance()
        session_manager = SessionManager(config.get_db_engine())
        cost_manager = CostManager(session_manager)

        cost_manager.set_pricing(
            tavily_per_search=tavily_cost,
            llm_per_1k_tokens=llm_cost_per_k_tokens,
        )

        table = Table(title="Cost Configuration Updated")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Tavily Cost per Search", f"${tavily_cost:.4f}")
        table.add_row("LLM Cost per 1K Tokens", f"${llm_cost_per_k_tokens:.4f}")

        console.print(table)
        console.print("[green]✓ Configuration updated[/green]")

    except Exception as e:
        console.print(f"[red]Error[/red]: {e}")
        if ctx.obj.get("verbose"):
            raise
        ctx.exit(1)
