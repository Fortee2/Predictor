"""Command to update notes for a ticker in a watchlist."""

from rich.prompt import Prompt

from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui


class UpdateTickerNotesCommand(Command):
    """Command to update notes for a ticker in a watchlist."""

    def __init__(self):
        super().__init__("Update Ticker Notes", "Update notes for a ticker in a watchlist")

    @error_handler("updating ticker notes")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to update notes for a ticker in a watchlist.

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

        # Get watch list tickers
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)

        if not tickers:
            ui.status_message("This watch list has no tickers.", "warning")
            return

        # Show current tickers with notes
        columns = [{"header": "Symbol", "style": "cyan"}, {"header": "Notes"}]

        rows = []
        for ticker in tickers:
            rows.append([ticker["symbol"], ticker["notes"] or ""])

        table = ui.data_table("Current Tickers", columns, rows)
        ui.console.print(table)

        ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to update[/bold]").upper()

        # Check if ticker exists in the watch list
        ticker_exists = any(t["symbol"] == ticker_symbol for t in tickers)
        if not ticker_exists:
            ui.status_message(f"Ticker {ticker_symbol} not found in this watch list.", "error")
            return

        # Get current notes
        current_notes = next((t["notes"] for t in tickers if t["symbol"] == ticker_symbol), "")
        notes = Prompt.ask("[bold]Enter new notes[/bold]", default=current_notes or "")

        if ui.confirm_action(f"Update notes for {ticker_symbol}?"):
            with ui.progress("Updating notes...") as progress:
                progress.add_task("", total=None)
                cli.update_watch_list_ticker_notes(watch_list_id, ticker_symbol, notes)

            ui.status_message("Notes updated successfully", "success")
