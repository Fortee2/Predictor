"""
Data management views and commands for the Enhanced CLI.

This module provides commands for data management operations such as
updating data for all securities in portfolios.
"""

from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui

# Import DataRetrieval lazily to avoid startup delay
# This prevents the initial delay caused by DataRetrieval's initialization


class UpdateDataCommand(Command):
    """Command to update data for all securities in portfolios."""

    def __init__(self):
        super().__init__("Update Data", "Update data for all securities in portfolios")

    @error_handler("updating data")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to update data for all securities.

        Args:
            cli: The CLI instance
        """
        if not ui.confirm_action(
            "[bold]This will update data for all securities in your portfolios. "
            "This may take some time. Continue?[/bold]"
        ):
            return

        # Import here to avoid startup delay
        import os

        from data.data_retrieval_consolidated import DataRetrieval

        # Get database credentials from PortfolioCLI instance
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")

        with ui.progress("Updating stock data...") as progress:
            progress.add_task("", total=None)

            # Create DataRetrieval instance only when needed
            data_retrieval = DataRetrieval(db_user, db_password, db_host, db_name)
            data_retrieval.update_stock_activity()

        ui.status_message("Data update complete", "success")


def register_data_commands(registry: CommandRegistry) -> None:
    """
    Register data management commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("update_data", UpdateDataCommand(), "data")
