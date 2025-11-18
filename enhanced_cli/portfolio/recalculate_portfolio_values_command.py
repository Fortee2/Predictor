"""Command to recalculate portfolio historical values."""

from datetime import datetime

from rich.prompt import Prompt

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


class RecalculatePortfolioValuesCommand(Command):
    """Command to recalculate portfolio historical values."""

    def __init__(self):
        super().__init__(
            "Recalculate Portfolio Values", "Recalculate historical portfolio values"
        )

    @error_handler("recalculating portfolio values")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to recalculate portfolio values.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        from enhanced_cli.portfolio.list_portfolios_command import ListPortfoliosCommand

        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # List portfolios and ask for selection
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)

                try:
                    portfolio_id = int(
                        Prompt.ask("[bold]Enter Portfolio ID to recalculate[/bold]")
                    )
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
                f"Recalculate Values for Portfolio #{portfolio_id} - {portfolio['name']}"
            )
        )

        # Ask for start date
        from_date = None
        if ui.confirm_action("Specify a start date for recalculation?"):
            while True:
                date_input = Prompt.ask(
                    "[bold]Start date[/bold] (YYYY-MM-DD format, or leave empty for earliest transaction)"
                )
                if not date_input.strip():
                    from_date = None
                    break
                try:
                    # Validate date format
                    datetime.strptime(date_input, "%Y-%m-%d")
                    from_date = date_input
                    break
                except ValueError:
                    ui.status_message(
                        "Invalid date format. Please use YYYY-MM-DD.", "error"
                    )

        # Show warning about the operation
        ui.console.print("\n[yellow]Warning:[/yellow] This operation will:")
        ui.console.print(
            "• Delete existing portfolio value records from the start date forward"
        )
        ui.console.print(
            "• Recalculate values for each day based on current transaction data"
        )
        ui.console.print("• This may take several minutes for large date ranges")

        if from_date:
            ui.console.print(f"• Starting from: [bold]{from_date}[/bold]")
        else:
            ui.console.print("• Starting from: [bold]earliest transaction date[/bold]")

        if ui.confirm_action("Proceed with portfolio value recalculation?"):
            with ui.progress("Recalculating portfolio values...") as progress:
                # Use optimized recalculation method
                from data.optimized_portfolio_recalculator import (
                    OptimizedPortfolioRecalculator,
                )

                # Use the database connection pool from CLI
                optimizer = OptimizedPortfolioRecalculator(cli.cli.db_pool)

                if from_date:
                    # Manual date specified - use specific date recalculation
                    from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                    result = optimizer.recalculate_from_specific_date(
                        portfolio_id, from_date_obj, "Manual recalculation via CLI"
                    )
                else:
                    # No date specified - find earliest transaction and use optimized method
                    info = optimizer.get_recalculation_info(portfolio_id)

                    if (
                        info.get("transaction_info")
                        and info["transaction_info"]["earliest_transaction"]
                    ):
                        earliest_date = info["transaction_info"]["earliest_transaction"]
                        if hasattr(earliest_date, "date"):
                            earliest_date = earliest_date.date()

                        result = optimizer.smart_recalculate_from_transaction(
                            portfolio_id, earliest_date, force_full_recalc=True
                        )
                    else:
                        ui.status_message(
                            "No transactions found for this portfolio", "warning"
                        )
                        result = False

            if result:
                ui.status_message(
                    "Portfolio values have been successfully recalculated using optimized method!",
                    "success",
                )
            else:
                ui.status_message(
                    "Failed to recalculate portfolio values. Check the output above for details.",
                    "error",
                )
        else:
            ui.status_message("Recalculation cancelled.", "warning")
