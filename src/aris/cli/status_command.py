"""System status command for ARIS CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from aris.core.config import ConfigManager, ConfigurationError
from aris.storage.database import DatabaseManager

console = Console()


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current ARIS system status.
    
    Displays information about:
    - Configuration status
    - Database status
    - Git repository status
    - API key configuration
    - Document and session counts
    
    Example:
        aris status
        aris status --json
    """
    formatter = ctx.obj["formatter"]
    
    try:
        # Get configuration
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        
        # Check configuration validity
        validation = config_manager.validate()
        config_status = "✅ Configured" if validation["valid"] else "⚠️ Incomplete"
        
        # Check database
        db_manager = DatabaseManager(config.database_path)
        db_initialized = db_manager.is_initialized()
        db_status = "✅ Ready" if db_initialized else "❌ Not initialized"
        
        # Get counts
        doc_count = db_manager.get_document_count() if db_initialized else 0
        session_count = db_manager.get_session_count() if db_initialized else 0
        
        # Check Git repository
        git_initialized = (config.research_dir / ".git").exists()
        git_status = "✅ Initialized" if git_initialized else "❌ Not initialized"
        
        # Check API keys
        api_keys_configured = validation["valid"]
        keys_status = "✅ Configured" if api_keys_configured else "⚠️ Missing keys"
        
        if ctx.obj["json"]:
            formatter.json_output({
                "status": "ok",
                "components": {
                    "configuration": {
                        "status": "configured" if validation["valid"] else "incomplete",
                        "project_root": str(config.project_root),
                        "research_dir": str(config.research_dir),
                        "database_path": str(config.database_path)
                    },
                    "database": {
                        "status": "ready" if db_initialized else "not_initialized",
                        "document_count": doc_count,
                        "session_count": session_count
                    },
                    "git": {
                        "status": "initialized" if git_initialized else "not_initialized",
                        "repository_path": str(config.research_dir)
                    },
                    "api_keys": {
                        "status": "configured" if api_keys_configured else "missing",
                        "errors": validation.get("errors", [])
                    }
                }
            })
        else:
            # Create status table
            table = Table(title="🔧 ARIS System Status", show_header=True)
            table.add_column("Component", style="cyan", width=20)
            table.add_column("Status", style="white", width=20)
            table.add_column("Details", style="dim", width=50)
            
            # Add rows
            table.add_row(
                "Configuration",
                config_status,
                f"Profile: {config_manager._profile.value}\nRoot: {config.project_root}"
            )
            
            table.add_row(
                "Database",
                db_status,
                f"Path: {config.database_path}\nDocuments: {doc_count} | Sessions: {session_count}"
            )
            
            table.add_row(
                "Git Repository",
                git_status,
                f"Path: {config.research_dir}"
            )
            
            table.add_row(
                "API Keys",
                keys_status,
                "Run 'aris config list-keys' for details"
            )
            
            console.print(table)
            
            # Show warnings if any
            if not validation["valid"]:
                console.print("\n[yellow]⚠️  Configuration issues:[/yellow]")
                for error in validation["errors"]:
                    console.print(f"  • {error}")
                console.print("\n[cyan]💡 Tip:[/cyan] Run 'aris config set-key <provider> <key>' to configure API keys")
            
            if not db_initialized:
                console.print("\n[yellow]⚠️  Database not initialized[/yellow]")
                console.print("[cyan]💡 Tip:[/cyan] Run 'aris init' to initialize the project")
    
    except ConfigurationError as e:
        formatter.error(
            "Configuration not initialized",
            details={
                "error": str(e),
                "hint": "Run 'aris init' to initialize the project"
            }
        )
        sys.exit(1)
    
    except Exception as e:
        formatter.error(
            f"Failed to get system status: {e}",
            details={"error_type": type(e).__name__}
        )
        sys.exit(1)
