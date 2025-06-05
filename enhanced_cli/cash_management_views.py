"""
Cash management views and commands for the Enhanced CLI.

This module provides commands for cash management operations such as
viewing cash balances, depositing, and withdrawing cash.
"""

from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from datetime import datetime

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class ManageCashCommand(Command):
    """Command to manage portfolio cash balance."""
    
    def __init__(self):
        super().__init__("Manage Cash", "Manage portfolio cash balance")
    
    @error_handler("managing cash")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to manage cash balance.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # First list portfolios for selection
            from enhanced_cli.portfolio_views import ListPortfoliosCommand
            list_command = ListPortfoliosCommand()
            list_command.execute(cli)
            
            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return
        
        # Get portfolio info
        with ui.progress("Loading portfolio details...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
            
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
        
        # Current cash balance
        cash_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id)
        
        ui.console.print(ui.section_header(f"Cash Management for {portfolio['name']}"))
        ui.console.print(f"[bold]Current Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]")
        
        # Cash management actions
        options = {
            "1": "Deposit Cash",
            "2": "Withdraw Cash",
            "3": "View Cash Transactions",
            "4": "Return to Portfolio"
        }
        
        choice = ui.menu("Select Action", options)
        
        if choice == "1":  # Deposit
            amount = float(Prompt.ask("[bold]Enter deposit amount ($)[/bold]", default="0.00"))
            
            if amount <= 0:
                ui.status_message("Amount must be greater than zero.", "error")
                return
                
            if ui.confirm_action(f"Deposit ${amount:.2f} to {portfolio['name']}?"):
                date_str = datetime.now().strftime('%Y-%m-%d')
                description = f"Deposit to {portfolio['name']}"
                
                with ui.progress("Processing deposit...") as progress:
                    progress.add_task("", total=None)
                    # Use the log_cash_transaction method which updates both history and balance
                    new_balance = cli.cli.portfolio_dao.log_cash_transaction(
                        portfolio_id, 
                        amount, 
                        "deposit",
                        description
                    )
                
                ui.status_message(f"Deposited ${amount:.2f} successfully", "success")
                ui.console.print(f"[bold]New Cash Balance:[/bold] [green]${new_balance:.2f}[/green]")
                
        elif choice == "2":  # Withdraw
            amount = float(Prompt.ask("[bold]Enter withdrawal amount ($)[/bold]", default="0.00"))
            
            if amount <= 0:
                ui.status_message("Amount must be greater than zero.", "error")
                return
                
            if amount > cash_balance:
                ui.status_message(
                    f"Warning: Requested amount (${amount:.2f}) exceeds available balance (${cash_balance:.2f})",
                    "warning"
                )
                if not ui.confirm_action("Continue with withdrawal anyway?", False):
                    ui.status_message("Withdrawal cancelled.", "info")
                    return
            
            if ui.confirm_action(f"Withdraw ${amount:.2f} from {portfolio['name']}?"):
                date_str = datetime.now().strftime('%Y-%m-%d')
                description = f"Withdrawal from {portfolio['name']}"
                
                with ui.progress("Processing withdrawal...") as progress:
                    progress.add_task("", total=None)
                    # Use negative amount for withdrawal
                    new_balance = cli.cli.portfolio_dao.log_cash_transaction(
                        portfolio_id, 
                        -amount,  # Negative amount for withdrawal
                        "withdrawal",
                        description
                    )
                
                ui.status_message(f"Withdrew ${amount:.2f} successfully", "success")
                ui.console.print(f"[bold]New Cash Balance:[/bold] [green]${new_balance:.2f}[/green]")

        elif choice == "3":  # View cash transactions
            self.view_cash_transactions(cli, portfolio_id)
        
        # Return to portfolio view automatically if the user selected option 4 
        # or after completing an action
        if choice == "4" or ui.confirm_action("Return to portfolio view?", True):
            from enhanced_cli.portfolio_views import ViewPortfolioCommand
            view_command = ViewPortfolioCommand()
            view_command.execute(cli, portfolio_id=portfolio_id)
    
    @error_handler("viewing cash transactions")
    def view_cash_transactions(self, cli, portfolio_id: int) -> None:
        """
        View cash transactions for a portfolio.
        
        Args:
            cli: The CLI instance
            portfolio_id: Portfolio ID
        """
        with ui.progress("Loading portfolio details...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
            
            # Create a new approach that can track all cash movements
            # First, get the current cash balance
            current_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id)
            
            # We'll use a direct SQL query to get the cash_balance_history
            connection = cli.cli.portfolio_dao.connection
            cursor = connection.cursor(dictionary=True)
            
            try:
                check_table_query = """
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'cash_balance_history'
                """
                cursor.execute(check_table_query)
                table_exists = cursor.fetchone()['count'] > 0
                
                if not table_exists:
                    # Create the table to track cash balance history
                    create_table_query = """
                        CREATE TABLE cash_balance_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            portfolio_id INT NOT NULL,
                            transaction_date DATETIME NOT NULL,
                            amount DECIMAL(10,2) NOT NULL,
                            transaction_type VARCHAR(20) NOT NULL,
                            description VARCHAR(255),
                            balance_after DECIMAL(10,2) NOT NULL,
                            FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
                        )
                    """
                    cursor.execute(create_table_query)
                    connection.commit()
                
                # Get initial portfolio creation details
                query_initial = "SELECT cash_balance, date_added FROM portfolio WHERE id = %s"
                cursor.execute(query_initial, (portfolio_id,))
                initial_data = cursor.fetchone()
                initial_cash = float(initial_data['cash_balance']) if initial_data and 'cash_balance' in initial_data else 0
                creation_date = initial_data['date_added'] if initial_data else datetime.now()
                
                # Check if we already have a record of the initial deposit
                check_initial_query = """
                    SELECT COUNT(*) as count
                    FROM cash_balance_history
                    WHERE portfolio_id = %s
                    AND transaction_type = 'initial'
                """
                cursor.execute(check_initial_query, (portfolio_id,))
                has_initial = cursor.fetchone()['count'] > 0
                
                # Record the initial funding if not already recorded
                if not has_initial and initial_cash > 0:
                    initial_query = """
                        INSERT INTO cash_balance_history 
                        (portfolio_id, transaction_date, amount, transaction_type, description, balance_after)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    initial_values = (
                        portfolio_id, 
                        creation_date, 
                        initial_cash, 
                        'initial', 
                        'Initial portfolio funding', 
                        initial_cash
                    )
                    cursor.execute(initial_query, initial_values)
                    connection.commit()
                
                # Get cash transactions from our history table
                query_history = """
                    SELECT * FROM cash_balance_history
                    WHERE portfolio_id = %s
                    ORDER BY transaction_date DESC
                """
                cursor.execute(query_history, (portfolio_id,))
                cash_transactions = cursor.fetchall()
                
                # Get all buy, sell, and dividend transactions to ensure we haven't missed any
                query_transactions = """
                    SELECT 
                        transaction_date, 
                        transaction_type,
                        shares, 
                        price, 
                        amount,
                        tk.ticker as symbol
                    FROM portfolio_transactions pt
                    JOIN portfolio_securities ps ON pt.security_id = ps.id
                    JOIN tickers tk ON ps.ticker_id = tk.id
                    WHERE pt.portfolio_id = %s
                    ORDER BY transaction_date ASC
                """
                cursor.execute(query_transactions, (portfolio_id,))
                stock_transactions = cursor.fetchall()
                
                # Check if we have any new stock transactions to track for cash impact
                for t in stock_transactions:
                    # Check if this transaction is already in our cash history
                    check_query = """
                        SELECT COUNT(*) as count
                        FROM cash_balance_history
                        WHERE portfolio_id = %s
                        AND transaction_date = %s
                        AND description LIKE %s
                    """
                    description_pattern = f"%{t['symbol']}%"
                    check_values = (portfolio_id, t['transaction_date'], description_pattern)
                    cursor.execute(check_query, check_values)
                    already_tracked = cursor.fetchone()['count'] > 0
                    
                    if not already_tracked:
                        # Calculate cash impact
                        cash_impact = 0
                        transaction_type = ''
                        description = ''
                        
                        if t['transaction_type'] == 'buy':
                            # Buy transactions decrease cash
                            shares = float(t['shares']) if hasattr(t['shares'], 'as_tuple') else float(t['shares'])
                            price = float(t['price']) if hasattr(t['price'], 'as_tuple') else float(t['price'])
                            cash_impact = -(shares * price)
                            transaction_type = 'buy'
                            description = f"Purchase of {shares} {t['symbol']} at ${price}"
                        elif t['transaction_type'] == 'sell':
                            # Sell transactions increase cash
                            shares = float(t['shares']) if hasattr(t['shares'], 'as_tuple') else float(t['shares'])
                            price = float(t['price']) if hasattr(t['price'], 'as_tuple') else float(t['price'])
                            cash_impact = shares * price
                            transaction_type = 'sell'
                            description = f"Sale of {shares} {t['symbol']} at ${price}"
                        elif t['transaction_type'] == 'dividend':
                            # Dividend transactions increase cash
                            cash_impact = float(t['amount']) if hasattr(t['amount'], 'as_tuple') else float(t['amount'])
                            transaction_type = 'dividend'
                            description = f"Dividend from {t['symbol']}"
                        
                        if cash_impact != 0:
                            # Get the latest balance before this transaction
                            balance_query = """
                                SELECT balance_after
                                FROM cash_balance_history
                                WHERE portfolio_id = %s
                                AND transaction_date <= %s
                                ORDER BY transaction_date DESC
                                LIMIT 1
                            """
                            cursor.execute(balance_query, (portfolio_id, t['transaction_date']))
                            balance_result = cursor.fetchone()
                            prior_balance = float(balance_result['balance_after']) if balance_result else initial_cash
                            
                            # Calculate new balance
                            new_balance = prior_balance + cash_impact
                            
                            # Record this cash impact
                            insert_query = """
                                INSERT INTO cash_balance_history 
                                (portfolio_id, transaction_date, amount, transaction_type, description, balance_after)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            insert_values = (
                                portfolio_id, 
                                t['transaction_date'], 
                                cash_impact, 
                                transaction_type, 
                                description, 
                                new_balance
                            )
                            cursor.execute(insert_query, insert_values)
                            connection.commit()
                
                # Get the updated cash transaction history
                query_history = """
                    SELECT * FROM cash_balance_history
                    WHERE portfolio_id = %s
                    ORDER BY transaction_date DESC
                """
                cursor.execute(query_history, (portfolio_id,))
                cash_transactions = cursor.fetchall()
                
            except Exception as e:
                ui.status_message(
                    f"Note: Enhanced cash tracking is not available. Using simplified view. Error: {str(e)}",
                    "warning"
                )
                # Get the initial cash when portfolio was created
                query_initial = "SELECT cash_balance FROM portfolio WHERE id = %s"
                cursor.execute(query_initial, (portfolio_id,))
                initial_result = cursor.fetchone()
                initial_cash = float(initial_result['cash_balance']) if initial_result and 'cash_balance' in initial_result else 0
                
                # Get all transactions that affected cash
                query_transactions = """
                    SELECT 
                        transaction_date, 
                        transaction_type,
                        shares, 
                        price, 
                        amount,
                        tk.ticker as symbol
                    FROM portfolio_transactions pt
                    JOIN portfolio_securities ps ON pt.security_id = ps.id
                    JOIN tickers tk ON ps.ticker_id = tk.id
                    WHERE pt.portfolio_id = %s
                    ORDER BY transaction_date ASC
                """
                cursor.execute(query_transactions, (portfolio_id,))
                all_transactions = cursor.fetchall()
                
                # Build synthetic cash transactions list with running balance
                cash_transactions = []
                running_balance = initial_cash
                
                # Add initial deposit as first transaction if portfolio had initial cash
                if initial_cash > 0:
                    creation_date = portfolio['date_added']
                    cash_transactions.append({
                        'transaction_date': creation_date,
                        'amount': initial_cash,
                        'transaction_type': 'initial',
                        'description': 'Initial portfolio cash',
                        'balance_after': initial_cash
                    })
                
                # Process each transaction to determine cash flow
                for t in all_transactions:
                    cash_impact = 0
                    description = ''
                    transaction_type = ''
                    
                    if t['transaction_type'] == 'buy':
                        # Buy transactions decrease cash
                        shares = float(t['shares']) if hasattr(t['shares'], 'as_tuple') else float(t['shares'])
                        price = float(t['price']) if hasattr(t['price'], 'as_tuple') else float(t['price'])
                        cash_impact = -(shares * price)
                        transaction_type = 'buy'
                        description = f"Purchase of {shares} {t['symbol']} at ${price}"
                    elif t['transaction_type'] == 'sell':
                        # Sell transactions increase cash
                        shares = float(t['shares']) if hasattr(t['shares'], 'as_tuple') else float(t['shares'])
                        price = float(t['price']) if hasattr(t['price'], 'as_tuple') else float(t['price'])
                        cash_impact = shares * price
                        transaction_type = 'sell'
                        description = f"Sale of {shares} {t['symbol']} at ${price}"
                    elif t['transaction_type'] == 'dividend':
                        # Dividend transactions increase cash
                        cash_impact = float(t['amount']) if hasattr(t['amount'], 'as_tuple') else float(t['amount'])
                        transaction_type = 'dividend'
                        description = f"Dividend from {t['symbol']}"
                    
                    if cash_impact != 0:
                        running_balance += cash_impact
                        cash_transactions.append({
                            'transaction_date': t['transaction_date'],
                            'amount': cash_impact,
                            'transaction_type': transaction_type,
                            'description': description,
                            'balance_after': running_balance
                        })
                        
                # Sort by date, newest first
                cash_transactions = sorted(cash_transactions, key=lambda x: x['transaction_date'], reverse=True)
                
            finally:
                cursor.close()
        
        ui.console.print(ui.section_header(f"Cash Transaction History for {portfolio['name']}"))
        
        if not cash_transactions:
            ui.status_message("No cash transactions found for this portfolio.", "warning")
            
            # Show helpful information about cash management
            ui.console.print("\n[bold]To manage cash in this portfolio:[/bold]")
            ui.console.print("1. Use the 'Deposit Cash' or 'Withdraw Cash' options in the Cash Management menu")
            ui.console.print("2. The system will automatically track cash flows from buy/sell/dividend transactions")
            return
        
        # Prepare table columns
        columns = [
            {'header': 'Date', 'style': 'cyan'},
            {'header': 'Type', 'style': 'green'},
            {'header': 'Amount', 'justify': 'right'},
            {'header': 'Balance After', 'justify': 'right', 'style': 'bold'},
            {'header': 'Description', 'style': 'dim'}
        ]
        
        # Prepare table rows
        rows = []
        for t in cash_transactions:
            date = t['transaction_date'].strftime('%Y-%m-%d')
            
            # Determine transaction type label
            # Convert amount to float to avoid decimal.Decimal issues
            amount = float(t['amount'])
            
            if t['transaction_type'] == 'initial':
                trans_type = "Initial Funding"
                amount_str = f"[green]+${abs(amount):.2f}[/green]"
            elif t['transaction_type'] == 'buy':
                trans_type = "Purchase"
                amount_str = f"[red]-${abs(amount):.2f}[/red]"
            elif t['transaction_type'] == 'sell':
                trans_type = "Sale"
                amount_str = f"[green]+${abs(amount):.2f}[/green]"
            elif t['transaction_type'] == 'dividend':
                trans_type = "Dividend"
                amount_str = f"[green]+${abs(amount):.2f}[/green]"
            elif t['transaction_type'] == 'deposit':
                trans_type = "Deposit"
                amount_str = f"[green]+${abs(amount):.2f}[/green]"
            elif t['transaction_type'] == 'withdrawal':
                trans_type = "Withdrawal"
                amount_str = f"[red]-${abs(amount):.2f}[/red]"
            else:
                trans_type = "Other"
                if amount > 0:
                    amount_str = f"[green]+${abs(amount):.2f}[/green]"
                else:
                    amount_str = f"[red]-${abs(amount):.2f}[/red]"
            
            # Make sure balance_after is a float too
            balance_after = float(t['balance_after']) if hasattr(t['balance_after'], 'as_tuple') else float(t['balance_after'])
            
            rows.append([
                date,
                trans_type,
                amount_str,
                f"${balance_after:.2f}",
                t['description']
            ])
        
        # Display the table
        table = ui.data_table("Cash Transactions", columns, rows)
        ui.console.print(table)
        ui.wait_for_user()


def register_cash_management_commands(registry: CommandRegistry) -> None:
    """
    Register cash management commands with the command registry.
    
    Args:
        registry: The command registry to register commands with
    """
    registry.register("manage_cash", ManageCashCommand(), "cash_management")
