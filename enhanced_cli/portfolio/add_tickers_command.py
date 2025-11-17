"""Command to add tickers to a portfolio."""

from rich.prompt import Prompt

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


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
                f"Add Tickers to Portfolio #{portfolio_id} - {portfolio['name']}"
            )
        )

        ticker_input = Prompt.ask(
            "[bold]Enter ticker symbols[/bold] (separated by spaces)"
        )
        ticker_symbols = ticker_input.upper().split()

        if ticker_symbols:
            with ui.progress("Adding tickers...") as progress:
                progress.add_task("", total=None)
                cli.cli.add_tickers(portfolio_id, ticker_symbols)

            ui.status_message(
                f"Tickers added to portfolio: {portfolio['name']}", "success"
            )
        else:
            ui.status_message("No tickers entered.", "warning")
