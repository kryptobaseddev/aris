"""Configuration management CLI commands for ARIS.

Provides commands for:
- Setting/getting API keys via keyring
- Viewing configuration
- Validating configuration
- Testing API keys
- Initializing configuration
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aris.core.config import ConfigManager, ConfigProfile, ConfigurationError
from aris.core.secrets import KeyringNotAvailableError, SecureKeyManager

console = Console()


@click.group(name="config")
def config_group() -> None:
    """Manage ARIS configuration and API keys."""
    pass


@config_group.command(name="init")
@click.option(
    "--profile",
    type=click.Choice(["development", "production", "testing"]),
    default="development",
    help="Configuration profile to initialize",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinitialization even if config exists",
)
def init_config(profile: str, force: bool) -> None:
    """Initialize ARIS configuration.

    Creates necessary directories and config files.

    Example:
        aris config init
        aris config init --profile production
    """
    try:
        config_manager = ConfigManager.get_instance()
        profile_enum = ConfigProfile(profile)

        # Check if already initialized
        if not force:
            try:
                config_manager.get_config()
                console.print("[yellow]Configuration already initialized.[/yellow]")
                console.print("Use --force to reinitialize.")
                return
            except ConfigurationError:
                pass  # Not initialized, continue

        # Load configuration
        config = config_manager.load(profile=profile_enum)

        console.print(f"[green]✓[/green] Initialized ARIS configuration")
        console.print(f"Profile: {profile}")
        console.print(f"Project root: {config.project_root}")
        console.print(f"Research directory: {config.research_dir}")
        console.print(f"Database: {config.database_path}")

        # Check for API keys
        validation = config_manager.validate()
        if not validation["valid"]:
            console.print("\n[yellow]⚠ Configuration incomplete:[/yellow]")
            for error in validation["errors"]:
                console.print(f"  • {error}")
            console.print("\nSet API keys using: aris config set-key <provider> <key>")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize configuration: {e}")
        sys.exit(1)


@config_group.command(name="show")
@click.option(
    "--secure/--no-secure",
    default=True,
    help="Mask API keys in output (default: masked)",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def show_config(secure: bool, format: str) -> None:
    """Display current configuration.

    Example:
        aris config show
        aris config show --no-secure  # Show full API keys
        aris config show --format json
    """
    try:
        config_manager = ConfigManager.get_instance()
        config_manager.load()
        summary = config_manager.get_config_summary(mask_secrets=secure)

        if format == "json":
            import json

            console.print_json(json.dumps(summary, indent=2))
            return

        # Table format
        console.print(Panel("[bold]ARIS Configuration[/bold]", expand=False))
        console.print(f"Profile: [cyan]{summary['profile']}[/cyan]\n")

        # Paths table
        paths_table = Table(title="Paths", show_header=True)
        paths_table.add_column("Setting", style="cyan")
        paths_table.add_column("Value", style="white")

        paths_table.add_row("Project Root", summary["project_root"])
        paths_table.add_row("Research Dir", summary["research_dir"])
        paths_table.add_row("Database", summary["database_path"])

        console.print(paths_table)
        console.print()

        # API Keys table
        keys_table = Table(title="API Keys", show_header=True)
        keys_table.add_column("Provider", style="cyan")
        keys_table.add_column("Status", style="white")

        for provider, key_value in summary["api_keys"].items():
            status = (
                f"[green]{key_value}[/green]"
                if key_value != "Not set"
                else "[red]Not set[/red]"
            )
            keys_table.add_row(provider.capitalize(), status)

        console.print(keys_table)
        console.print()

        # Budgets table
        budgets_table = Table(title="Budgets (USD)", show_header=True)
        budgets_table.add_column("Type", style="cyan")
        budgets_table.add_column("Amount", style="white")

        budgets_table.add_row("Quick Research", f"${summary['budgets']['quick']:.2f}")
        budgets_table.add_row(
            "Standard Research", f"${summary['budgets']['standard']:.2f}"
        )
        budgets_table.add_row("Deep Research", f"${summary['budgets']['deep']:.2f}")
        budgets_table.add_row(
            "Monthly Limit", f"${summary['budgets']['monthly_limit']:.2f}"
        )

        console.print(budgets_table)
        console.print()

        # Research parameters table
        research_table = Table(title="Research Parameters", show_header=True)
        research_table.add_column("Parameter", style="cyan")
        research_table.add_column("Value", style="white")

        research_table.add_row("Max Hops", str(summary["research"]["max_hops"]))
        research_table.add_row(
            "Similarity Threshold",
            f"{summary['research']['similarity_threshold']:.2f}",
        )
        research_table.add_row(
            "Confidence Target", f"{summary['research']['confidence_target']:.2f}"
        )

        console.print(research_table)

    except ConfigurationError as e:
        console.print(f"[red]✗[/red] {e}")
        console.print("\nRun: aris config init")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to show configuration: {e}")
        sys.exit(1)


@config_group.command(name="validate")
def validate_config() -> None:
    """Validate configuration completeness.

    Checks that all required API keys are set and configuration is valid.

    Example:
        aris config validate
    """
    try:
        config_manager = ConfigManager.get_instance()
        config_manager.load()
        validation = config_manager.validate()

        if validation["valid"]:
            console.print("[green]✓[/green] Configuration is valid!")
        else:
            console.print("[red]✗[/red] Configuration validation failed:\n")

            if validation["errors"]:
                console.print("[red]Errors:[/red]")
                for error in validation["errors"]:
                    console.print(f"  • {error}")

        if validation["warnings"]:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in validation["warnings"]:
                console.print(f"  • {warning}")

        if not validation["valid"]:
            sys.exit(1)

    except ConfigurationError as e:
        console.print(f"[red]✗[/red] {e}")
        console.print("\nRun: aris config init")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to validate configuration: {e}")
        sys.exit(1)


@config_group.command(name="set-key")
@click.argument("provider", type=click.Choice(["tavily", "anthropic", "openai", "google"]))
@click.argument("api_key", required=False)
@click.option(
    "--prompt",
    is_flag=True,
    help="Prompt for API key interactively (secure, no echo)",
)
def set_api_key(provider: str, api_key: Optional[str], prompt: bool) -> None:
    """Set API key for a provider.

    Stores the key securely in system keyring.

    Examples:
        aris config set-key tavily tvly-xxxxx
        aris config set-key anthropic --prompt  # Interactive, secure
    """
    try:
        # Get API key
        if prompt:
            api_key = click.prompt(
                f"Enter API key for {provider}", hide_input=True, type=str
            )
        elif api_key is None:
            console.print("[red]✗[/red] API key required. Use --prompt for secure input.")
            sys.exit(1)

        # Store key
        config_manager = ConfigManager.get_instance()
        try:
            config_manager.load()
        except ConfigurationError:
            # Config not initialized yet, initialize it
            config_manager.load(profile=ConfigProfile.DEVELOPMENT)

        config_manager.set_api_key(provider, api_key, persist=True)

        console.print(
            f"[green]✓[/green] API key for [cyan]{provider}[/cyan] stored securely in keyring"
        )

        # Validate after setting
        validation = config_manager.validate()
        if validation["valid"]:
            console.print("[green]✓[/green] All required API keys are now configured!")

    except KeyringNotAvailableError as e:
        console.print(f"[red]✗[/red] Keyring not available: {e}")
        console.print("\nFallback: Set ARIS_<PROVIDER>_API_KEY in .env file")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to set API key: {e}")
        sys.exit(1)


@config_group.command(name="get-key")
@click.argument("provider", type=click.Choice(["tavily", "anthropic", "openai", "google"]))
@click.option(
    "--show/--mask",
    default=False,
    help="Show full key or mask it (default: masked)",
)
def get_api_key(provider: str, show: bool) -> None:
    """Get API key for a provider.

    Example:
        aris config get-key tavily
        aris config get-key anthropic --show  # Show full key
    """
    try:
        config_manager = ConfigManager.get_instance()
        config_manager.load()

        api_key = config_manager.get_api_key(provider)

        if api_key is None:
            console.print(f"[yellow]API key for {provider} not set[/yellow]")
            console.print(f"\nSet it using: aris config set-key {provider} <key>")
            sys.exit(1)

        if show:
            console.print(f"{provider}: {api_key}")
        else:
            masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "****"
            console.print(f"{provider}: {masked}")
            console.print("\nUse --show to display full key")

    except ConfigurationError as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to get API key: {e}")
        sys.exit(1)


@config_group.command(name="delete-key")
@click.argument("provider", type=click.Choice(["tavily", "anthropic", "openai", "google"]))
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete_api_key(provider: str, confirm: bool) -> None:
    """Delete API key for a provider from keyring.

    Example:
        aris config delete-key tavily
        aris config delete-key anthropic --confirm
    """
    try:
        if not confirm:
            if not click.confirm(f"Delete API key for {provider}?"):
                console.print("Cancelled.")
                return

        config_manager = ConfigManager.get_instance()
        config_manager.load()
        config_manager.delete_api_key(provider)

        console.print(f"[green]✓[/green] API key for {provider} deleted")

    except ConfigurationError as e:
        console.print(f"[red]✗[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to delete API key: {e}")
        sys.exit(1)


@config_group.command(name="list-keys")
def list_api_keys() -> None:
    """List all configured API key providers.

    Example:
        aris config list-keys
    """
    try:
        secrets_manager = SecureKeyManager()
        providers = secrets_manager.list_providers()

        if not providers:
            console.print("[yellow]No API keys configured[/yellow]")
            console.print("\nSet keys using: aris config set-key <provider> <key>")
            return

        console.print("[bold]Configured API Key Providers:[/bold]\n")
        for provider in providers:
            console.print(f"  [green]✓[/green] {provider}")

        console.print(f"\n[cyan]Total: {len(providers)} provider(s)[/cyan]")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list API keys: {e}")
        sys.exit(1)


@config_group.command(name="test-keys")
@click.option(
    "--provider",
    type=click.Choice(["tavily", "anthropic", "openai", "google"]),
    help="Test specific provider only",
)
def test_api_keys(provider: Optional[str]) -> None:
    """Test API keys by making test requests.

    Example:
        aris config test-keys
        aris config test-keys --provider tavily
    """
    console.print("[yellow]Note: API key testing not yet implemented[/yellow]")
    console.print("This will validate keys by making test API calls.")
    console.print("Coming in Phase 2 (Research Workflow implementation)")


@config_group.command(name="reset")
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--keep-keys",
    is_flag=True,
    help="Keep API keys in keyring (only reset config)",
)
def reset_config(confirm: bool, keep_keys: bool) -> None:
    """Reset ARIS configuration to defaults.

    WARNING: This will delete configuration and optionally API keys.

    Example:
        aris config reset --keep-keys  # Reset config but keep API keys
        aris config reset --confirm     # Reset everything
    """
    try:
        if not confirm:
            console.print("[red]⚠ WARNING: This will reset your configuration![/red]")
            if not keep_keys:
                console.print("[red]This will also delete all API keys from keyring![/red]")
            if not click.confirm("Are you sure?"):
                console.print("Cancelled.")
                return

        # Reset config manager
        ConfigManager.reset_instance()
        console.print("[green]✓[/green] Configuration reset")

        # Delete API keys if requested
        if not keep_keys:
            deleted_count = SecureKeyManager.clear_all_keys()
            console.print(f"[green]✓[/green] Deleted {deleted_count} API key(s)")

        console.print("\nRun 'aris config init' to reinitialize")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to reset configuration: {e}")
        sys.exit(1)
