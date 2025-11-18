"""
Reusable UI components for the Enhanced CLI.

This module provides standardized UI components and layout utilities
to ensure a consistent look and feel across the application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table


class UIComponents:
    """Factory class for creating consistent UI components."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the UI components factory.

        Args:
            console: The Rich Console instance to use for output
        """
        self.console = console or Console()

    def header(self, title: str, subtitle: Optional[str] = None) -> Panel:
        """
        Create a header panel with title and optional subtitle.

        Args:
            title: The main title text
            subtitle: Optional subtitle text

        Returns:
            A Rich Panel instance
        """
        return Panel(f"[bold blue]{title}[/bold blue]", subtitle=subtitle, box=box.DOUBLE)

    def section_header(self, title: str) -> Panel:
        """
        Create a section header panel.

        Args:
            title: The section title text

        Returns:
            A Rich Panel instance
        """
        return Panel(f"[bold]{title}[/bold]", box=box.ROUNDED)

    def data_table(self, title: str, columns: List[Dict[str, Any]], rows: List[List[str]]) -> Table:
        """
        Create a data table with standardized formatting.

        Args:
            title: Table title
            columns: List of column definitions, each with 'header' and optional 'style', 'justify', etc.
            rows: List of rows, each row is a list of cell values

        Returns:
            A Rich Table instance
        """
        table = Table(title=title, box=box.ROUNDED)

        # Add columns
        for col in columns:
            table.add_column(
                col["header"],
                style=col.get("style"),
                justify=col.get("justify"),
                width=col.get("width"),
                no_wrap=col.get("no_wrap", False),
            )

        # Add rows
        for row in rows:
            table.add_row(*row)

        return table

    def menu(self, title: str, options: Dict[str, str]) -> str:
        """
        Display a menu and get user selection.

        Args:
            title: Menu title
            options: Dictionary of option IDs to option descriptions

        Returns:
            Selected option ID
        """
        self.console.print(f"\n[bold]{title}:[/bold]")
        for key, desc in options.items():
            self.console.print(f"[{key}] {desc}")

        # Get valid choices
        valid_choices = list(options.keys())
        default = valid_choices[0] if valid_choices else None

        return Prompt.ask("Select an option", choices=valid_choices, default=default)

    def input_form(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Display an input form to collect multiple values.

        Args:
            fields: List of field definitions, each with 'name', 'prompt', optional 'default', 'type', etc.

        Returns:
            Dictionary of field names to entered values
        """
        result = {}

        for field in fields:
            name = field["name"]
            prompt = field["prompt"]
            field_type = field.get("type", str)
            default = field.get("default")
            choices = field.get("choices")

            if field_type == bool:
                result[name] = Confirm.ask(prompt, default=bool(default) if default is not None else None)
            elif choices:
                result[name] = Prompt.ask(prompt, choices=choices, default=default)
            else:
                value = Prompt.ask(prompt, default=str(default) if default is not None else None)

                # Convert value to expected type
                if field_type == int:
                    result[name] = int(value)
                elif field_type == float:
                    result[name] = float(value)
                elif field_type == datetime:
                    try:
                        result[name] = datetime.strptime(value, field.get("format", "%Y-%m-%d"))
                    except ValueError:
                        self.console.print("[bold red]Invalid date format. Using default.[/bold red]")
                        result[name] = default or datetime.now()
                else:
                    result[name] = value

        return result

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """
        Ask for confirmation before an action.

        Args:
            message: Confirmation message
            default: Default response (True for yes, False for no)

        Returns:
            True if confirmed, False otherwise
        """
        return Confirm.ask(message, default=default)

    def progress(self, message: str) -> Progress:
        """
        Create a progress indicator with standard formatting.

        Args:
            message: Message to display during progress operation

        Returns:
            A Rich Progress instance
        """
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{message}[/bold blue]"),
            transient=True,
        )

    def status_message(self, message: str, level: str = "info") -> None:
        """
        Display a status message with appropriate formatting.

        Args:
            message: The status message
            level: Message level ('info', 'success', 'warning', 'error')
        """
        if level == "success":
            self.console.print(f"[bold green]✓ {message}[/bold green]")
        elif level == "warning":
            self.console.print(f"[bold yellow]! {message}[/bold yellow]")
        elif level == "error":
            self.console.print(f"[bold red]✗ {message}[/bold red]")
        else:  # info
            self.console.print(message)

    def format_cash(self, amount: float, show_positive: bool = False) -> str:
        """
        Format a cash amount with color based on positive/negative value.

        Args:
            amount: Cash amount
            show_positive: Whether to include '+' for positive amounts

        Returns:
            Formatted string
        """
        if amount > 0:
            prefix = "+" if show_positive else ""
            return f"[green]{prefix}${amount:.2f}[/green]"
        elif amount < 0:
            return f"[red]-${abs(amount):.2f}[/red]"
        else:
            return f"${amount:.2f}"

    def format_percent(self, value: float) -> str:
        """
        Format a percentage value with color based on positive/negative value.

        Args:
            value: Percentage value

        Returns:
            Formatted string
        """
        if value > 0:
            return f"[green]+{value:.2f}%[/green]"
        elif value < 0:
            return f"[red]{value:.2f}%[/red]"
        else:
            return f"{value:.2f}%"

    def wait_for_user(self) -> None:
        """Prompt user to press Enter to continue."""
        Prompt.ask("[bold]Press Enter to continue[/bold]")


# Global UI components instance for shared use
ui = UIComponents(Console())
