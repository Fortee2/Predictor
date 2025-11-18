"""Command to log a new transaction."""

from datetime import datetime, timedelta

from rich.prompt import Prompt

from data.utility import DatabaseConnectionPool
from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


class LogTransactionCommand(Command):
    """Command to log a new transaction."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Log Transaction", "Record a new transaction")
        self.pool = pool

    @error_handler("logging transaction")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to log a new transaction.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        from enhanced_cli.portfolio import AddTickersCommand, ListPortfoliosCommand

        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
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

        ui.console.print(
            ui.section_header(
                f"Log Transaction for Portfolio #{portfolio_id} - {portfolio['name']}"
            )
        )

        # Show transaction type options
        options = {
            "1": "Buy",
            "2": "Sell",
            "3": "Dividend",
            "4": "Cash (Deposit/Withdraw)",
        }

        trans_choice = ui.menu("Transaction Types", options)
        trans_type = {"1": "buy", "2": "sell", "3": "dividend", "4": "cash"}[
            trans_choice
        ]

        # For cash transactions, we don't need a ticker
        ticker_symbol = None
        if trans_type != "cash":
            # Get tickers in portfolio
            with ui.progress("Loading portfolio tickers...") as progress:
                progress.add_task("", total=None)
                tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)

            if not tickers and ui.confirm_action(
                "[yellow]No tickers in this portfolio. Add one now?[/yellow]"
            ):
                add_tickers_command = AddTickersCommand()
                add_tickers_command.execute(cli, portfolio_id=portfolio_id)

                with ui.progress("Reloading tickers...") as progress:
                    progress.add_task("", total=None)
                    tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(
                        portfolio_id
                    )

                if not tickers:
                    ui.status_message(
                        "Cannot log transactions without tickers in the portfolio.",
                        "error",
                    )
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
                default=datetime.now().strftime("%Y-%m-%d"),
            )
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                break
            except ValueError:
                ui.status_message(
                    "Invalid date format. Please use YYYY-MM-DD.", "error"
                )

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
            cash_action = Prompt.ask(
                "[bold]Action[/bold]",
                choices=["deposit", "withdraw"],
                default="deposit",
            )
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
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                # Get portfolio value before transaction (previous day or same day before transaction)
                before_date = transaction_date - timedelta(days=1)
                portfolio_before = cli.cli.value_service.calculate_portfolio_value(
                    portfolio_id,
                    calculation_date=before_date,
                    include_cash=True,
                    include_dividends=False,
                    use_current_prices=False,
                )
            except Exception:
                portfolio_before = None

            # Use a separate status for each operation
            with ui.progress("Logging transaction...") as progress:
                progress.add_task("", total=None)
                cli.cli.log_transaction(
                    portfolio_id,
                    trans_type,
                    date_str,
                    ticker_symbol,
                    shares,
                    price,
                    amount,
                )

            # Only show the confirmation after the status context is completed
            ui.status_message("Transaction logged successfully", "success")

            # Show updated portfolio information
            ui.console.print("\n[bold]Portfolio Update:[/bold]")

            # Check cash balance after transaction
            cash_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id)
            ui.console.print(
                f"[bold]Current Cash Balance:[/bold] [green]${cash_balance:.2f}[/green]"
            )

            # Get current portfolio value after transaction
            try:
                portfolio_after = cli.cli.value_service.calculate_portfolio_value(
                    portfolio_id,
                    include_cash=True,
                    include_dividends=False,
                    use_current_prices=True,
                )

                ui.console.print(
                    f"[bold]Current Portfolio Value:[/bold] [green]${portfolio_after['total_value']:,.2f}[/green]"
                )

                # Show change if we have before value
                if portfolio_before and portfolio_before["total_value"] > 0:
                    value_change = (
                        portfolio_after["total_value"] - portfolio_before["total_value"]
                    )
                    change_pct = (value_change / portfolio_before["total_value"]) * 100

                    change_color = "green" if value_change >= 0 else "red"
                    change_sign = "+" if value_change >= 0 else ""

                    ui.console.print(
                        f"[bold]Value Change:[/bold] [{change_color}]{change_sign}${value_change:,.2f} ({change_sign}{change_pct:.2f}%)[/{change_color}]"
                    )

            except Exception as e:
                ui.console.print(
                    f"[yellow]Could not calculate portfolio value change: {e}[/yellow]"
                )

            # Separate prompt for recalculation
            if ui.confirm_action(
                "Would you like to recalculate portfolio history with this new transaction?"
            ):
                with ui.progress("Recalculating portfolio history...") as progress:
                    progress.add_task("", total=None)

                    # Use optimized recalculation starting from transaction date
                    from data.optimized_portfolio_recalculator import (
                        OptimizedPortfolioRecalculator,
                    )

                    optimizer = OptimizedPortfolioRecalculator(self.pool)

                    try:
                        transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        success = optimizer.smart_recalculate_from_transaction(
                            portfolio_id, transaction_date
                        )

                        if success:
                            ui.status_message(
                                "Portfolio history recalculated successfully using optimized method",
                                "success",
                            )
                        else:
                            ui.status_message(
                                "Recalculation completed with some issues - check output above",
                                "warning",
                            )
                    except Exception as e:
                        ui.status_message(
                            f"Error in optimized recalculation: {e}", "error"
                        )
                        # Fall back to original method
                        cli.cli.recalculate_portfolio_history(portfolio_id)
                        ui.status_message(
                            "Fell back to standard recalculation method", "warning"
                        )
