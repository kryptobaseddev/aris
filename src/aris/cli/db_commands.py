"""Database management commands for ARIS CLI."""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from aris.core.config import ConfigManager, ConfigurationError
from aris.storage.database import DatabaseManager

console = Console()


@click.group()
def db() -> None:
    """Database management commands.

    Commands for managing ARIS database operations with SQLAlchemy and Alembic.
    """
    pass


@db.command()
@click.option("--echo", is_flag=True, help="Enable SQL query logging")
@click.pass_context
def init(ctx: click.Context, echo: bool) -> None:
    """Initialize database schema.

    Creates all tables using SQLAlchemy models.

    Example:
        aris db init
        aris db init --echo  # Show SQL queries
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        config = ConfigManager.get_instance().get_config()
        db_manager = DatabaseManager(config.database_path, echo=echo)

        if not formatter:
            console.print("\n[bold blue]Initializing ARIS database...[/bold blue]")
            console.print(f"Database path: {config.database_path}")

        # Initialize database
        db_manager.initialize_database()

        # Show table stats
        stats = db_manager.get_table_stats()

        if formatter:
            formatter.success("Database initialized", details={"tables": stats})
        else:
            console.print("\n[bold green]✓ Database initialized successfully![/bold green]")
            console.print("\n[bold]Tables created:[/bold]")
            for table_name, count in stats.items():
                console.print(f"  - {table_name}: {count} rows")

    except Exception as e:
        if formatter:
            formatter.error(f"Database initialization failed: {e}")
        else:
            console.print(f"\n[bold red]✗ Database initialization failed:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show database status and table statistics.

    Example:
        aris db status
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        config = ConfigManager.get_instance().get_config()
        db_path = config.database_path

        # Check if database exists
        if not db_path.exists():
            if formatter:
                formatter.error("Database not found", details={"path": str(db_path), "hint": "Run 'aris db init'"})
            else:
                console.print(f"\n[yellow]Database not found:[/yellow] {db_path}")
                console.print("[dim]Run 'aris db init' to create the database[/dim]")
            return

        db_manager = DatabaseManager(db_path)

        # Get table statistics
        stats = db_manager.get_table_stats()

        if formatter and ctx.obj.get("json"):
            formatter.json_output({
                "path": str(db_path),
                "file_size_kb": db_path.stat().st_size / 1024,
                "tables": stats
            })
        else:
            # Create status table
            table = Table(title="💾 ARIS Database Status", show_header=True)
            table.add_column("Table", style="cyan", no_wrap=True)
            table.add_column("Rows", justify="right", style="magenta")

            total_rows = 0
            for table_name, count in stats.items():
                table.add_row(table_name, str(count))
                total_rows += count

            table.add_section()
            table.add_row("[bold]Total[/bold]", f"[bold]{total_rows}[/bold]")

            console.print()
            console.print(table)
            console.print(f"\n[dim]Database file:[/dim] {db_path}")
            console.print(f"[dim]File size:[/dim] {db_path.stat().st_size / 1024:.2f} KB")

    except ConfigurationError:
        if formatter:
            formatter.error("Configuration not initialized", details={"hint": "Run 'aris init'"})
        else:
            console.print("[red]Configuration not initialized. Run 'aris init'[/red]")
        sys.exit(1)
    except Exception as e:
        if formatter:
            formatter.error(f"Failed to get database status: {e}")
        else:
            console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def reset(ctx: click.Context, confirm: bool) -> None:
    """Reset database (drop all tables and recreate).

    WARNING: This will delete all research data!

    Example:
        aris db reset --confirm
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    if not confirm and not click.confirm("⚠️  Delete all database data?"):
        console.print("Cancelled.")
        return

    try:
        config = ConfigManager.get_instance().get_config()
        db_manager = DatabaseManager(config.database_path)

        if not formatter:
            console.print("\n[bold yellow]Resetting database...[/bold yellow]")

        # Drop all tables
        db_manager.drop_all_tables()
        if not formatter:
            console.print("[dim]All tables dropped[/dim]")

        # Recreate tables
        db_manager.create_all_tables()
        if not formatter:
            console.print("[dim]All tables recreated[/dim]")

        if formatter:
            formatter.success("Database reset complete")
        else:
            console.print("\n[bold green]✓ Database reset successfully![/bold green]")

    except Exception as e:
        if formatter:
            formatter.error(f"Failed to reset database: {e}")
        else:
            console.print(f"\n[bold red]✗ Database reset failed:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.option("--output", "-o", type=click.Path(), help="Backup file path")
@click.pass_context
def backup(ctx: click.Context, output: str) -> None:
    """Create a backup of the database.

    Example:
        aris db backup
        aris db backup -o /path/to/backup.db
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        config = ConfigManager.get_instance().get_config()
        db_path = config.database_path

        if not db_path.exists():
            if formatter:
                formatter.error("Database not found")
            else:
                console.print("\n[yellow]Database not found. Nothing to backup.[/yellow]")
            return

        # Generate backup path if not provided
        if output:
            backup_path = Path(output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.parent / f"metadata_backup_{timestamp}.db"

        db_manager = DatabaseManager(db_path)

        if not formatter:
            console.print(f"\n[bold blue]Creating database backup...[/bold blue]")
            console.print(f"Source: {db_path}")
            console.print(f"Destination: {backup_path}")

        db_manager.backup_database(backup_path)

        if formatter:
            formatter.success("Backup created", details={"path": str(backup_path), "size_kb": backup_path.stat().st_size / 1024})
        else:
            console.print(f"\n[bold green]✓ Backup created successfully![/bold green]")
            console.print(f"Backup size: {backup_path.stat().st_size / 1024:.2f} KB")

    except Exception as e:
        if formatter:
            formatter.error(f"Backup failed: {e}")
        else:
            console.print(f"\n[bold red]✗ Backup failed:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.pass_context
def migrate(ctx: click.Context) -> None:
    """Run pending database migrations.

    Example:
        aris db migrate
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        from alembic import command
        from alembic.config import Config

        if not formatter:
            console.print("\n[bold blue]Running database migrations...[/bold blue]")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Run migrations
        command.upgrade(alembic_cfg, "head")

        if formatter:
            formatter.success("Migrations applied")
        else:
            console.print("\n[bold green]✓ Migrations applied successfully![/bold green]")

    except ImportError:
        if formatter:
            formatter.error("Alembic not installed", details={"hint": "Install with: poetry install"})
        else:
            console.print("\n[bold red]✗ Alembic not installed.[/bold red]")
            console.print("[dim]Install with: poetry install[/dim]")
        sys.exit(1)
    except Exception as e:
        if formatter:
            formatter.error(f"Migration failed: {e}")
        else:
            console.print(f"\n[bold red]✗ Migration failed:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.argument("message")
@click.option("--autogenerate", is_flag=True, help="Autogenerate migration from model changes")
@click.pass_context
def revision(ctx: click.Context, message: str, autogenerate: bool) -> None:
    """Create a new database migration.

    MESSAGE: Description of the migration

    Example:
        aris db revision "add user table"
        aris db revision "update schema" --autogenerate
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        from alembic import command
        from alembic.config import Config

        if not formatter:
            console.print(f"\n[bold blue]Creating migration: {message}[/bold blue]")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Create revision
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=autogenerate
        )

        if formatter:
            formatter.success("Migration created", details={"message": message})
        else:
            console.print("\n[bold green]✓ Migration created successfully![/bold green]")
            console.print("[dim]Edit the migration file in alembic/versions/[/dim]")
            console.print("[dim]Then run 'aris db migrate' to apply[/dim]")

    except ImportError:
        if formatter:
            formatter.error("Alembic not installed", details={"hint": "Install with: poetry install"})
        else:
            console.print("\n[bold red]✗ Alembic not installed.[/bold red]")
            console.print("[dim]Install with: poetry install[/dim]")
        sys.exit(1)
    except Exception as e:
        if formatter:
            formatter.error(f"Revision creation failed: {e}")
        else:
            console.print(f"\n[bold red]✗ Revision creation failed:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed migration history")
@click.pass_context
def history(ctx: click.Context, verbose: bool) -> None:
    """Show database migration history.

    Example:
        aris db history
        aris db history -v
    """
    try:
        from alembic import command
        from alembic.config import Config

        console.print("\n[bold blue]Migration History:[/bold blue]\n")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Show history
        command.history(alembic_cfg, verbose=verbose)

    except ImportError:
        console.print("\n[bold red]✗ Alembic not installed.[/bold red]")
        console.print("[dim]Install with: poetry install[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        sys.exit(1)


@db.command()
@click.argument("revision", default="-1")
@click.pass_context
def downgrade(ctx: click.Context, revision: str) -> None:
    """Downgrade database to a previous migration.

    REVISION: Target revision (default: -1 for previous migration)

    Example:
        aris db downgrade
        aris db downgrade -1
        aris db downgrade <revision_id>
    """
    formatter = ctx.obj.get("formatter") if ctx.obj else None

    try:
        from alembic import command
        from alembic.config import Config

        if not formatter:
            console.print(f"\n[bold yellow]Downgrading database to: {revision}[/bold yellow]")

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Run downgrade
        command.downgrade(alembic_cfg, revision)

        if formatter:
            formatter.success("Downgrade completed", details={"revision": revision})
        else:
            console.print("\n[bold green]✓ Downgrade completed successfully![/bold green]")

    except ImportError:
        if formatter:
            formatter.error("Alembic not installed", details={"hint": "Install with: poetry install"})
        else:
            console.print("\n[bold red]✗ Alembic not installed.[/bold red]")
            console.print("[dim]Install with: poetry install[/dim]")
        sys.exit(1)
    except Exception as e:
        if formatter:
            formatter.error(f"Downgrade failed: {e}")
        else:
            console.print(f"\n[bold red]✗ Downgrade failed:[/bold red] {e}")
        sys.exit(1)
