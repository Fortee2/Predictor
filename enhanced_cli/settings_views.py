"""
Settings views and commands for the Enhanced CLI.

This module provides commands for managing application settings
such as database connection, UI preferences, and analysis parameters.
"""

from rich.prompt import Prompt

from enhanced_cli.core.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class EditSettingsCommand(Command):
    """Command to edit application settings."""

    def __init__(self):
        super().__init__("Edit Settings", "Edit application settings")

    @error_handler("editing settings")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to edit application settings.

        Args:
            cli: The CLI instance
            category: Settings category to edit
        """
        from data.config import Config

        config = Config()

        # Get the category from kwargs
        section = kwargs.get("category")
        if not section:
            # Show categories menu
            options = {
                "1": "Database Settings",
                "2": "UI Settings",
                "3": "Analysis Settings",
                "4": "Watchlist Settings",
                "5": "Logging Settings",
                "6": "Chart Settings",
                "7": "Back to Main Menu",
            }

            choice = ui.menu("Settings Category", options)

            # Map choice to category
            section = {
                "1": "database",
                "2": "ui",
                "3": "analysis",
                "4": "watchlist",
                "5": "logging",
                "6": "chart",
            }.get(choice)

            if choice == "7" or not section:
                return

        # Get the settings for the selected section
        settings = config.get(section)
        if not settings:
            ui.status_message(f"No settings found for section: {section}", "warning")
            return

        ui.console.print(ui.section_header(f"{section.capitalize()} Settings"))

        # Display current settings
        columns = [
            {"header": "Setting", "style": "cyan"},
            {"header": "Value", "style": "green"},
        ]

        rows = []
        for key, value in settings.items():
            rows.append([key, str(value)])

        table = ui.data_table("Current Settings", columns, rows)
        ui.console.print(table)

        # Ask which setting to change
        setting_keys = list(settings.keys())
        options = {str(i + 1): key for i, key in enumerate(setting_keys)}
        options[str(len(options) + 1)] = "Back"

        ui.console.print("\n[bold]Select setting to change:[/bold]")
        choice = ui.menu("Settings", options)

        if choice == str(len(options)):  # Back option
            return

        # Get the key and current value
        key_to_change = options[choice]
        current_value = settings[key_to_change]

        # Handle different setting types
        if isinstance(current_value, bool):
            new_value = ui.confirm_action(f"Enable {key_to_change}?", default=current_value)
        elif isinstance(current_value, int):
            try:
                new_value = int(
                    Prompt.ask(
                        f"Enter new value for {key_to_change}",
                        default=str(current_value),
                    )
                )
            except ValueError:
                ui.status_message("Invalid input. Please enter a number.", "error")
                return
        elif isinstance(current_value, float):
            try:
                new_value = float(
                    Prompt.ask(
                        f"Enter new value for {key_to_change}",
                        default=str(current_value),
                    )
                )
            except ValueError:
                ui.status_message("Invalid input. Please enter a number.", "error")
                return
        else:
            new_value = Prompt.ask(f"Enter new value for {key_to_change}", default=str(current_value))

        # Update the setting if changed
        if new_value != current_value:
            config.set(section, key_to_change, new_value)
            if config.save_config():
                ui.status_message(f"Setting updated: {key_to_change} = {new_value}", "success")
            else:
                ui.status_message("Failed to save settings", "error")
        else:
            ui.status_message("No changes made", "warning")

        # Ask if they want to edit another setting in this section
        if ui.confirm_action("Edit another setting in this section?"):
            self.execute(cli, category=section)


def register_settings_commands(registry: CommandRegistry) -> None:
    """
    Register settings-related commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("edit_settings", EditSettingsCommand(), "settings")
