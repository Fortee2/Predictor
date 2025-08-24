"""
Transaction views and commands for the Enhanced CLI.

This module provides commands for transaction management operations such as
logging transactions and viewing transaction history.
"""

from rich.prompt import Prompt
from datetime import datetime

from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class LogTransactionCommand(Command):
    """Command to log a new transaction."""
    
    def __init__(self):
        super().__init__("Log Transaction", "Record a new transaction")
    
    @error_handler("logging transaction")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to log a new transaction.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, 'selected_portfolio') and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand
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
            
        ui.console.print(ui.section_header(f"Log Transaction for Portfolio #{portfolio_id} - {portfolio['name']}"))
        
        # Show transaction type options
        options = {
            "1": "Buy",
            "2": "Sell",
            "3": "Dividend",
            "4": "Cash (Deposit/Withdraw)"
        }
        
        trans_choice = ui.menu("Transaction Types", options)
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
            with ui.progress("Loading portfolio tickers...") as progress:
                progress.add_task("", total=None)
                tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            if not tickers and ui.confirm_action("[yellow]No tickers in this portfolio. Add one now?[/yellow]"):
                from enhanced_cli.portfolio_views import AddTickersCommand
                add_tickers_command = AddTickersCommand()
                add_tickers_command.execute(cli, portfolio_id=portfolio_id)
                
                with ui.progress("Reloading tickers...") as progress:
                    progress.add_task("", total=None)
                    tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
                
                if not tickers:
                    ui.status_message("Cannot log transactions without tickers in the portfolio.", "error")
                    return
            
            # Show ticker options
            ui.console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                ui.console.print(f"[{i}] {ticker}")
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold]").upper()
        
        # Date selection with validation
        while True:
            date_str = Prompt.ask(
                "[bold]Transaction date[/bold] (YYYY-MM-DD)", 
                default=datetime.now().strftime('%Y-%m-%d')
            )
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                break
            except ValueError:
                ui.status_message("Invalid date format. Please use YYYY-MM-DD.", "error")
        
        # Different fields based on transaction type
        shares = None
        price = None
        amount = None
        
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
        ui.console.print("\n[bold]Transaction Summary:[/bold]")
        ui.console.print(f"Portfolio: #{portfolio_id} - {portfolio['name']}")
        ui.console.print(f"Type: {trans_type.upper()}")
        if ticker_symbol:
            ui.console.print(f"Ticker: {ticker_symbol}")
        ui.console.print(f"Date: {date_str}")
        
        if trans_type in ["buy", "sell"]:
            ui.console.print(f"Shares: {shares}")
            ui.console.print(f"Price: ${price:.2f}")
            ui.console.print(f"Total: ${shares * price:.2f}")
        elif trans_type == "dividend":
            ui.console.print(f"Dividend Amount: ${amount:.2f}")
        else:  # cash
            action_label = "Deposit" if amount > 0 else "Withdrawal"
            ui.console.print(f"{action_label} Amount: ${abs(amount):.2f}")
        
        if ui.confirm_action("Log this transaction?"):
            # Get portfolio value before transaction for comparison
            try:
                from datetime import timedelta
                transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Get portfolio value before transaction (previous day or same day before transaction)
                before_date = transaction_date - timedelta(days=1)
                portfolio_before = cli.cli.value_service.calculate_portfolio_value(
                    portfolio_id,
                    calculation_date=before_date,
                    include_cash=True,
                    include_dividends=False,
                    use_current_prices=False
                )
            except Exception:
                portfolio_before = None
            
            # Use a separate status for each operation
            with ui.progress("Logging transaction...") as progress:
                progress.add_task("", total=None)
                cli.cli.log_transaction(
                    portfolio_id, trans_type, date_str, ticker_symbol, shares, price, amount
                )
            
            # Only show the confirmation after the status context is completed
            ui.status_message("Transaction logged successfully", "success")
            
            # Show updated portfolio information
            ui.console.print("\n[bold]Portfolio Update:[/bold]")
            
            # Check cash balance after transaction
            cash_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id)
            ui.console.print(f"[bold]Current Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
            
            # Get current portfolio value after transaction
            try:
                portfolio_after = cli.cli.value_service.calculate_portfolio_value(
                    portfolio_id,
                    include_cash=True,
                    include_dividends=False,
                    use_current_prices=True
                )
                
                ui.console.print(f"[bold]Current Portfolio Value:[/bold] [green]${portfolio_after['total_value']:,.2f}[/green]")
                
                # Show change if we have before value
                if portfolio_before and portfolio_before['total_value'] > 0:
                    value_change = portfolio_after['total_value'] - portfolio_before['total_value']
                    change_pct = (value_change / portfolio_before['total_value']) * 100
                    
                    change_color = "green" if value_change >= 0 else "red"
                    change_sign = "+" if value_change >= 0 else ""
                    
                    ui.console.print(f"[bold]Value Change:[/bold] [{change_color}]{change_sign}${value_change:,.2f} ({change_sign}{change_pct:.2f}%)[/{change_color}]")
                    
            except Exception as e:
                ui.console.print(f"[yellow]Could not calculate portfolio value change: {e}[/yellow]")
            
            # Separate prompt for recalculation
            if ui.confirm_action("Would you like to recalculate portfolio history with this new transaction?"):
                with ui.progress("Recalculating portfolio history...") as progress:
                    progress.add_task("", total=None)
                    cli.cli.recalculate_portfolio_history(portfolio_id)
                ui.status_message("Portfolio history recalculated successfully", "success")


class ViewTransactionsCommand(Command):
    """Command to view transaction history."""
    
    def __init__(self):
        super().__init__("View Transactions", "View transaction history")
    
    @error_handler("viewing transactions")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view transaction history.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
            ticker_symbol: Optional ticker symbol to filter transactions
        """
        portfolio_id = kwargs.get('portfolio_id')
        ticker_symbol = kwargs.get('ticker_symbol')
        
        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, 'selected_portfolio') and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)
                
                try:
                    portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return
        
        # Ask if they want to filter by ticker
        if ticker_symbol is None and ui.confirm_action("Filter by ticker symbol?"):
            with ui.progress("Loading tickers...") as progress:
                progress.add_task("", total=None)
                tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            ui.console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                ui.console.print(f"[{i}] {ticker}")
            
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold] (or leave empty for all)").upper()
            if ticker_symbol == "":
                ticker_symbol = None
        
        with ui.progress("Loading transactions...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
            
            # Get transactions
            security_id = None
            if ticker_symbol:
                ticker_id = cli.cli.ticker_dao.get_ticker_id(ticker_symbol)
                if ticker_id:
                    security_id = cli.cli.portfolio_dao.get_security_id(portfolio_id, ticker_id)
            
            transactions = cli.cli.transactions_dao.get_transaction_history(portfolio_id, security_id)
        
        # Create header based on filter
        header_text = f"Transaction History for {portfolio['name']}"
        if ticker_symbol:
            header_text += f" - {ticker_symbol}"
            
        ui.console.print(ui.section_header(header_text))
        
        if not transactions:
            ui.status_message("No transactions found.", "warning")
            return
        
        # Prepare table columns
        columns = [
            {'header': 'Date', 'style': 'cyan'},
            {'header': 'Type', 'style': 'green'},
            {'header': 'Symbol'},
            {'header': 'Shares', 'justify': 'right'},
            {'header': 'Price', 'justify': 'right'},
            {'header': 'Amount', 'justify': 'right'},
            {'header': 'Total', 'justify': 'right', 'style': 'bold'}
        ]
        
        # Prepare table rows
        rows = []
        for t in transactions:
            date = t['transaction_date'].strftime('%Y-%m-%d')
            type_str = t['transaction_type'].capitalize()
            symbol = t['symbol'] if 'symbol' in t else "-"
            
            if t['transaction_type'] in ['buy', 'sell']:
                shares = f"{t['shares']:.2f}"
                price = f"${t['price']:.2f}"
                amount = "—"
                total = f"${t['shares'] * t['price']:.2f}"
            else:  # dividend or cash
                shares = "—"
                price = "—"
                amount = f"${t['amount']:.2f}" if t.get('amount') is not None else "—"
                total = amount
            
            rows.append([date, type_str, symbol, shares, price, amount, total])
        
        # Display the table
        table = ui.data_table("Transactions", columns, rows)
        ui.console.print(table)


def register_transaction_commands(registry: CommandRegistry) -> None:
    """
    Register transaction-related commands with the command registry.
    
    Args:
        registry: The command registry to register commands with
    """
    registry.register("log_transaction", LogTransactionCommand(), "transaction")
    registry.register("view_transactions", ViewTransactionsCommand(), "transaction")
