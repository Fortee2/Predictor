from data.utility import DatabaseConnectionPool
from data.watch_list_dao import WatchListDAO
from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui
from rich.prompt import Prompt

class ListWatchListsCommand(Command):
    """Command to list all watchlists."""

    def __init__(self):
        super().__init__("List Watch Lists", "Display all watch lists")
        self.pool = DatabaseConnectionPool()
        self.watch_list_dao = WatchListDAO(self.pool)

    @error_handler("listing watchlists")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to list all watch lists.

        Args:
            cli: The CLI instance
        """
        with ui.progress("Loading watch lists...") as progress:
            progress.add_task("", total=None)
            watch_lists = self.watch_list_dao.get_watch_list()

        if not watch_lists:
            ui.status_message("No watch lists found.", "warning")
            if ui.confirm_action("Create a new watch list?"):
                # Lazy import to avoid circular dependency
                from enhanced_cli.watchlist.create_watchlists_command import CreateWatchListCommand
                
                create_command = CreateWatchListCommand()
                create_command.execute(cli)
            return

        # Prepare table columns
        columns = [
            {"header": "ID", "style": "cyan"},
            {"header": "Name", "style": "green"},
            {"header": "Description"},
            {"header": "Tickers", "style": "magenta"},
            {"header": "Date Created"},
        ]

        # Prepare table rows
        rows = []
        for wl in watch_lists:
            ticker_count = len(self.watch_list_dao.get_tickers_in_watch_list(wl["id"]))

            rows.append(
                [
                    str(wl["id"]),
                    wl["name"],
                    wl["description"] or "",
                    str(ticker_count),
                    wl["date_created"].strftime("%Y-%m-%d"),
                ]
            )

        # Display the table
        table = ui.data_table("Your Watch Lists", columns, rows)
        ui.console.print(table)

        # Ask if user wants to view a specific watch list
        if ui.confirm_action("View a specific watch list?"):
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
                # Lazy import to avoid circular dependency
                from enhanced_cli.watchlist.view_watch_list_command import ViewWatchListCommand
                
                view_command = ViewWatchListCommand()
                view_command.execute(cli, watch_list_id=watch_list_id)
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
