"""Project initialization command for ARIS CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console

from aris.core.config import ConfigManager, ConfigProfile, ConfigurationError
from aris.storage.database import DatabaseManager
from aris.storage.git_manager import GitManager

console = Console()


@click.command()
@click.option("--name", prompt="Project name", help="Name of research project")
@click.option(
    "--profile",
    type=click.Choice(["development", "production", "testing"]),
    default="development",
    help="Configuration profile",
)
@click.option("--force", is_flag=True, help="Force reinitialize existing project")
@click.pass_context
def init(ctx: click.Context, name: str, profile: str, force: bool) -> None:
    """Initialize new ARIS research project.
    
    Creates necessary directories, initializes database, and sets up
    Git repository for version control.
    
    Examples:
        aris init --name "AI Research"
        aris init --name "Market Analysis" --profile production
        aris init --name "Testing" --profile testing --force
    """
    formatter = ctx.obj["formatter"]
    
    try:
        # Get configuration manager
        config_manager = ConfigManager.get_instance()
        profile_enum = ConfigProfile(profile)
        
        # Check if already initialized
        if not force:
            try:
                config_manager.get_config()
                formatter.warning(
                    "Project already initialized",
                    details={"hint": "Use --force to reinitialize"}
                )
                return
            except ConfigurationError:
                pass  # Not initialized, continue
        
        # Load configuration
        config = config_manager.load(profile=profile_enum)
        
        # Create directories
        formatter.info("Creating project directories...")
        config.research_dir.mkdir(parents=True, exist_ok=True)
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        formatter.info("Initializing database...")
        db_manager = DatabaseManager(config.database_path)
        db_manager.initialize()
        
        # Initialize Git repository
        formatter.info("Initializing Git repository...")
        git_manager = GitManager(config.research_dir)
        
        # Success message
        formatter.success(f"Initialized ARIS project: {name}")
        
        if not ctx.obj["json"]:
            console.print(f"\n[cyan]📁 Research directory:[/cyan] {config.research_dir}")
            console.print(f"[cyan]💾 Database:[/cyan] {config.database_path}")
            console.print(f"[cyan]🔧 Profile:[/cyan] {profile}")
            
            # Check for API keys
            validation = config_manager.validate()
            if not validation["valid"]:
                console.print("\n[yellow]⚠️  Configuration incomplete:[/yellow]")
                for error in validation["errors"]:
                    console.print(f"  • {error}")
                console.print("\n[cyan]Set API keys using:[/cyan] aris config set-key <provider> <key>")
        else:
            formatter.json_output({
                "status": "success",
                "project": name,
                "profile": profile,
                "research_dir": str(config.research_dir),
                "database_path": str(config.database_path),
                "config_valid": validation["valid"],
                "missing_keys": validation.get("errors", [])
            })
    
    except Exception as e:
        formatter.error(
            f"Failed to initialize project: {e}",
            details={"error_type": type(e).__name__}
        )
        sys.exit(1)
