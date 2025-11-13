"""Document display command for ARIS CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from aris.core.config import ConfigManager, ConfigurationError
from aris.storage.document_store import DocumentStore, DocumentStoreError

console = Console()


@click.command()
@click.argument("document_path", type=click.Path(exists=True))
@click.option("--metadata-only", is_flag=True, help="Show only metadata, not content")
@click.option("--raw", is_flag=True, help="Show raw markdown without rendering")
@click.pass_context
def show(
    ctx: click.Context,
    document_path: str,
    metadata_only: bool,
    raw: bool
) -> None:
    """Display research document.
    
    Shows document metadata and content with Rich formatting.
    Supports both absolute and relative paths.
    
    Examples:
        aris show research/ai/machine-learning.md
        aris show research/ai/machine-learning.md --metadata-only
        aris show research/ai/machine-learning.md --raw
    """
    formatter = ctx.obj["formatter"]
    
    try:
        # Get configuration
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        
        # Create document store
        store = DocumentStore(config)
        
        # Load document
        doc_path = Path(document_path)
        document = store.load_document(doc_path)
        
        # Extract metadata
        metadata = document.metadata
        
        if ctx.obj["json"]:
            # JSON output
            output = {
                "file_path": str(doc_path),
                "metadata": {
                    "title": metadata.title,
                    "confidence": metadata.confidence,
                    "topics": metadata.topics,
                    "created_at": metadata.created_at.isoformat(),
                    "updated_at": metadata.updated_at.isoformat(),
                }
            }
            if not metadata_only:
                output["content"] = document.content
            
            formatter.json_output(output)
        else:
            # Display metadata panel
            metadata_text = f"""
[bold]Title:[/bold] {metadata.title}
[bold]Confidence:[/bold] {metadata.confidence:.2%}
[bold]Topics:[/bold] {', '.join(metadata.topics) if metadata.topics else 'None'}
[bold]Created:[/bold] {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Updated:[/bold] {metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Path:[/bold] {doc_path}
"""
            
            console.print(Panel(
                metadata_text.strip(),
                title="📄 Document Metadata",
                border_style="cyan"
            ))
            
            # Display content if requested
            if not metadata_only:
                console.print()
                if raw:
                    console.print("[dim]" + "=" * 80 + "[/dim]")
                    console.print(document.content)
                    console.print("[dim]" + "=" * 80 + "[/dim]")
                else:
                    console.print(Markdown(document.content))
    
    except ConfigurationError as e:
        formatter.error(
            "Configuration not initialized",
            details={
                "error": str(e),
                "hint": "Run 'aris init' to initialize the project"
            }
        )
        sys.exit(1)
    
    except DocumentStoreError as e:
        formatter.error(
            f"Failed to load document: {e}",
            details={"path": document_path}
        )
        sys.exit(1)
    
    except Exception as e:
        formatter.error(
            f"Unexpected error: {e}",
            details={"error_type": type(e).__name__}
        )
        sys.exit(1)
