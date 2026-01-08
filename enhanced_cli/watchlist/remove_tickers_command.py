"""Command to remove tickers from a watchlist."""

from rich.prompt import Prompt

from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui


class RemoveTickersFromWatchListCommand(Command):
    """Command to remove tickers from a watchlist."""

    def __init__(self):
        super().__init__("Remove Tickers from Watch List", "Remove tickers from a watchlist")

    @error_handler("removing tickers from watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to remove tickers from a watchlist.

        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
        """
        watch_list_id = kwargs.get("watch_list_id")

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

        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)

        if not tickers:
            ui.status_message("This watch list has no tickers to remove.", "warning")
            return

        # Show current tickers
        ui.console.print("[bold]Current Tickers:[/bold]")
        ticker_symbols = []
        for ticker in tickers:
            ui.console.print(f"- {ticker['symbol']}")
            ticker_symbols.append(ticker["symbol"])

        ticker_input = Prompt.ask("[bold]Enter ticker symbols to remove[/bold] (separated by spaces)")
        to_remove = ticker_input.upper().split()

        valid_tickers = [t for t in to_remove if t in ticker_symbols]
        if not valid_tickers:
            ui.status_message("No valid tickers selected for removal.", "warning")
            return

        if ui.confirm_action(f"Remove {len(valid_tickers)} ticker(s) from watch list #{watch_list_id}?"):
            with ui.progress("Removing tickers...") as progress:
                progress.add_task("", total=None)
                cli.remove_watch_list_ticker(watch_list_id, valid_tickers)

            ui.status_message("Tickers removed successfully", "success")
