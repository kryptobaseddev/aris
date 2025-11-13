"""Main CLI entry point for ARIS.

Autonomous Research Intelligence System
Prevents document proliferation through semantic deduplication.
"""

import sys
from pathlib import Path

import click
from rich.console import Console

from aris.utils.output import OutputFormatter

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="aris")
@click.option("--json", is_flag=True, help="Output in JSON format (LLM-friendly)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Path to custom config file",
)
@click.pass_context
def cli(ctx: click.Context, json: bool, verbose: bool, config_file: str) -> None:
    """ARIS - Autonomous Research Intelligence System
    
    Prevents document proliferation through semantic deduplication.
    
    ARIS intelligently determines whether to UPDATE existing documents
    or CREATE new ones based on semantic similarity (>0.85 = UPDATE mode).
    
    Features:
    - Semantic deduplication with vector search
    - Git-based version control
    - Multi-model validation for quality assurance
    - Cost tracking and optimization
    - Session persistence across runs
    
    Examples:
        aris init --name "My Research Project"
        aris status
        aris show research/ai/machine-learning.md
        aris config show
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json
    ctx.obj["verbose"] = verbose
    ctx.obj["config_file"] = config_file
    ctx.obj["formatter"] = OutputFormatter(json_mode=json, verbose=verbose)


# Import command modules
from aris.cli.config_commands import config_group
from aris.cli.init_command import init
from aris.cli.status_command import status
from aris.cli.show_command import show
from aris.cli.db_commands import db
from aris.cli.git_commands import git
from aris.cli.research_commands import research
from aris.cli.organize_commands import organize
from aris.cli.session_commands import session
from aris.cli.cost_commands import cost_group
from aris.cli.quality_commands import quality

# Register command groups
cli.add_command(config_group, name="config")
cli.add_command(init)
cli.add_command(status)
cli.add_command(show)
cli.add_command(db)
cli.add_command(git)
cli.add_command(research)
cli.add_command(organize)
cli.add_command(session)
cli.add_command(cost_group, name="cost")
cli.add_command(quality)


def main() -> None:
    """Entry point for CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
