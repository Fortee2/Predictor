"""Command to remove tickers from a portfolio."""

from rich.prompt import Prompt

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


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

        ticker_input = Prompt.ask(
            "[bold]Enter ticker symbols to remove[/bold] (separated by spaces)"
        )
        ticker_symbols = ticker_input.upper().split()

        if ticker_symbols:
            if ui.confirm_action(
                f"Remove {len(ticker_symbols)} ticker(s) from portfolio #{portfolio_id}?"
            ):
                with ui.progress("Removing tickers...") as progress:
                    progress.add_task("", total=None)
                    cli.cli.remove_tickers(portfolio_id, ticker_symbols)

                ui.status_message(
                    f"Tickers removed from portfolio: {portfolio['name']}", "success"
                )
        else:
            ui.status_message("No tickers specified for removal.", "warning")
