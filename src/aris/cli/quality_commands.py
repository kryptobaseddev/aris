"""Quality validation and metrics commands.

Provides CLI interface for quality validation gates, metrics analysis,
and source credibility assessment.
"""

import json
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from aris.core.quality_validator import QualityValidator, SourceCredibilityTracker
from aris.models.quality import QualityGateLevel
from aris.models.source import Source, SourceType
from aris.utils.output import OutputFormatter

console = Console()


@click.group()
@click.pass_context
def quality(ctx: click.Context) -> None:
    """Quality validation and metrics commands.

    Provides quality gates, confidence scoring, and source credibility
    assessment for research results.

    Examples:
        aris quality validate --query "What is CRISPR?" --depth standard
        aris quality report <session_id>
        aris quality sources list
    """
    pass


@quality.command(name="validate")
@click.option(
    "--query",
    required=True,
    help="Research query to validate",
)
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Research depth level",
)
@click.option(
    "--budget",
    type=float,
    default=0.50,
    help="Available budget in dollars",
)
@click.option(
    "--gate-level",
    type=click.Choice(["permissive", "standard", "strict"]),
    default="standard",
    help="Validation strictness level",
)
@click.option(
    "--session-id",
    help="Session ID (optional, generates random if not provided)",
)
@click.pass_context
def validate_query(
    ctx: click.Context,
    query: str,
    depth: str,
    budget: float,
    gate_level: str,
    session_id: Optional[str],
) -> None:
    """Validate research query before execution.

    Checks query clarity, specificity, budget sufficiency, and feasibility.

    \b
    Examples:
        aris quality validate \\
            --query "What is CRISPR gene therapy?" \\
            --depth standard \\
            --budget 0.50

        aris quality validate \\
            --query "Latest advances in quantum computing" \\
            --depth deep \\
            --budget 2.00 \\
            --gate-level strict
    """
    import asyncio
    from uuid import uuid4

    if not session_id:
        session_id = str(uuid4())

    # Select gate level
    gate_enum = QualityGateLevel(gate_level)

    # Create validator
    validator = QualityValidator(gate_level=gate_enum)
    formatter = ctx.obj.get("formatter", OutputFormatter())

    # Run validation
    report = asyncio.run(
        validator.validate_pre_execution(
            session_id=session_id,
            query=query,
            depth=depth,
            budget=budget,
        )
    )

    # Format output
    if ctx.obj.get("json"):
        console.print_json(
            data=json.loads(report.model_dump_json()),
        )
    else:
        # Display as formatted table
        console.print(
            f"\n[bold cyan]Pre-Execution Validation Report[/bold cyan]\n"
        )

        console.print(f"[bold]Query:[/bold] {report.query}")
        console.print(f"[bold]Depth:[/bold] {report.depth}")
        console.print(f"[bold]Budget:[/bold] ${report.budget:.2f}")
        console.print(f"[bold]Session ID:[/bold] {report.session_id}\n")

        # Scores
        console.print("[bold]Validation Scores:[/bold]")
        console.print(f"  Query Clarity:      {report.query_clarity_score:.2f}")
        console.print(f"  Query Specificity:  {report.query_specificity_score:.2f}")
        console.print(f"  Budget Sufficiency: {report.budget_sufficiency_score:.2f}")
        console.print(f"  Feasibility:        {report.feasibility_score:.2f}")
        console.print(f"  Overall Readiness:  {report.overall_readiness:.2f}\n")

        # Result
        if report.can_proceed:
            console.print("[bold green]✓ Can Proceed[/bold green]")
        else:
            console.print("[bold red]✗ Cannot Proceed[/bold red]")

        # Issues
        if report.issues:
            console.print("\n[bold yellow]Issues:[/bold yellow]")
            for issue in report.issues:
                console.print(f"  • {issue}")

        # Recommendations
        if report.recommendations:
            console.print("\n[bold cyan]Recommendations:[/bold cyan]")
            for rec in report.recommendations:
                console.print(f"  • {rec}")

        console.print()


@quality.command(name="report")
@click.argument("session_id")
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show detailed source credibility scores",
)
@click.pass_context
def quality_report(
    ctx: click.Context,
    session_id: str,
    show_sources: bool,
) -> None:
    """Display quality validation report for a research session.

    \b
    Examples:
        aris quality report abc123def456

        aris quality report abc123def456 --show-sources
    """
    console.print(
        f"[yellow]Quality report functionality requires database integration.[/yellow]\n"
        f"This command will be available after Wave 4 database schema is deployed.\n"
        f"Session ID: {session_id}"
    )


@quality.group(name="sources")
@click.pass_context
def sources_group(ctx: click.Context) -> None:
    """Source credibility management commands.

    Manage and track source credibility assessments.

    Examples:
        aris quality sources list
        aris quality sources verify <url>
    """
    pass


@sources_group.command(name="classify")
@click.argument("url")
@click.pass_context
def classify_source(ctx: click.Context, url: str) -> None:
    """Classify source credibility tier.

    Determines credibility tier (TIER_1 to TIER_4) based on URL domain patterns.

    \b
    Examples:
        aris quality sources classify https://arxiv.org/paper/12345

        aris quality sources classify https://medium.com/article

        aris quality sources classify https://example-blog.blogspot.com/post
    """
    tracker = SourceCredibilityTracker()

    tier = tracker.classify_source(url)
    score = tracker.calculate_credibility_score(tier)

    # Tier descriptions
    tier_descriptions = {
        "TIER_1": "Academic, peer-reviewed, official government (0.90-1.00)",
        "TIER_2": "Established media, expert sources, documentation (0.70-0.90)",
        "TIER_3": "Community resources, user-generated content (0.50-0.70)",
        "TIER_4": "Forums, unverified sources, personal blogs (0.30-0.50)",
    }

    if ctx.obj.get("json"):
        result = {
            "url": url,
            "tier": tier.value,
            "credibility_score": round(score, 3),
            "description": tier_descriptions.get(tier.value, "Unknown"),
        }
        console.print_json(data=result)
    else:
        console.print(f"\n[bold cyan]Source Classification[/bold cyan]\n")
        console.print(f"[bold]URL:[/bold] {url}")
        console.print(f"[bold]Tier:[/bold] {tier.value}")
        console.print(f"[bold]Credibility Score:[/bold] {score:.3f}")
        console.print(f"[bold]Description:[/bold] {tier_descriptions.get(tier.value, 'Unknown')}\n")


@sources_group.command(name="score")
@click.option(
    "--url",
    required=True,
    help="Source URL",
)
@click.option(
    "--verified",
    type=int,
    default=0,
    help="Number of times verified",
)
@click.pass_context
def score_source(ctx: click.Context, url: str, verified: int) -> None:
    """Calculate detailed credibility score for a source.

    Takes into account tier classification and verification history.

    \b
    Examples:
        aris quality sources score --url https://arxiv.org/paper/12345

        aris quality sources score \\
            --url https://example.edu/research \\
            --verified 3
    """
    tracker = SourceCredibilityTracker()

    tier = tracker.classify_source(url)
    base_score = tracker.calculate_credibility_score(tier, 0)
    boosted_score = tracker.calculate_credibility_score(tier, verified)

    if ctx.obj.get("json"):
        result = {
            "url": url,
            "tier": tier.value,
            "verification_count": verified,
            "base_score": round(base_score, 3),
            "verified_score": round(boosted_score, 3),
            "boost_from_verification": round(boosted_score - base_score, 3),
        }
        console.print_json(data=result)
    else:
        console.print(f"\n[bold cyan]Source Credibility Scoring[/bold cyan]\n")
        console.print(f"[bold]URL:[/bold] {url}")
        console.print(f"[bold]Tier:[/bold] {tier.value}")
        console.print(f"[bold]Verifications:[/bold] {verified}\n")
        console.print("[bold]Scoring:[/bold]")
        console.print(f"  Base Score:              {base_score:.3f}")
        console.print(f"  Verification Boost:      +{(boosted_score - base_score):.3f}")
        console.print(f"  Final Score:             {boosted_score:.3f}\n")


@quality.command(name="gate-config")
@click.option(
    "--level",
    type=click.Choice(["permissive", "standard", "strict"]),
    default="standard",
    help="Gate level to display configuration for",
)
@click.pass_context
def show_gate_config(ctx: click.Context, level: str) -> None:
    """Display validation gate configuration for a strictness level.

    Shows threshold values used for quality validation at different levels.

    \b
    Examples:
        aris quality gate-config

        aris quality gate-config --level strict

        aris quality gate-config --level permissive
    """
    validator = QualityValidator(gate_level=QualityGateLevel(level))
    thresholds = validator.thresholds

    if ctx.obj.get("json"):
        console.print_json(data=thresholds)
    else:
        # Create readable table
        table = Table(title=f"Quality Gate Configuration: {level.upper()}")
        table.add_column("Metric", style="cyan")
        table.add_column("Threshold", style="green")

        # Pre-execution thresholds
        table.add_row("[bold]Pre-Execution[/bold]", "")
        table.add_row("  Query Clarity Minimum", f"{thresholds['query_clarity_min']:.2f}")
        table.add_row("  Query Specificity Minimum", f"{thresholds['query_specificity_min']:.2f}")
        table.add_row("  Budget Sufficiency Minimum", f"{thresholds['budget_sufficiency_min']:.2f}")
        table.add_row("  Feasibility Minimum", f"{thresholds['feasibility_min']:.2f}")

        # Post-execution thresholds
        table.add_row("[bold]Post-Execution[/bold]", "")
        table.add_row("  Average Credibility Minimum", f"{thresholds['avg_credibility_min']:.2f}")
        table.add_row("  Source Diversity Minimum", str(thresholds["source_diversity_min"]))
        table.add_row("  Coverage Completeness Minimum", f"{thresholds['coverage_min']:.2f}")
        table.add_row("  Contradiction Tolerance", f"{thresholds['contradiction_tolerance']:.2f}")

        # Quality targets
        table.add_row("[bold]Targets[/bold]", "")
        table.add_row("  Confidence Target", f"{thresholds['confidence_target']:.2f}")

        console.print(table)
        console.print()
