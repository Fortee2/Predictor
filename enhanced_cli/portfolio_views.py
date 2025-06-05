"""
Portfolio views and commands for the Enhanced CLI.

This module provides commands for portfolio management operations such as
listing, creating, viewing, and managing portfolios.
"""

from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from datetime import datetime

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class ListPortfoliosCommand(Command):
    """Command to list all portfolios."""
    
    def __init__(self):
        super().__init__("List Portfolios", "Display all portfolios")
    
    @error_handler("listing portfolios")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to list all portfolios.
        
        Args:
            cli: The CLI instance
        """
        with ui.progress("Loading portfolios...") as progress:
            progress.add_task("", total=None)
            
            # Fetch portfolios
            portfolios = []
            try:
                cursor = cli.cli.portfolio_dao.connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM portfolio ORDER BY name")
                portfolios = cursor.fetchall()
                cursor.close()
            except Exception as e:
                ui.status_message(f"Error loading portfolios: {str(e)}", "error")
                return
        
        if not portfolios:
            ui.status_message("No portfolios found.", "warning")
            return
        
        # Prepare table columns
        columns = [
            {'header': 'ID', 'style': 'cyan'},
            {'header': 'Name', 'style': 'green'},
            {'header': 'Description'},
            {'header': 'Tickers', 'style': 'magenta'},
            {'header': 'Status'},
            {'header': 'Date Added'}
        ]
        
        # Prepare table rows
        rows = []
        for portfolio in portfolios:
            ticker_count = len(cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio['id']))
            
            rows.append([
                str(portfolio['id']),
                portfolio['name'],
                portfolio['description'] or "",
                str(ticker_count),
                "[green]Active[/green]" if portfolio['active'] else "[red]Inactive[/red]",
                portfolio['date_added'].strftime('%Y-%m-%d')
            ])
        
        # Display the table
        table = ui.data_table("Your Portfolios", columns, rows)
        ui.console.print(table)


class CreatePortfolioCommand(Command):
    """Command to create a new portfolio."""
    
    def __init__(self):
        super().__init__("Create Portfolio", "Create a new portfolio")
    
    @error_handler("creating portfolio")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to create a new portfolio.
        
        Args:
            cli: The CLI instance
        """
        # Display form header
        ui.console.print(ui.section_header("Create a New Portfolio"))
        
        # Define form fields
        fields = [
            {
                'name': 'name',
                'prompt': "[bold]Portfolio Name[/bold]"
            },
            {
                'name': 'description',
                'prompt': "[bold]Description[/bold] (optional)"
            },
            {
                'name': 'initial_cash',
                'prompt': "[bold]Initial Cash Balance ($)[/bold]",
                'type': float,
                'default': "0.00"
            }
        ]
        
        # Get form data
        data = ui.input_form(fields)
        
        # Confirm
        if ui.confirm_action(f"Create portfolio [bold]{data['name']}[/bold] with description: [italic]{data['description']}[/italic] and ${data['initial_cash']:.2f} cash?"):
            with ui.progress("Creating portfolio...") as progress:
                progress.add_task("", total=None)
                portfolio_id = cli.cli.portfolio_dao.create_portfolio(data['name'], data['description'], data['initial_cash'])
            
            if portfolio_id:
                ui.status_message(f"Portfolio created successfully with ID: {portfolio_id}", "success")
                
                # Ask if user wants to add tickers
                if ui.confirm_action("Would you like to add tickers to this portfolio now?"):
                    add_tickers_command = AddTickersCommand()
                    add_tickers_command.execute(cli, portfolio_id=portfolio_id)
            else:
                ui.status_message("Failed to create portfolio", "error")


class ViewPortfolioCommand(Command):
    """Command to view and manage a portfolio."""
    
    def __init__(self):
        super().__init__("View Portfolio", "View and manage a portfolio")
    
    @error_handler("viewing portfolio")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view and manage a portfolio.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID to view
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # List portfolios and ask for selection
            list_command = ListPortfoliosCommand()
            list_command.execute(cli)
            
            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to view[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return
        
        with ui.progress("Loading portfolio details...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
            
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
        
        # Portfolio header
        ui.console.print(ui.header(portfolio['name'], f"Portfolio #{portfolio_id}"))
        
        # Portfolio details
        ui.console.print(f"[bold]Description:[/bold] {portfolio['description']}")
        ui.console.print(f"[bold]Status:[/bold] {'[green]Active[/green]' if portfolio['active'] else '[red]Inactive[/red]'}")
        ui.console.print(f"[bold]Date Added:[/bold] {portfolio['date_added'].strftime('%Y-%m-%d')}")
        
        # Get and display cash balance
        cash_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id)
        ui.console.print(f"[bold]Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        
        # Get current positions
        with ui.progress("Loading positions...") as progress:
            progress.add_task("", total=None)
            positions = cli.cli.transactions_dao.get_current_positions(portfolio_id)
            tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
        
        # Current Holdings Table
        columns = [
            {'header': 'Symbol', 'style': 'cyan'},
            {'header': 'Shares', 'justify': 'right'},
            {'header': 'Avg Price', 'justify': 'right'},
            {'header': 'Current Price', 'justify': 'right'},
            {'header': 'Value', 'justify': 'right'},
            {'header': 'Gain/Loss', 'justify': 'right'},
            {'header': 'Percent', 'justify': 'right'}
        ]
        
        portfolio_value = 0
        rows = []
        
        if positions:
            for ticker_id, position in positions.items():
                ticker_data = cli.cli.ticker_dao.get_ticker_data(ticker_id)
                current_price = ticker_data.get('last_price', 0)
                shares = float(position['shares']) if hasattr(position['shares'], 'as_tuple') else position['shares']
                avg_price = position.get('avg_price', 0)
                avg_price = float(avg_price) if hasattr(avg_price, 'as_tuple') else avg_price
                value = shares * current_price
                gain_loss = value - (shares * avg_price)
                percent = (gain_loss / (shares * avg_price)) * 100 if avg_price > 0 else 0
                
                portfolio_value += value
                
                # Color formatting for gain/loss values
                gl_color = "green" if gain_loss >= 0 else "red"
                gl_formatted = f"[{gl_color}]${gain_loss:.2f}[/{gl_color}]"
                percent_formatted = f"[{gl_color}]{percent:.2f}%[/{gl_color}]"
                
                rows.append([
                    position['symbol'],
                    f"{shares:.2f}",
                    f"${avg_price:.2f}",
                    f"${current_price:.2f}",
                    f"${value:.2f}",
                    gl_formatted,
                    percent_formatted
                ])
        else:
            rows.append(["[italic]No current holdings[/italic]", "", "", "", "", "", ""])
        
        holdings_table = ui.data_table("Current Holdings", columns, rows)
        ui.console.print(holdings_table)
        
        # Add cash to total portfolio value
        total_value = portfolio_value + cash_balance
        ui.console.print(f"[bold]Stock Value:[/bold] [green]${portfolio_value:.2f}[/green]")
        ui.console.print(f"[bold]Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        ui.console.print(f"[bold]Total Portfolio Value:[/bold] [green]${total_value:.2f}[/green]")
        
        # Portfolio Actions Menu
        options = {
            "1": "Add Tickers",
            "2": "Remove Tickers",
            "3": "Log Transaction",
            "4": "View Transactions",
            "5": "Analyze Portfolio",
            "6": "View Performance",
            "7": "Manage Cash",
            "8": "Back to Main Menu"
        }
        
        choice = ui.menu("Portfolio Actions", options)
        
        if choice == "1":
            add_tickers_command = AddTickersCommand()
            add_tickers_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "2":
            remove_tickers_command = RemoveTickersCommand()
            remove_tickers_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "3":
            from enhanced_cli.transaction_views import LogTransactionCommand
            log_transaction_command = LogTransactionCommand()
            log_transaction_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "4":
            from enhanced_cli.transaction_views import ViewTransactionsCommand
            view_transactions_command = ViewTransactionsCommand()
            view_transactions_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "5":
            from enhanced_cli.analysis_views import AnalyzePortfolioCommand
            analyze_command = AnalyzePortfolioCommand()
            analyze_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "6":
            from enhanced_cli.analysis_views import ViewPerformanceCommand
            performance_command = ViewPerformanceCommand()
            performance_command.execute(cli, portfolio_id=portfolio_id)
        elif choice == "7":
            from enhanced_cli.cash_management_views import ManageCashCommand
            cash_command = ManageCashCommand()
            cash_command.execute(cli, portfolio_id=portfolio_id)
        # choice 8 returns to main menu


class AddTickersCommand(Command):
    """Command to add tickers to a portfolio."""
    
    def __init__(self):
        super().__init__("Add Tickers", "Add tickers to a portfolio")
    
    @error_handler("adding tickers")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to add tickers to a portfolio.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # List portfolios and ask for selection
            list_command = ListPortfoliosCommand()
            list_command.execute(cli)
            
            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return
        
        # Get portfolio info for header
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
            
        ui.console.print(ui.section_header(f"Add Tickers to Portfolio #{portfolio_id} - {portfolio['name']}"))
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if ticker_symbols:
            with ui.progress("Adding tickers...") as progress:
                progress.add_task("", total=None)
                cli.cli.add_tickers(portfolio_id, ticker_symbols)
                
            ui.status_message(f"Tickers added to portfolio: {portfolio['name']}", "success")
        else:
            ui.status_message("No tickers entered.", "warning")


class RemoveTickersCommand(Command):
    """Command to remove tickers from a portfolio."""
    
    def __init__(self):
        super().__init__("Remove Tickers", "Remove tickers from a portfolio")
    
    @error_handler("removing tickers")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to remove tickers from a portfolio.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # List portfolios and ask for selection
            list_command = ListPortfoliosCommand()
            list_command.execute(cli)
            
            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return
        
        # Get portfolio info
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
            
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
        
        if not tickers:
            ui.status_message("This portfolio has no tickers to remove.", "warning")
            return
        
        # Show current tickers
        ui.console.print("[bold]Current Tickers:[/bold]")
        for i, symbol in enumerate(tickers, 1):
            ui.console.print(f"[{i}] {symbol}")
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols to remove[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if ticker_symbols:
            if ui.confirm_action(f"Remove {len(ticker_symbols)} ticker(s) from portfolio #{portfolio_id}?"):
                with ui.progress("Removing tickers...") as progress:
                    progress.add_task("", total=None)
                    cli.cli.remove_tickers(portfolio_id, ticker_symbols)
                    
                ui.status_message(f"Tickers removed from portfolio: {portfolio['name']}", "success")
        else:
            ui.status_message("No tickers specified for removal.", "warning")


def register_portfolio_commands(registry: CommandRegistry) -> None:
    """
    Register portfolio-related commands with the command registry.
    
    Args:
        registry: The command registry to register commands with
    """
    registry.register("list_portfolios", ListPortfoliosCommand(), "portfolio")
    registry.register("create_portfolio", CreatePortfolioCommand(), "portfolio")
    registry.register("view_portfolio", ViewPortfolioCommand(), "portfolio")
    registry.register("add_tickers", AddTickersCommand(), "portfolio")
    registry.register("remove_tickers", RemoveTickersCommand(), "portfolio")
