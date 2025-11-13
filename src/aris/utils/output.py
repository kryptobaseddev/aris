"""Output formatting utilities for ARIS CLI.

Provides dual-mode output:
- Human-friendly: Rich terminal formatting with colors, tables, progress bars
- LLM-friendly: Structured JSON for machine parsing
"""

import json
import sys
from typing import Any, Dict, Optional, Union

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown


class OutputFormatter:
    """Dual-mode output formatter for CLI.
    
    Supports two modes:
    - Rich mode: Beautiful terminal output with colors and formatting
    - JSON mode: Structured data for LLM/machine consumption
    
    Example:
        formatter = OutputFormatter(json_mode=False)
        formatter.print("Hello, World!", title="Greeting")
        formatter.success("Operation completed")
        formatter.error("Something went wrong", details={"code": 500})
    """
    
    def __init__(self, json_mode: bool = False, verbose: bool = False):
        """Initialize output formatter.
        
        Args:
            json_mode: Enable JSON output mode
            verbose: Enable verbose output
        """
        self.json_mode = json_mode
        self.verbose = verbose
        self.console = Console()
        self._json_buffer: list[Dict[str, Any]] = []
    
    def print(self, data: Any, title: Optional[str] = None, style: Optional[str] = None) -> None:
        """Print formatted output.
        
        Args:
            data: Data to print
            title: Optional title
            style: Rich style (ignored in JSON mode)
        """
        if self.json_mode:
            output = {"data": data}
            if title:
                output["title"] = title
            self._output_json(output)
        else:
            if title:
                self.console.print(f"[bold cyan]{title}[/bold cyan]")
            if style:
                self.console.print(data, style=style)
            else:
                self.console.print(data)
    
    def success(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Print success message.
        
        Args:
            message: Success message
            details: Optional additional details
        """
        if self.json_mode:
            output = {"status": "success", "message": message}
            if details:
                output["details"] = details
            self._output_json(output)
        else:
            self.console.print(f"[green]✅ {message}[/green]")
            if details and self.verbose:
                self.console.print_json(data=details)
    
    def error(self, message: str, details: Optional[Dict[str, Any]] = None, exit_code: int = 1) -> None:
        """Print error message.
        
        Args:
            message: Error message
            details: Optional error details
            exit_code: Exit code (0 = don't exit)
        """
        if self.json_mode:
            output = {"status": "error", "message": message, "type": "error"}
            if details:
                output["details"] = details
            self._output_json(output)
        else:
            self.console.print(f"[red]❌ Error:[/red] {message}")
            if details:
                if self.verbose:
                    self.console.print_json(data=details)
                else:
                    for key, value in details.items():
                        self.console.print(f"  {key}: {value}")
        
        if exit_code > 0:
            sys.exit(exit_code)
    
    def warning(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Print warning message.
        
        Args:
            message: Warning message
            details: Optional warning details
        """
        if self.json_mode:
            output = {"status": "warning", "message": message}
            if details:
                output["details"] = details
            self._output_json(output)
        else:
            self.console.print(f"[yellow]⚠️  Warning:[/yellow] {message}")
            if details and self.verbose:
                self.console.print_json(data=details)
    
    def info(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Print info message.
        
        Args:
            message: Info message
            details: Optional info details
        """
        if self.json_mode:
            output = {"status": "info", "message": message}
            if details:
                output["details"] = details
            self._output_json(output)
        else:
            self.console.print(f"[cyan]ℹ️  {message}[/cyan]")
            if details and self.verbose:
                self.console.print_json(data=details)
    
    def table(self, data: list[Dict[str, Any]], title: Optional[str] = None) -> None:
        """Print data as table.
        
        Args:
            data: List of dictionaries to display
            title: Optional table title
        """
        if self.json_mode:
            output = {"type": "table", "data": data}
            if title:
                output["title"] = title
            self._output_json(output)
        else:
            if not data:
                self.console.print("[yellow]No data to display[/yellow]")
                return
            
            table = Table(title=title, show_header=True)
            
            # Add columns from first row
            for key in data[0].keys():
                table.add_column(str(key).title(), style="cyan")
            
            # Add rows
            for row in data:
                table.add_row(*[str(v) for v in row.values()])
            
            self.console.print(table)
    
    def panel(self, content: str, title: Optional[str] = None) -> None:
        """Print content in a panel.
        
        Args:
            content: Panel content
            title: Optional panel title
        """
        if self.json_mode:
            output = {"type": "panel", "content": content}
            if title:
                output["title"] = title
            self._output_json(output)
        else:
            self.console.print(Panel(content, title=title))
    
    def markdown(self, content: str) -> None:
        """Print markdown content.
        
        Args:
            content: Markdown content
        """
        if self.json_mode:
            self._output_json({"type": "markdown", "content": content})
        else:
            self.console.print(Markdown(content))
    
    def json_output(self, data: Dict[str, Any]) -> None:
        """Output structured JSON data.
        
        Args:
            data: Dictionary to output as JSON
        """
        print(json.dumps(data, indent=2, default=str))
    
    def _output_json(self, data: Dict[str, Any]) -> None:
        """Internal method to output JSON.
        
        Args:
            data: Data to output
        """
        print(json.dumps(data, indent=2, default=str))
