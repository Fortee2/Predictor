#!/usr/bin/env python3
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from enhanced_cli.main import EnhancedCLI

console = Console()

def main():
    """Main launcher function."""

    # Display welcome message
    console.print(
        Panel(
            "[bold blue]Portfolio & Stock Management System[/bold blue]",
            subtitle="v1.0.0",
            box=box.DOUBLE,
        )
    )

    # Use enhanced GUI-like interface
    console.print("[green]Starting enhanced user interface...[/green]")


    cli = EnhancedCLI()
    cli.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
