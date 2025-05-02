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
                console.print("[bold red]✗ Failed to create portfolio[/bold red]")
    
    def view_portfolio(self, portfolio_id=None):
        """View detailed portfolio information."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to view[/bold]"))
        
        with console.status("[bold green]Loading portfolio details...[/bold green]"):
            portfolio = self.cli.portfolio_dao.read_portfolio(portfolio_id)
            
        if not portfolio:
            console.print(f"[bold red]Portfolio with ID {portfolio_id} not found.[/bold red]")
            return
        
        # Portfolio header
        console.print(Panel(f"[bold blue]{portfolio['name']}[/bold blue]", 
                           subtitle=f"Portfolio #{portfolio_id}", box=box.ROUNDED))
        
        # Portfolio details
        console.print(f"[bold]Description:[/bold] {portfolio['description']}")
        console.print(f"[bold]Status:[/bold] {'[green]Active[/green]' if portfolio['active'] else '[red]Inactive[/red]'}")
        console.print(f"[bold]Date Added:[/bold] {portfolio['date_added'].strftime('%Y-%m-%d')}")
        
        # Get and display cash balance
        cash_balance = self.cli.portfolio_dao.get_cash_balance(portfolio_id)
        console.print(f"[bold]Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        
        # Get current positions
        with console.status("[bold green]Loading positions...[/bold green]"):
            positions = self.cli.transactions_dao.get_current_positions(portfolio_id)
            tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
        
        # Current Holdings Table
        table = Table(title="Current Holdings", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Shares", justify="right")
        table.add_column("Avg Price", justify="right")
        table.add_column("Current Price", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("Gain/Loss", justify="right")
        table.add_column("Percent", justify="right")
        
        portfolio_value = 0
        
        if positions:
            for ticker_id, position in positions.items():
                ticker_data = self.cli.ticker_dao.get_ticker_data(ticker_id)
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
                
                table.add_row(
                    position['symbol'],
                    f"{shares:.2f}",
                    f"${avg_price:.2f}",
                    f"${current_price:.2f}",
                    f"${value:.2f}",
                    gl_formatted,
                    percent_formatted
                )
        else:
            table.add_row("[italic]No current holdings[/italic]", "", "", "", "", "", "")
        
        console.print(table)
        
        # Add cash to total portfolio value
        total_value = portfolio_value + cash_balance
        console.print(f"[bold]Stock Value:[/bold] [green]${portfolio_value:.2f}[/green]")
        console.print(f"[bold]Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        console.print(f"[bold]Total Portfolio Value:[/bold] [green]${total_value:.2f}[/green]")
        
        # Portfolio Actions Menu
        console.print("\n[bold]Portfolio Actions:[/bold]")
        console.print("[1] Add Tickers")
        console.print("[2] Remove Tickers") 
        console.print("[3] Log Transaction")
        console.print("[4] View Transactions")
        console.print("[5] Analyze Portfolio")
        console.print("[6] View Performance")
        console.print("[7] Manage Cash")
        console.print("[8] Back to Main Menu")
        
        choice = Prompt.ask("Select an action", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="8")
        
        if choice == "1":
            self.add_tickers_to_portfolio(portfolio_id)
        elif choice == "2":
            self.remove_tickers_from_portfolio(portfolio_id)
        elif choice == "3":
            self.log_transaction(portfolio_id)
        elif choice == "4":
            self.view_transactions(portfolio_id)
        elif choice == "5":
            self.analyze_portfolio(portfolio_id)
        elif choice == "6":
            self.view_performance(portfolio_id)
        elif choice == "7":
            self.manage_cash(portfolio_id)
        # choice 8 returns to main menu
    
    def add_tickers_to_portfolio(self, portfolio_id):
        """Interactive ticker addition to a portfolio."""
        console.print(Panel(f"[bold]Add Tickers to Portfolio #{portfolio_id}[/bold]", box=box.ROUNDED))
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if ticker_symbols:
            with console.status("[bold green]Adding tickers...[/bold green]"):
                self.cli.add_tickers(portfolio_id, ticker_symbols)
    
    def remove_tickers_from_portfolio(self, portfolio_id):
        """Interactive ticker removal from a portfolio."""
        with console.status("[bold green]Loading tickers...[/bold green]"):
            tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
        
        if not tickers:
            console.print("[yellow]This portfolio has no tickers to remove.[/yellow]")
            return
        
        # Show current tickers
        console.print("[bold]Current Tickers:[/bold]")
        for i, symbol in enumerate(tickers, 1):
            console.print(f"[{i}] {symbol}")
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols to remove[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if ticker_symbols:
            if Confirm.ask(f"Remove {len(ticker_symbols)} ticker(s) from portfolio #{portfolio_id}?"):
                with console.status("[bold green]Removing tickers...[/bold green]"):
                    self.cli.remove_tickers(portfolio_id, ticker_symbols)
    
    def log_transaction(self, portfolio_id=None):
        """Interactive transaction logging."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
        
        console.print(Panel(f"[bold]Log Transaction for Portfolio #{portfolio_id}[/bold]", box=box.ROUNDED))
        
        # Show transaction type options
        console.print("[bold]Transaction Types:[/bold]")
        console.print("[1] Buy")
        console.print("[2] Sell")
        console.print("[3] Dividend")
        console.print("[4] Cash (Deposit/Withdraw)")
        
        trans_choice = Prompt.ask("Select transaction type", choices=["1", "2", "3", "4"], default="1")
        trans_type = {
            "1": "buy",
            "2": "sell",
            "3": "dividend",
            "4": "cash"
        }[trans_choice]
        
        # For cash transactions, we don't need a ticker
        ticker_symbol = None
        if trans_type != "cash":
            # Get tickers in portfolio
            with console.status("[bold green]Loading portfolio tickers...[/bold green]"):
                tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            if not tickers and Confirm.ask("[yellow]No tickers in this portfolio. Add one now?[/yellow]"):
                self.add_tickers_to_portfolio(portfolio_id)
                with console.status("[bold green]Reloading tickers...[/bold green]"):
                    tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
                
                if not tickers:
                    console.print("[bold red]Cannot log transactions without tickers in the portfolio.[/bold red]")
                    return
            
            # Show ticker options
            console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                console.print(f"[{i}] {ticker}")
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold]").upper()
        
        # Date selection with validation
        while True:
            date_str = Prompt.ask("[bold]Transaction date[/bold] (YYYY-MM-DD)", 
                               default=datetime.now().strftime('%Y-%m-%d'))
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                break
            except ValueError:
                console.print("[bold red]Invalid date format. Please use YYYY-MM-DD.[/bold red]")
        
        if trans_type in ["buy", "sell"]:
            shares = float(Prompt.ask("[bold]Number of shares[/bold]"))
            price = float(Prompt.ask("[bold]Price per share[/bold] ($)"))
            amount = None
        elif trans_type == "dividend":
            shares = None
            price = None
            amount = float(Prompt.ask("[bold]Dividend amount[/bold] ($)"))
        else:  # cash
            shares = None
            price = None
            
            # For cash, ask if deposit or withdrawal
            cash_action = Prompt.ask("[bold]Action[/bold]", choices=["deposit", "withdraw"], default="deposit")
            amount_str = Prompt.ask(f"[bold]Amount to {cash_action}[/bold] ($)")
            amount = float(amount_str)
            
            # For withdrawals, make the amount negative
            if cash_action == "withdraw":
                amount = -amount
        
        # Confirmation
        console.print("\n[bold]Transaction Summary:[/bold]")
        console.print(f"Portfolio: #{portfolio_id}")
        console.print(f"Type: {trans_type.upper()}")
        if ticker_symbol:
            console.print(f"Ticker: {ticker_symbol}")
        console.print(f"Date: {date_str}")
        
        if trans_type in ["buy", "sell"]:
            console.print(f"Shares: {shares}")
            console.print(f"Price: ${price:.2f}")
            console.print(f"Total: ${shares * price:.2f}")
        elif trans_type == "dividend":
            console.print(f"Dividend Amount: ${amount:.2f}")
        else:  # cash
            action_label = "Deposit" if amount > 0 else "Withdrawal"
            console.print(f"{action_label} Amount: ${abs(amount):.2f}")
        
        if Confirm.ask("Log this transaction?"):
            # Use a separate status for each operation and ensure it completes before moving on
            with console.status("[bold green]Logging transaction...[/bold green]") as status:
                self.cli.log_transaction(
                    portfolio_id, trans_type, date_str, ticker_symbol, shares, price, amount
                )
            
            # Only show the confirmation after the status context is completed
            console.print("[bold green]✓ Transaction logged successfully[/bold green]")
            
            # Check cash balance after transaction
            cash_balance = self.cli.portfolio_dao.get_cash_balance(portfolio_id)
            console.print(f"[bold]Current Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
            
            # Separate prompt for recalculation with no status in background
            if Confirm.ask("Would you like to recalculate portfolio history with this new transaction?"):
                with console.status("[bold green]Recalculating portfolio history...[/bold green]"):
                    self.cli.recalculate_portfolio_history(portfolio_id)
                console.print("[bold green]✓ Portfolio history recalculated successfully[/bold green]")
    
    def view_transactions(self, portfolio_id=None, ticker_symbol=None):
        """View transaction history with filtering options."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
        
        # Ask if they want to filter by ticker
        if ticker_symbol is None and Confirm.ask("Filter by ticker symbol?"):
            with console.status("[bold green]Loading tickers...[/bold green]"):
                tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                console.print(f"[{i}] {ticker}")
            
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold] (or leave empty for all)").upper()
            if ticker_symbol == "":
                ticker_symbol = None
        
        with console.status("[bold green]Loading transactions...[/bold green]"):
            portfolio = self.cli.portfolio_dao.read_portfolio(portfolio_id)
            
            # Get transactions
            security_id = None
            if ticker_symbol:
                ticker_id = self.cli.ticker_dao.get_ticker_id(ticker_symbol)
                if ticker_id:
                    security_id = self.cli.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            
            transactions = self.cli.transactions_dao.get_transaction_history(portfolio_id, security_id)
        
        console.print(Panel(f"[bold]Transaction History for {portfolio['name']}[/bold]" + 
                          (f" - {ticker_symbol}" if ticker_symbol else ""), box=box.ROUNDED))
        
        if not transactions:
            console.print("[yellow]No transactions found.[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Symbol")
        table.add_column("Shares", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Amount", justify="right")
        table.add_column("Total", justify="right", style="bold")
        
        for t in transactions:
            date = t['transaction_date'].strftime('%Y-%m-%d')
            type_str = t['transaction_type'].capitalize()
            symbol = t['symbol']
            
            if t['transaction_type'] in ['buy', 'sell']:
                shares = f"{t['shares']:.2f}"
                price = f"${t['price']:.2f}"
                amount = "—"
                total = f"${t['shares'] * t['price']:.2f}"
            else:  # dividend
                shares = "—"
                price = "—"
                amount = f"${t['amount']:.2f}"
                total = amount
            
            table.add_row(date, type_str, symbol, shares, price, amount, total)
        
        console.print(table)
    
    def analyze_portfolio(self, portfolio_id=None, ticker_symbol=None):
        """Enhanced portfolio analysis display."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to analyze[/bold]"))
        
        # Ask if they want to analyze specific ticker
        if ticker_symbol is None and Confirm.ask("Analyze specific ticker?"):
            with console.status("[bold green]Loading tickers...[/bold green]"):
                tickers = self.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                console.print(f"[{i}] {ticker}")
            
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold] (or leave empty for all)").upper()
            if ticker_symbol == "":
                ticker_symbol = None
        
        with console.status("[bold green]Running portfolio analysis...[/bold green]"):
            self.cli.analyze_portfolio(portfolio_id, ticker_symbol)
            
        # Analysis results are printed directly by the CLI analyze_portfolio method
        # After analysis is complete, wait for user input to continue
        Prompt.ask("[bold]Press Enter to continue[/bold]")
    
    def view_performance(self, portfolio_id=None):
        """Enhanced portfolio performance visualization."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
        
        console.print(Panel(f"[bold]Portfolio Performance[/bold]", box=box.ROUNDED))
        
        # Time period options
        console.print("[bold]Select Time Period:[/bold]")
        console.print("[1] Last 30 days")
        console.print("[2] Last 3 months")
        console.print("[3] Last 6 months")
        console.print("[4] Year to date")
        console.print("[5] Last 1 year")
        console.print("[6] Custom range")
        
        period_choice = Prompt.ask("Select period", choices=["1", "2", "3", "4", "5", "6"], default="1")
        
        today = datetime.now().date()
        start_date = None
        end_date = today.strftime('%Y-%m-%d')
        days = 30
        
        if period_choice == "1":  # 30 days
            start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            days = 30
        elif period_choice == "2":  # 3 months
            start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
            days = 90
        elif period_choice == "3":  # 6 months
            start_date = (today - timedelta(days=180)).strftime('%Y-%m-%d')
            days = 180
        elif period_choice == "4":  # YTD
            start_date = datetime(today.year, 1, 1).strftime('%Y-%m-%d')
            days = (today - datetime(today.year, 1, 1).date()).days
        elif period_choice == "5":  # 1 year
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
            days = 365
        elif period_choice == "6":  # Custom
            while True:
                start_date = Prompt.ask("[bold]Start date[/bold] (YYYY-MM-DD)")
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                    break
                except ValueError:
                    console.print("[bold red]Invalid date format. Please use YYYY-MM-DD.[/bold red]")
            
            while True:
                end_date = Prompt.ask("[bold]End date[/bold] (YYYY-MM-DD)", 
                                    default=today.strftime('%Y-%m-%d'))
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    if end_date_obj > today:
                        console.print("[bold yellow]End date cannot be in the future. Using today's date.[/bold yellow]")
                        end_date = today.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    console.print("[bold red]Invalid date format. Please use YYYY-MM-DD.[/bold red]")
        
        # Ask about chart generation
        generate_chart = Confirm.ask("Generate performance chart?")
        
        with console.status("[bold green]Calculating performance...[/bold green]"):
            self.cli.view_portfolio_performance(portfolio_id, days, start_date, end_date, generate_chart)
            
        # Performance results are printed directly by the CLI view_portfolio_performance method
        # After performance display is complete, wait for user input to continue
        Prompt.ask("[bold]Press Enter to continue[/bold]")
    
    def watch_list_menu(self):
        """Display and manage watch lists."""
        console.print(Panel("[bold]Watch List Management[/bold]", box=box.ROUNDED))
        
        console.print("[1] View All Watch Lists")
        console.print("[2] Create New Watch List")
        console.print("[3] View/Edit Watch List")
        console.print("[4] Delete Watch List")
        console.print("[5] Back to Main Menu")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"], default="1")
        
        if choice == "1":
            self.view_all_watch_lists()
        elif choice == "2":
            self.create_watch_list()
        elif choice == "3":
            self.view_watch_list()
        elif choice == "4":
            self.delete_watch_list()
        # choice 5 returns to main menu
    
    def view_all_watch_lists(self):
        """Display all watch lists in a table."""
        with console.status("[bold green]Loading watch lists...[/bold green]"):
            watch_lists = self.cli.watch_list_dao.get_watch_list()
        
        if not watch_lists:
            console.print("[yellow]No watch lists found.[/yellow]")
            if Confirm.ask("Create a new watch list?"):
                self.create_watch_list()
            return
        
        table = Table(title="Your Watch Lists", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description")
        table.add_column("Tickers", style="magenta")
        table.add_column("Date Created")
        
        for wl in watch_lists:
            ticker_count = len(self.cli.watch_list_dao.get_tickers_in_watch_list(wl['id']))
            table.add_row(
                str(wl['id']),
                wl['name'],
                wl['description'] or "",
                str(ticker_count),
                wl['date_created'].strftime('%Y-%m-%d')
            )
        
        console.print(table)
        
        # Ask if user wants to view a specific watch list
        if Confirm.ask("View a specific watch list?"):
            watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            self.view_watch_list(watch_list_id)
    
    def create_watch_list(self):
        """Interactive watch list creation."""
        console.print(Panel("[bold]Create a New Watch List[/bold]", box=box.ROUNDED))
        
        name = Prompt.ask("[bold]Watch List Name[/bold]")
        description = Prompt.ask("[bold]Description[/bold] (optional)")
        
        if Confirm.ask(f"Create watch list [bold]{name}[/bold] with description: [italic]{description}[/italic]?"):
            with console.status("[bold green]Creating watch list...[/bold green]"):
                watch_list_id = self.cli.create_watch_list(name, description)
            
            if watch_list_id:
                console.print(f"[bold green]✓ Watch list created successfully with ID: {watch_list_id}[/bold green]")
                
                if Confirm.ask("Would you like to add tickers to this watch list now?"):
                    self.add_tickers_to_watch_list(watch_list_id)
            else:
                console.print("[bold red]✗ Failed to create watch list[/bold red]")
    
    def view_watch_list(self, watch_list_id=None):
        """View and manage a specific watch list."""
        if watch_list_id is None:
            with console.status("[bold green]Loading watch lists...[/bold green]"):
                watch_lists = self.cli.watch_list_dao.get_watch_list()
            
            if not watch_lists:
                console.print("[yellow]No watch lists found.[/yellow]")
                return
            
            table = Table(title="Your Watch Lists", box=box.ROUNDED)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            
            for wl in watch_lists:
                table.add_row(str(wl['id']), wl['name'])
            
            console.print(table)
            watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to view[/bold]"))
        
        with console.status("[bold green]Loading watch list details...[/bold green]"):
            watch_list = self.cli.watch_list_dao.get_watch_list(watch_list_id)
            
        if not watch_list:
            console.print(f"[bold red]Watch list with ID {watch_list_id} not found.[/bold red]")
            return
        
        # Watch List header
        console.print(Panel(f"[bold blue]{watch_list['name']}[/bold blue]", 
                           subtitle=f"Watch List #{watch_list_id}", box=box.ROUNDED))
        
        # Watch List details
        if watch_list['description']:
            console.print(f"[bold]Description:[/bold] {watch_list['description']}")
        console.print(f"[bold]Date Created:[/bold] {watch_list['date_created'].strftime('%Y-%m-%d')}")
        
        # Get tickers in watch list
        with console.status("[bold green]Loading tickers...[/bold green]"):
            tickers = self.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if tickers:
            table = Table(title="Tickers in Watch List", box=box.ROUNDED)
            table.add_column("Symbol", style="cyan")
            table.add_column("Name")
            table.add_column("Notes")
            table.add_column("Date Added")
            
            for ticker in tickers:
                table.add_row(
                    ticker['symbol'],
                    ticker['name'],
                    ticker['notes'] or "",
                    ticker['date_added'].strftime('%Y-%m-%d')
                )
            
            console.print(table)
        else:
            console.print("[yellow]No tickers in this watch list.[/yellow]")
        
        # Watch List Actions Menu
        console.print("\n[bold]Watch List Actions:[/bold]")
        console.print("[1] Add Tickers")
        console.print("[2] Remove Tickers") 
        console.print("[3] Update Ticker Notes")
        console.print("[4] Analyze Watch List")
        console.print("[5] Back to Watch Lists")
        
        choice = Prompt.ask("Select an action", choices=["1", "2", "3", "4", "5"], default="5")
        
        if choice == "1":
            self.add_tickers_to_watch_list(watch_list_id)
        elif choice == "2":
            self.remove_tickers_from_watch_list(watch_list_id)
        elif choice == "3":
            self.update_ticker_notes(watch_list_id)
        elif choice == "4":
            self.analyze_watch_list(watch_list_id)
        # choice 5 returns to watch list menu
    
    def add_tickers_to_watch_list(self, watch_list_id):
        """Interactive ticker addition to a watch list."""
        console.print(Panel(f"[bold]Add Tickers to Watch List #{watch_list_id}[/bold]", box=box.ROUNDED))
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if not ticker_symbols:
            console.print("[yellow]No tickers entered.[/yellow]")
            return
            
        notes = Prompt.ask("[bold]Notes[/bold] (optional, will apply to all tickers)")
        
        if Confirm.ask(f"Add {len(ticker_symbols)} ticker(s) to watch list #{watch_list_id}?"):
            with console.status("[bold green]Adding tickers...[/bold green]"):
                for symbol in ticker_symbols:
                    self.cli.add_watch_list_ticker(watch_list_id, [symbol], notes)
            
            console.print("[bold green]✓ Tickers added successfully[/bold green]")
    
    def remove_tickers_from_watch_list(self, watch_list_id):
        """Interactive ticker removal from a watch list."""
        with console.status("[bold green]Loading tickers...[/bold green]"):
            tickers = self.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            console.print("[yellow]This watch list has no tickers to remove.[/yellow]")
            return
        
        # Show current tickers
        console.print("[bold]Current Tickers:[/bold]")
        ticker_symbols = []
        for ticker in tickers:
            console.print(f"- {ticker['symbol']}")
            ticker_symbols.append(ticker['symbol'])
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols to remove[/bold] (separated by spaces)")
        to_remove = ticker_input.upper().split()
        
        valid_tickers = [t for t in to_remove if t in ticker_symbols]
        if not valid_tickers:
            console.print("[yellow]No valid tickers selected for removal.[/yellow]")
            return
        
        if Confirm.ask(f"Remove {len(valid_tickers)} ticker(s) from watch list #{watch_list_id}?"):
            with console.status("[bold green]Removing tickers...[/bold green]"):
                self.cli.remove_watch_list_ticker(watch_list_id, valid_tickers)
            
            console.print("[bold green]✓ Tickers removed successfully[/bold green]")
    
    def update_ticker_notes(self, watch_list_id):
        """Update notes for a ticker in a watch list."""
        with console.status("[bold green]Loading tickers...[/bold green]"):
            tickers = self.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            console.print("[yellow]This watch list has no tickers.[/yellow]")
            return
        
        # Show current tickers with notes
        table = Table(title="Current Tickers", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Notes")
        
        for ticker in tickers:
            table.add_row(ticker['symbol'], ticker['notes'] or "")
        
        console.print(table)
        
        ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to update[/bold]").upper()
        
        # Check if ticker exists in the watch list
        ticker_exists = any(t['symbol'] == ticker_symbol for t in tickers)
        if not ticker_exists:
            console.print(f"[bold red]Ticker {ticker_symbol} not found in this watch list.[/bold red]")
            return
        
        # Get current notes
        current_notes = next((t['notes'] for t in tickers if t['symbol'] == ticker_symbol), "")
        notes = Prompt.ask("[bold]Enter new notes[/bold]", default=current_notes or "")
        
        if Confirm.ask(f"Update notes for {ticker_symbol}?"):
            with console.status("[bold green]Updating notes...[/bold green]"):
                self.cli.update_watch_list_ticker_notes(watch_list_id, ticker_symbol, notes)
            
            console.print("[bold green]✓ Notes updated successfully[/bold green]")
    
    def analyze_watch_list(self, watch_list_id):
        """Analyze tickers in a watch list."""
        with console.status("[bold green]Loading watch list...[/bold green]"):
            watch_list = self.cli.watch_list_dao.get_watch_list(watch_list_id)
            
        if not watch_list:
            console.print(f"[bold red]Watch list with ID {watch_list_id} not found.[/bold red]")
            return
        
        # Get tickers in watch list
        with console.status("[bold green]Loading tickers...[/bold green]"):
            tickers = self.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            console.print("[yellow]This watch list has no tickers to analyze.[/yellow]")
            return
        
        # Ask if they want to analyze a specific ticker
        console.print("[bold]Available Tickers:[/bold]")
        for ticker in tickers:
            console.print(f"- {ticker['symbol']}")
        
        analyze_all = Confirm.ask("Analyze all tickers?", default=True)
        ticker_symbol = None
        
        if not analyze_all:
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to analyze[/bold]").upper()
            # Check if ticker exists in the watch list
            ticker_exists = any(t['symbol'] == ticker_symbol for t in tickers)
            if not ticker_exists:
                console.print(f"[bold red]Ticker {ticker_symbol} not found in this watch list.[/bold red]")
                return
        
        with console.status("[bold green]Running analysis...[/bold green]"):
            self.cli.analyze_watch_list(watch_list_id, ticker_symbol)
        
        # Analysis results are printed directly by the CLI analyze_watch_list method
        # After analysis is complete, wait for user input to continue
        Prompt.ask("[bold]Press Enter to continue[/bold]")
    
    def delete_watch_list(self):
        """Delete a watch list."""
        with console.status("[bold green]Loading watch lists...[/bold green]"):
            watch_lists = self.cli.watch_list_dao.get_watch_list()
        
        if not watch_lists:
            console.print("[yellow]No watch lists found.[/yellow]")
            return
        
        table = Table(title="Your Watch Lists", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Tickers", style="magenta")
        
        for wl in watch_lists:
            ticker_count = len(self.cli.watch_list_dao.get_tickers_in_watch_list(wl['id']))
            table.add_row(str(wl['id']), wl['name'], str(ticker_count))
        
        console.print(table)
        
        watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to delete[/bold]"))
        
        # Get watch list details for confirmation
        with console.status("[bold green]Loading watch list details...[/bold green]"):
            watch_list = self.cli.watch_list_dao.get_watch_list(watch_list_id)
        
        if not watch_list:
            console.print(f"[bold red]Watch list with ID {watch_list_id} not found.[/bold red]")
            return
        
        if Confirm.ask(f"[bold red]Are you sure you want to delete watch list '{watch_list['name']}'? This cannot be undone.[/bold red]", default=False):
            with console.status("[bold green]Deleting watch list...[/bold green]"):
                self.cli.delete_watch_list(watch_list_id)
            
            console.print("[bold green]✓ Watch list deleted successfully[/bold green]")
    
    def update_data(self):
        """Update data for all securities in portfolios."""
        if not Confirm.ask("[bold]This will update data for all securities in your portfolios. This may take some time. Continue?[/bold]"):
            return
        
        with Progress() as progress:
            task = progress.add_task("[bold green]Updating data...", total=None)
            self.cli.update_data()
        
        console.print("[bold green]✓ Data update complete[/bold green]")
    
    def settings_menu(self):
        """Display and manage application settings."""
        from data.config import Config
        config = Config()
        
        while True:
            console.print(Panel("[bold]Application Settings[/bold]", box=box.ROUNDED))
            
            console.print("[1] Database Settings")
            console.print("[2] UI Settings")
            console.print("[3] Analysis Settings")
            console.print("[4] Watchlist Settings")
            console.print("[5] Logging Settings")
            console.print("[6] Chart Settings")
            console.print("[7] Back to Main Menu")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
            
            if choice == "1":
                self._edit_settings("database", config)
            elif choice == "2":
                self._edit_settings("ui", config)
            elif choice == "3":
                self._edit_settings("analysis", config)
            elif choice == "4":
                self._edit_settings("watchlist", config)
            elif choice == "5":
                self._edit_settings("logging", config)
            elif choice == "6":
                self._edit_settings("chart", config)
            elif choice == "7":
                return
    
    def _edit_settings(self, section, config):
        """Edit settings for a specific section."""
        settings = config.get(section)
        if not settings:
            console.print(f"[yellow]No settings found for section: {section}[/yellow]")
            return
        
        console.print(Panel(f"[bold]{section.capitalize()} Settings[/bold]", box=box.ROUNDED))
        
        # Display current settings
        table = Table(title="Current Settings", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in settings.items():
            table.add_row(key, str(value))
        
        console.print(table)
        
        # Ask which setting to change
        setting_keys = list(settings.keys())
        options = {str(i+1): key for i, key in enumerate(setting_keys)}
        options[str(len(options) + 1)] = "Back"
        
        console.print("\n[bold]Select setting to change:[/bold]")
        for i, key in enumerate(setting_keys, 1):
            console.print(f"[{i}] {key}")
        console.print(f"[{len(options)}] Back")
        
        choice = Prompt.ask(
            "Select an option", 
            choices=list(options.keys()),
            default=str(len(options))
        )
        
        if options[choice] == "Back":
            return
        
        # Get the key and current value
        key_to_change = options[choice]
        current_value = settings[key_to_change]
        
        # Get new value based on type
        if isinstance(current_value, bool):
            new_value = Confirm.ask(f"Enable {key_to_change}?", default=current_value)
        elif isinstance(current_value, int):
            new_value = int(
                Prompt.ask(
                    f"Enter new value for {key_to_change}", default=str(current_value)))
        elif isinstance(current_value, float):
            new_value = float(Prompt.ask(f"Enter new value for {key_to_change}", default=str(current_value)))
        else:
            new_value = Prompt.ask(f"Enter new value for {key_to_change}", default=str(current_value))
        
        # Update the setting if changed
        if new_value != current_value:
            config.set(section, key_to_change, new_value)
            if config.save_config():
                console.print(f"[bold green]✓ Setting updated: {key_to_change} = {new_value}[/bold green]")
            else:
                console.print("[bold red]✗ Failed to save settings[/bold red]")
        else:
            console.print("[yellow]No changes made[/yellow]")
        
        # Ask if they want to edit another setting in this section
        if Confirm.ask("Edit another setting in this section?"):
            self._edit_settings(section, config)
    
    def manage_cash(self, portfolio_id=None):
        """Manage cash balance for a portfolio."""
        if portfolio_id is None:
            self.list_portfolios()
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
        
        with console.status("[bold green]Loading portfolio details...[/bold green]"):
            portfolio = self.cli.portfolio_dao.read_portfolio(portfolio_id)
            
        if not portfolio:
            console.print(f"[bold red]Portfolio with ID {portfolio_id} not found.[/bold red]")
            return
        
        # Current cash balance
        cash_balance = self.cli.portfolio_dao.get_cash_balance(portfolio_id)
        
        console.print(Panel(f"[bold]Cash Management for {portfolio['name']}[/bold]", box=box.ROUNDED))
        console.print(f"[bold]Current Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        
        # Cash management actions
        console.print("\n[bold]Select Action:[/bold]")
        console.print("[1] Deposit Cash")
        console.print("[2] Withdraw Cash")
        console.print("[3] View Cash Transactions")
        console.print("[4] Return to Portfolio")
        
        choice = Prompt.ask("Select an action", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":  # Deposit
            amount = float(Prompt.ask("[bold]Enter deposit amount ($)[/bold]", default="0.00"))
            
            if amount <= 0:
                console.print("[bold red]Amount must be greater than zero.[/bold red]")
                return
                
            if Confirm.ask(f"Deposit ${amount:.2f} to {portfolio['name']}?"):
                with console.status("[bold green]Processing deposit...[/bold green]"):
                    new_balance = self.cli.portfolio_dao.add_cash(portfolio_id, amount)
                
                console.print(f"[bold green]✓ Deposited ${amount:.2f} successfully[/bold green]")
                console.print(f"[bold]New Cash Balance:[/bold] [green]${new_balance:.2f}[/green]")
                
                # Ask if they want to log this as a cash transaction
                if Confirm.ask("Log this deposit as a cash transaction?"):
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    with console.status("[bold green]Logging cash transaction...[/bold green]"):
                        self.cli.log_transaction(portfolio_id, "cash", date_str, None, None, None, amount)
                    console.print("[bold green]✓ Cash transaction logged successfully[/bold green]")
                
        elif choice == "2":  # Withdraw
            amount = float(Prompt.ask("[bold]Enter withdrawal amount ($)[/bold]", default="0.00"))
            
            if amount <= 0:
                console.print("[bold red]Amount must be greater than zero.[/bold red]")
                return
                
            if amount > cash_balance:
                console.print(f"[bold yellow]Warning: Requested amount (${amount:.2f}) exceeds available balance (${cash_balance:.2f})[/bold yellow]")
                if not Confirm.ask("Continue with withdrawal anyway?", default=False):
                    console.print("Withdrawal cancelled.")
                    return
            
            if Confirm.ask(f"Withdraw ${amount:.2f} from {portfolio['name']}?"):
                with console.status("[bold green]Processing withdrawal...[/bold green]"):
                    new_balance = self.cli.portfolio_dao.withdraw_cash(portfolio_id, amount)
                
                console.print(f"[bold green]✓ Withdrew ${amount:.2f} successfully[/bold green]")
                console.print(f"[bold]New Cash Balance:[/bold] [green]${new_balance:.2f}[/green]")
                
                # Ask if they want to log this as a cash transaction
                if Confirm.ask("Log this withdrawal as a cash transaction?"):
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    with console.status("[bold green]Logging cash transaction...[/bold green]"):
                        self.cli.log_transaction(portfolio_id, "cash", date_str, None, None, None, -amount)
                    console.print("[bold green]✓ Cash transaction logged successfully[/bold green]")

        elif choice == "3":  # View cash transactions
            self.view_cash_transactions(portfolio_id)
        
        # Return to portfolio view automatically if the user selected option 4 or after completing an action
        if choice == "4" or Confirm.ask("Return to portfolio view?", default=True):
            self.view_portfolio(portfolio_id)
    
    def view_cash_transactions(self, portfolio_id):
        """View only cash transactions (deposits and withdrawals) for a portfolio."""
        with console.status("[bold green]Loading cash transactions...[/bold green]"):
            portfolio = self.cli.portfolio_dao.read_portfolio(portfolio_id)
            
            # Get all transactions
            transactions = self.cli.transactions_dao.get_transaction_history(portfolio_id)
            
            # Filter to only cash transactions
            cash_transactions = [t for t in transactions if t['transaction_type'] == 'cash']
        
        console.print(Panel(f"[bold]Cash Transaction History for {portfolio['name']}[/bold]", box=box.ROUNDED))
        
        if not cash_transactions:
            console.print("[yellow]No cash transactions found for this portfolio.[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("Date", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Amount", justify="right")
        table.add_column("Balance After", justify="right", style="bold")
        
        # Sort by date, newest first
        cash_transactions = sorted(cash_transactions, key=lambda x: x['transaction_date'], reverse=True)
        
        # We need to calculate the running balance since it's not stored in the transaction records
        current_balance = self.cli.portfolio_dao.get_cash_balance(portfolio_id)
        running_balance = current_balance
        
        # Since we're displaying newest first, we need to add up all transaction amounts 
        # to get the starting balance, then subtract as we go through chronologically
        total_transaction_amount = sum(t['amount'] for t in cash_transactions)
        
        # Starting balance before any transactions in our list
        starting_balance = current_balance - total_transaction_amount
        running_balance = starting_balance
        
        # Sort by date, oldest first for processing
        cash_transactions_chronological = sorted(cash_transactions, key=lambda x: x['transaction_date'])
        
        # Create a dictionary mapping transaction date to balance after that transaction
        balances = {}
        for t in cash_transactions_chronological:
            running_balance += t['amount']
            balances[t['transaction_date'].strftime('%Y-%m-%d')] = running_balance
            
        # Now display newest first
        for t in cash_transactions:
            date = t['transaction_date'].strftime('%Y-%m-%d')
            
            # Determine transaction type label and color
            if t['amount'] > 0:
                trans_type = "Deposit"
                amount_str = f"[green]+${t['amount']:.2f}[/green]"
            else:
                trans_type = "Withdrawal"
                amount_str = f"[red]-${abs(t['amount']):.2f}[/red]"
            
            balance = balances[date]
            table.add_row(
                date,
                trans_type,
                amount_str,
                f"${balance:.2f}"
            )
        
        console.print(table)
    
    def main_menu(self):
        """Display the main menu."""
        while True:
            self.display_header()
            
            console.print("\n[bold]Main Menu:[/bold]")
            console.print("[1] List Portfolios")
            console.print("[2] Create Portfolio")
            console.print("[3] View/Manage Portfolio")
            console.print("[4] Log Transaction")
            console.print("[5] View Transactions") 
            console.print("[6] Analyze Portfolio")
            console.print("[7] View Portfolio Performance")
            console.print("[8] Watch List Management")
            console.print("[9] Update Data")
            console.print("[10] Settings")
            console.print("[0] Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0"], default="1")
            
            if choice == "1":
                self.list_portfolios()
            elif choice == "2":
                self.create_portfolio()
            elif choice == "3":
                self.view_portfolio()
            elif choice == "4":
                self.log_transaction()
            elif choice == "5":
                self.view_transactions()
            elif choice == "6":
                self.analyze_portfolio()
            elif choice == "7":
                self.view_performance()
            elif choice == "8":
                self.watch_list_menu()
            elif choice == "9":
                self.update_data()
            elif choice == "10":
                self.settings_menu()
            elif choice == "0":
                console.print("[bold green]Thank you for using the Portfolio Management System![/bold green]")
                return

if __name__ == "__main__":
    try:
        cli = EnhancedCLI()
        cli.main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Program interrupted. Exiting...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        import traceback
        traceback.print_exc()