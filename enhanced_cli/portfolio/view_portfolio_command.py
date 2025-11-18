"""Command to view and manage a portfolio."""

from datetime import datetime

from rich.prompt import Prompt

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


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
            view_date: Optional date to view portfolio as of that date
        """
        from enhanced_cli.portfolio.add_tickers_command import AddTickersCommand
        from enhanced_cli.portfolio.list_portfolios_command import ListPortfoliosCommand
        from enhanced_cli.portfolio.remove_tickers_command import RemoveTickersCommand

        portfolio_id = kwargs.get("portfolio_id")
        view_date = kwargs.get("view_date")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # List portfolios and ask for selection
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)

                try:
                    portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to view[/bold]"))
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return

        # Ask for view date if not provided
        if view_date is None and ui.confirm_action("View portfolio as of a specific historical date?"):
            while True:
                view_date = Prompt.ask("[bold]Enter view date[/bold] (YYYY-MM-DD, or leave empty for today)")
                if view_date == "":
                    view_date = None
                    break
                try:
                    datetime.strptime(view_date, "%Y-%m-%d")
                    break
                except ValueError:
                    ui.status_message("Invalid date format. Please use YYYY-MM-DD.", "error")

        with ui.progress("Loading portfolio details...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)

        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return

        # Portfolio header with date info
        header_text = portfolio["name"]
        if view_date:
            header_text += f" (as of {view_date})"
        ui.console.print(ui.header(header_text, f"Portfolio #{portfolio_id}"))

        # Portfolio details
        ui.console.print(f"[bold]Description:[/bold] {portfolio['description']}")
        ui.console.print(
            f"[bold]Status:[/bold] {'[green]Active[/green]' if portfolio['active'] else '[red]Inactive[/red]'}"
        )
        ui.console.print(f"[bold]Date Added:[/bold] {portfolio['date_added'].strftime('%Y-%m-%d')}")

        # Parse view date for calculations
        calculation_date = None
        use_current_prices = True
        if view_date:
            try:
                calculation_date = datetime.strptime(view_date, "%Y-%m-%d").date()
                use_current_prices = calculation_date == datetime.now().date()
            except ValueError:
                ui.status_message("Invalid date format, using current date", "warning")

        # Get and display cash balance (historical if date specified)
        cash_balance = cli.cli.portfolio_dao.get_cash_balance(portfolio_id, calculation_date)
        cash_label = "Cash Balance"
        if view_date:
            cash_label += f" (as of {view_date})"
        ui.console.print(f"[bold]{cash_label}:[/bold] [green]${cash_balance:.2f}[/green]")

        # Use the universal value service for consistent calculations
        with ui.progress("Calculating portfolio value...") as progress:
            progress.add_task("", total=None)
            # Use the universal value service with historical date support
            portfolio_result = cli.cli.value_service.calculate_portfolio_value(
                portfolio_id,
                calculation_date=calculation_date,
                include_cash=True,
                include_dividends=False,  # Don't include dividends in current view
                use_current_prices=use_current_prices,
            )

        # Current Holdings Table
        columns = [
            {"header": "Symbol", "style": "cyan"},
            {"header": "Shares", "justify": "right"},
            {"header": "Avg Cost", "justify": "right", "style": "yellow"},
            {"header": "Current Price", "justify": "right"},
            {"header": "Value", "justify": "right"},
            {"header": "Weight %", "justify": "right", "style": "magenta"},
            {"header": "Gain/Loss", "justify": "right"},
            {"header": "Percent", "justify": "right"},
        ]

        rows = []

        if portfolio_result["positions"]:
            for ticker_id, position in portfolio_result["positions"].items():
                # Color formatting for gain/loss values
                gl_color = "green" if position["gain_loss"] >= 0 else "red"
                gl_formatted = f"[{gl_color}]${position['gain_loss']:.2f}[/{gl_color}]"
                percent_formatted = f"[{gl_color}]{position['gain_loss_pct']:.2f}%[/{gl_color}]"

                if position["shares"] > 0:
                    rows.append(
                        [
                            position["symbol"],
                            f"{position['shares']:.2f}",
                            f"${position['avg_price']:.2f}",
                            f"${position['current_price']:.2f}",
                            f"${position['position_value']:.2f}",
                            f"{position['weight_pct']:.1f}%",
                            gl_formatted,
                            percent_formatted,
                        ]
                    )
        else:
            rows.append(["[italic]No current holdings[/italic]", "", "", "", "", "", "", ""])

        holdings_table = ui.data_table("Current Holdings", columns, rows)
        ui.console.print(holdings_table)

        # Display portfolio value summary
        ui.console.print(f"[bold]Stock Value:[/bold] [green]${portfolio_result['stock_value']:.2f}[/green]")
        ui.console.print(f"[bold]Cash Balance:[/bold] [green]${portfolio_result['cash_balance']:.2f}[/green]")
        ui.console.print(f"[bold]Total Portfolio Value:[/bold] [green]${portfolio_result['total_value']:.2f}[/green]")

        # Portfolio Actions Menu
        options = {
            "1": "Add Tickers",
            "2": "Remove Tickers",
            "3": "Log Transaction",
            "4": "View Transactions",
            "5": "Analyze Portfolio",
            "6": "View Performance",
            "7": "Manage Cash",
            "8": "Back to Main Menu",
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
