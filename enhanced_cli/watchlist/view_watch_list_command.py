from data.utility import DatabaseConnectionPool
from data.watch_list_dao import WatchListDAO
from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui
from rich.prompt import Prompt

from enhanced_cli.watchlist.add_tickers_command import AddTickersToWatchListCommand
from enhanced_cli.watchlist.analyze_watch_llist_command import AnalyzeWatchListCommand
from enhanced_cli.watchlist.remove_tickers_command import RemoveTickersFromWatchListCommand
from enhanced_cli.watchlist.update_ticker_notes_command import UpdateTickerNotesCommand


class ViewWatchListCommand(Command):
    """Command to view and manage a watchlist."""

    def __init__(self):
        super().__init__("View Watch List", "View and manage a watchlist")
        self.pool = DatabaseConnectionPool()
        self.watch_list_dao = WatchListDAO(self.pool)

    @error_handler("viewing watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view and manage a watchlist.

        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID to view
        """
        watch_list_id = kwargs.get("watch_list_id")

        if watch_list_id is None:
            # Get all watch lists
            with ui.progress("Loading watch lists...") as progress:
                progress.add_task("", total=None)
                watch_lists = self.watch_list_dao.get_watch_list()

            if not watch_lists:
                ui.status_message("No watch lists found.", "warning")
                return

            # Display basic table to select from
            columns = [
                {"header": "ID", "style": "cyan"},
                {"header": "Name", "style": "green"},
            ]

            rows = []
            for wl in watch_lists:
                rows.append([str(wl["id"]), wl["name"]])

            table = ui.data_table("Your Watch Lists", columns, rows)
            ui.console.print(table)

            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to view[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return

        # Get watch list details
        with ui.progress("Loading watch list details...") as progress:
            progress.add_task("", total=None)
            watch_list = self.watch_list_dao.get_watch_list(watch_list_id)

        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return

        # Watch List header
        ui.console.print(ui.header(watch_list["name"], f"Watch List #{watch_list_id}"))

        # Watch List details
        if watch_list["description"]:
            ui.console.print(f"[bold]Description:[/bold] {watch_list['description']}")
        ui.console.print(f"[bold]Date Created:[/bold] {watch_list['date_created'].strftime('%Y-%m-%d')}")

        # Get tickers in watch list
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = self.watch_list_dao.get_tickers_in_watch_list(watch_list_id)

        if tickers:
            # Prepare ticker table columns
            columns = [
                {"header": "Symbol", "style": "cyan"},
                {"header": "Name"},
                {"header": "Notes"},
                {"header": "Date Added"},
            ]

            # Prepare ticker table rows
            rows = []
            for ticker in tickers:
                rows.append(
                    [
                        ticker["symbol"],
                        ticker["name"],
                        ticker["notes"] or "",
                        ticker["date_added"].strftime("%Y-%m-%d"),
                    ]
                )

            # Display the ticker table
            ticker_table = ui.data_table("Tickers in Watch List", columns, rows)
            ui.console.print(ticker_table)
        else:
            ui.status_message("No tickers in this watch list.", "warning")

        # Watch List Actions Menu
        options = {
            "1": "Add Tickers",
            "2": "Remove Tickers",
            "3": "Update Ticker Notes",
            "4": "Analyze Watch List",
            "5": "Back to Watch Lists",
        }

        choice = ui.menu("Watch List Actions", options)

        if choice == "1":
            add_tickers_command = AddTickersToWatchListCommand()
            add_tickers_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "2":
            remove_tickers_command = RemoveTickersFromWatchListCommand()
            remove_tickers_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "3":
            update_notes_command = UpdateTickerNotesCommand()
            update_notes_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "4":
            analyze_command = AnalyzeWatchListCommand()
            analyze_command.execute(cli, watch_list_id=watch_list_id)
        # choice 5 returns to watch list menu
