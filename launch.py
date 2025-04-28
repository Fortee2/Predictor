#!/usr/bin/env python3
import sys
import os
import argparse
import importlib.util
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ["rich", "mysql-connector-python", "python-dotenv"]
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package.replace('-', '_')) is None:
            missing_packages.append(package)
    
    if missing_packages:
        console.print("[bold red]Missing required packages:[/bold red]")
        for package in missing_packages:
            console.print(f"- {package}")
        console.print("\n[bold yellow]Please install the missing packages using:[/bold yellow]")
        console.print(f"pip install {' '.join(missing_packages)}")
        return False
    return True

def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(description="Portfolio & Stock Management System")
    parser.add_argument("--cli", action="store_true", help="Use traditional CLI interface")
    parser.add_argument('args', nargs=argparse.REMAINDER, help="Arguments to pass to the CLI")
    
    args = parser.parse_args()
    
    # Display welcome message
    console.print(Panel(
        "[bold blue]Portfolio & Stock Management System[/bold blue]",
        subtitle="v1.0.0", 
        box=box.DOUBLE
    ))
    
    if args.cli:
        # Use traditional command-line interface
        console.print("[yellow]Starting traditional command-line interface...[/yellow]")
        from portfolio_cli import main as cli_main
        return cli_main()
    else:
        # Use enhanced GUI-like interface
        console.print("[green]Starting enhanced user interface...[/green]")
        try:
            from enhanced_cli import EnhancedCLI
            cli = EnhancedCLI()
            cli.main_menu()
            return 0
        except Exception as e:
            console.print(f"[bold red]Error starting enhanced interface: {str(e)}[/bold red]")
            console.print("[yellow]Falling back to traditional interface...[/yellow]")
            from portfolio_cli import main as cli_main
            return cli_main()

if __name__ == "__main__":
    sys.exit(main())