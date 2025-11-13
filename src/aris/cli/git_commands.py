"""Git operations commands for ARIS CLI."""

import sys

import click
from rich.console import Console
from rich.table import Table

from aris.core.config import ConfigManager, ConfigurationError
from aris.storage.git_manager import GitManager, GitOperationError

console = Console()


@click.group()
def git() -> None:
    """Git repository management commands.
    
    Commands for managing Git version control operations.
    """
    pass


@git.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show Git repository status.
    
    Example:
        aris git status
    """
    formatter = ctx.obj["formatter"]
    
    try:
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        
        git_manager = GitManager(config.research_dir)
        git_initialized = (config.research_dir / ".git").exists()
        
        if ctx.obj["json"]:
            formatter.json_output({
                "status": "initialized" if git_initialized else "not_initialized",
                "repository_path": str(config.research_dir)
            })
        else:
            table = Table(title="📚 Git Repository Status")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Status", "✅ Initialized" if git_initialized else "❌ Not initialized")
            table.add_row("Repository Path", str(config.research_dir))
            
            console.print(table)
    
    except ConfigurationError as e:
        formatter.error("Configuration not initialized", details={"hint": "Run 'aris init'"})
        sys.exit(1)
    except Exception as e:
        formatter.error(f"Failed to get Git status: {e}")
        sys.exit(1)


@git.command()
@click.argument("file_path", required=False)
@click.option("--limit", default=10, help="Number of commits to show")
@click.pass_context
def log(ctx: click.Context, file_path: str, limit: int) -> None:
    """Show Git commit history.
    
    Examples:
        aris git log
        aris git log --limit 20
        aris git log research/ai/machine-learning.md
    """
    formatter = ctx.obj["formatter"]
    
    if ctx.obj["json"]:
        formatter.json_output({
            "status": "not_implemented",
            "message": "Git log will show commit history",
            "file_path": file_path,
            "limit": limit
        })
    else:
        console.print("[yellow]⏳ Git log command coming soon[/yellow]")
        console.print(f"Will show last {limit} commits" + (f" for {file_path}" if file_path else ""))
