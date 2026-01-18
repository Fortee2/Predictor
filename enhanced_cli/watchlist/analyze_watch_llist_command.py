from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui
from rich.prompt import Prompt

class AnalyzeWatchListCommand(Command):
    """Command to analyze tickers in a watchlist."""

    def __init__(self):
        super().__init__("Analyze Watch List", "Analyze tickers in a watchlist")

    @error_handler("analyzing watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to analyze tickers in a watchlist.

        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
            ticker_symbol: Optional ticker symbol to analyze
        """
        watch_list_id = kwargs.get("watch_list_id")
        ticker_symbol = kwargs.get("ticker_symbol")

        if watch_list_id is None:
            # Lazy import to avoid circular dependency
            from enhanced_cli.watchlist.list_watch_lists_command import ListWatchListsCommand
            
            # First list watch lists for selection
            list_command = ListWatchListsCommand()
            list_command.execute(cli)

            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return

        # Get watch list details
        watch_list = cli.watch_list_dao.get_watch_list(watch_list_id)
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return

        # Get tickers in watch list
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)

        if not tickers:
            ui.status_message("This watch list has no tickers to analyze.", "warning")
            return

        # Ask if they want to analyze a specific ticker
        if ticker_symbol is None:
            ui.console.print("[bold]Available Tickers:[/bold]")
            for ticker in tickers:
                ui.console.print(f"- {ticker['symbol']}")

            analyze_all = ui.confirm_action("Analyze all tickers?", True)
            if not analyze_all:
                ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to analyze[/bold]").upper()
                # Check if ticker exists in the watch list
                ticker_exists = any(t["symbol"] == ticker_symbol for t in tickers)
                if not ticker_exists:
                    ui.status_message(f"Ticker {ticker_symbol} not found in this watch list.", "error")
                    return

        header_text = f"Analyzing Watch List: {watch_list['name']}"
        if ticker_symbol:
            header_text += f" - {ticker_symbol}"
        ui.console.print(ui.section_header(header_text))

        with ui.progress("Running analysis...") as progress:
            progress.add_task("", total=None)

        ui.wait_for_user()
