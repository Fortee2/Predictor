"""
Data management views and commands for the Enhanced CLI.

This module provides commands for data management operations such as
updating data for all securities in portfolios.
"""

from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from datetime import datetime
from rich.progress import Progress

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


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
        
        with ui.progress("Updating stock data...") as progress:
            progress.add_task("", total=None)
            cli.cli.update_data()
        
        ui.status_message("Data update complete", "success")


def register_data_commands(registry: CommandRegistry) -> None:
    """
    Register data management commands with the command registry.
    
    Args:
        registry: The command registry to register commands with
    """
    registry.register("update_data", UpdateDataCommand(), "data")
