from data.utility import DatabaseConnectionPool
from data.watch_list_dao import WatchListDAO
from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui
from rich.prompt import Prompt

class AddTickersToWatchListCommand(Command):
    """Command to add tickers to a watchlist."""

    def __init__(self):
        super().__init__("Add Tickers to Watch List", "Add tickers to a watchlist")
        self.pool = DatabaseConnectionPool()
        self.watch_list_dao = WatchListDAO(self.pool)

    @error_handler("adding tickers to watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to add tickers to a watchlist.

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

        # Get watch list details for header
        watch_list = self.watch_list_dao.get_watch_list(watch_list_id)
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return

        ui.console.print(ui.section_header(f"Add Tickers to Watch List #{watch_list_id} - {watch_list['name']}"))

        ticker_input = Prompt.ask("[bold]Enter ticker symbols[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()

        if not ticker_symbols:
            ui.status_message("No tickers entered.", "warning")
            return

        notes = Prompt.ask("[bold]Notes[/bold] (optional, will apply to all tickers)")

        if ui.confirm_action(f"Add {len(ticker_symbols)} ticker(s) to watch list #{watch_list_id}?"):
            with ui.progress("Adding tickers...") as progress:
                progress.add_task("", total=None)
                for symbol in ticker_symbols:
                    self.watch_list_dao.add_ticker_to_watch_list(
                        watch_list_id=watch_list_id,
                        ticker_symbol=symbol,
                        notes=notes
                    )

            ui.status_message("Tickers added successfully", "success")
