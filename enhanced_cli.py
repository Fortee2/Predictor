#!/usr/bin/env python3
import sys
import os
import argparse
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich import box
from datetime import datetime, timedelta
from portfolio_cli import PortfolioCLI

console = Console()

def configure_logging():
    """Configure logging to redirect all logs to a file instead of the console."""
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_dir, "analysis.log")
    
    # Remove all existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger to write to file only
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='a'
    )
    
    # Get a list of all loggers used in the application
    loggers = [
        logging.getLogger('moving_averages'),
        logging.getLogger('config'),
        logging.getLogger('portfolio_cli'),
        logging.getLogger('bollinger_bands'),
        logging.getLogger('data_retrival'),
        logging.getLogger('ticker_dao'),
        logging.getLogger('rsi_calculations'),
        logging.getLogger('macd'),
        logging.getLogger('options_data'),
        logging.getLogger('news_sentiment')
    ]
    
    # Configure all these loggers to use file handler only
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    for logger in loggers:
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add file handler
        logger.addHandler(file_handler)
        logger.propagate = False  # Prevent propagation to root logger

class EnhancedCLI:
    """Enhanced CLI wrapper around the portfolio management application."""
    
    def __init__(self):
        self.cli = PortfolioCLI()
        configure_logging()  # Configure logging when CLI is initialized
    
    def display_header(self):
        """Display application header with styling."""
        console.print(Panel("[bold blue]Portfolio & Stock Management System[/bold blue]", 
                           subtitle="v1.0.0", box=box.DOUBLE))
    
    def list_portfolios(self):
        """List all portfolios with a nice table format."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Loading portfolios...[/bold blue]"),
            transient=True,
        ) as progress:
            progress.add_task("", total=None)
            # Fetch portfolios
            # Modified to use CLI method instead of directly accessing portfolio_dao
            portfolios = []
            try:
                # Get database cursor to execute query
                cursor = self.cli.portfolio_dao.connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM portfolio ORDER BY name")
                portfolios = cursor.fetchall()
                cursor.close()
            except Exception as e:
                console.print(f"[bold red]Error loading portfolios: {str(e)}[/bold red]")
                return
        
        if not portfolios:
            console.print("[yellow]No portfolios found.[/yellow]")
            return
        
        table = Table(title="Your Portfolios", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description")
        table.add_column("Tickers", style="magenta")
        table.add_column("Status")
        table.add_column("Date Added")
        
        for portfolio in portfolios:
            ticker_count = len(self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio['id']))
            table.add_row(
                str(portfolio['id']),
                portfolio['name'],
                portfolio['description'],
                str(ticker_count),
                "[green]Active[/green]" if portfolio['active'] else "[red]Inactive[/red]",
                portfolio['date_added'].strftime('%Y-%m-%d')
            )
        
        console.print(table)
    
    def create_portfolio(self):
        """Interactive portfolio creation."""
        console.print(Panel("[bold]Create a New Portfolio[/bold]", box=box.ROUNDED))
        
        name = Prompt.ask("[bold]Portfolio Name[/bold]")
        description = Prompt.ask("[bold]Description[/bold] (optional)")
        initial_cash = float(Prompt.ask("[bold]Initial Cash Balance ($)[/bold]", default="0.00"))
        
        if Confirm.ask(f"Create portfolio [bold]{name}[/bold] with description: [italic]{description}[/italic] and ${initial_cash:.2f} cash?"):
            with console.status("[bold green]Creating portfolio...[/bold green]"):
                portfolio_id = self.cli.portfolio_dao.create_portfolio(name, description, initial_cash)
            
            if portfolio_id:
                console.print(f"[bold green]✓ Portfolio created successfully with ID: {portfolio_id}[/bold green]")
                
                if Confirm.ask("Would you like to add tickers to this portfolio now?"):
                    self.add_tickers_to_portfolio(portfolio_id)
            else:
                console.print("[bold red]