"""Command to delete a watchlist."""

from rich.prompt import Prompt

from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui


class DeleteWatchListCommand(Command):
    """Command to delete a watchlist."""

    def __init__(self):
        super().__init__("Delete Watch List", "Delete a watchlist")

    @error_handler("deleting watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to delete a watchlist.

        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID to delete
        """
        watch_list_id = kwargs.get("watch_list_id")

        if watch_list_id is None:
            # First list watch lists for selection
            with ui.progress("Loading watch lists...") as progress:
                progress.add_task("", total=None)
                watch_lists = cli.watch_list_dao.get_watch_list()

            if not watch_lists:
                ui.status_message("No watch lists found.", "warning")
                return

            # Show table for selection
            columns = [
                {"header": "ID", "style": "cyan"},
                {"header": "Name", "style": "green"},
                {"header": "Tickers", "style": "magenta"},
            ]

            rows = []
            for wl in watch_lists:
                ticker_count = len(cli.watch_list_dao.get_tickers_in_watch_list(wl["id"]))
                rows.append([str(wl["id"]), wl["name"], str(ticker_count)])

            table = ui.data_table("Your Watch Lists", columns, rows)
            ui.console.print(table)

            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to delete[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return

        # Get watch list details for confirmation
        with ui.progress("Loading watch list details...") as progress:
            progress.add_task("", total=None)
            watch_list = cli.watch_list_dao.get_watch_list(watch_list_id)

        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return

        # Confirm deletion with a stronger warning
        if ui.confirm_action(
            f"[bold red]Are you sure you want to delete watch list '{watch_list['name']}'? "
            f"This cannot be undone.[/bold red]",
            default=False,
        ):
            with ui.progress("Deleting watch list...") as progress:
                progress.add_task("", total=None)
                cli.delete_watch_list(watch_list_id)

            ui.status_message("Watch list deleted successfully", "success")
