from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui
from rich.prompt import Prompt

class CreateWatchListCommand(Command):
    """Command to create a new watchlist."""

    def __init__(self):
        super().__init__("Create Watch List", "Create a new watchlist")

    @error_handler("creating watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to create a new watchlist.

        Args:
            cli: The CLI instance
        """
        ui.console.print(ui.section_header("Create a New Watch List"))

        # Define form fields
        fields = [
            {"name": "name", "prompt": "[bold]Watch List Name[/bold]"},
            {"name": "description", "prompt": "[bold]Description[/bold] (optional)"},
        ]

        # Get form data
        data = ui.input_form(fields)

        if ui.confirm_action(
            f"Create watch list [bold]{data['name']}[/bold] with description: [italic]{data['description']}[/italic]?"
        ):
            with ui.progress("Creating watch list...") as progress:
                progress.add_task("", total=None)
                watch_list_id = cli.create_watch_list(data["name"], data["description"])

            if watch_list_id:
                ui.status_message(
                    f"Watch list created successfully with ID: {watch_list_id}",
                    "success",
                )

                if ui.confirm_action("Would you like to add tickers to this watch list now?"):
                    # Lazy import to avoid circular dependency
                    from enhanced_cli.watchlist.add_tickers_command import AddTickersToWatchListCommand
                    
                    add_tickers_command = AddTickersToWatchListCommand()
                    add_tickers_command.execute(cli, watch_list_id=watch_list_id)
            else:
                ui.status_message("Failed to create watch list", "error")
