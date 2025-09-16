"""
Command pattern implementation for Enhanced CLI menu actions.

This module provides the base Command class and a CommandRegistry for organizing
and managing commands throughout the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console


class Command(ABC):
    """
    Base Command class that encapsulates a specific menu action.

    All CLI commands should inherit from this class and implement the execute method.
    """

    def __init__(self, name: str, description: str):
        """
        Initialize a command with a name and description.

        Args:
            name: The display name of the command
            description: A brief description of what the command does
        """
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, cli, *args, **kwargs) -> Any:
        """
        Execute the command logic.

        Args:
            cli: The CLI instance (provides access to services, DAOs, etc.)
            *args: Positional arguments specific to the command
            **kwargs: Keyword arguments specific to the command

        Returns:
            Result of the command execution, if any
        """
        pass


class CommandRegistry:
    """
    Registry to manage and organize commands.

    This class handles command registration, lookup, and execution.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the command registry.

        Args:
            console: Optional Console instance for output
        """
        self._commands: Dict[str, Command] = {}
        self._categories: Dict[str, List[str]] = {}
        self.console = console or Console()

    def register(
        self, command_id: str, command: Command, category: str = "default"
    ) -> None:
        """
        Register a command with a unique ID in a specific category.

        Args:
            command_id: Unique identifier for the command
            command: Command instance to register
            category: Category to group the command under
        """
        if command_id in self._commands:
            self.console.print(
                f"[bold yellow]Warning: Command {command_id} is being overwritten[/bold yellow]"
            )

        self._commands[command_id] = command

        if category not in self._categories:
            self._categories[category] = []

        if command_id not in self._categories[category]:
            self._categories[category].append(command_id)

    def get_command(self, command_id: str) -> Optional[Command]:
        """
        Get a command by its ID.

        Args:
            command_id: Unique identifier for the command

        Returns:
            Command instance if found, None otherwise
        """
        return self._commands.get(command_id)

    def get_commands_by_category(self, category: str) -> List[Command]:
        """
        Get all commands in a specific category.

        Args:
            category: Category to get commands from

        Returns:
            List of Command instances in the category
        """
        if category not in self._categories:
            return []

        return [
            self._commands[cmd_id]
            for cmd_id in self._categories[category]
            if cmd_id in self._commands
        ]

    def get_categories(self) -> List[str]:
        """
        Get all available command categories.

        Returns:
            List of category names
        """
        return list(self._categories.keys())

    def execute(self, command_id: str, cli, *args, **kwargs) -> Any:
        """
        Execute a command by its ID.

        Args:
            command_id: Unique identifier for the command
            cli: The CLI instance to pass to the command
            *args: Positional arguments to pass to the command
            **kwargs: Keyword arguments to pass to the command

        Returns:
            Result of the command execution, if any

        Raises:
            KeyError: If the command ID is not registered
        """
        if command_id not in self._commands:
            raise KeyError(f"Command '{command_id}' is not registered")

        return self._commands[command_id].execute(cli, *args, **kwargs)


def error_handler(operation_name: str):
    """
    Decorator for error handling in command execution.

    Args:
        operation_name: Name of the operation for error messages

    Returns:
        Decorated function with error handling
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            console = Console()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                console.print(
                    f"[bold red]Error during {operation_name}: {str(e)}[/bold red]"
                )
                import traceback

                console.print("[dim]" + traceback.format_exc() + "[/dim]")
                return None

        return wrapper

    return decorator
