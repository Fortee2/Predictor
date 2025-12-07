# Enhanced CLI - Portfolio & Stock Management System

This package contains a refactored, modular implementation of the Enhanced CLI for the Portfolio & Stock Management System. The code has been restructured for better maintainability, separation of concerns, and extensibility.

## Architecture

The enhanced CLI follows the Command pattern and a modular architecture with clear separation of concerns:

```
enhanced_cli/
├── __init__.py           # Package exports
├── main.py               # Application entry point and coordination
├── command.py            # Command pattern implementation
├── ui_components.py      # Reusable UI components
├── formatters.py         # Data formatting utilities
├── portfolio_views.py    # Portfolio management commands
├── transaction_views.py  # Transaction management commands
├── analysis_views.py     # Analysis operations
├── watchlist_views.py    # Watchlist management
├── settings_views.py     # Settings management
├── cash_management_views.py # Cash operations
├── data_views.py         # Data update operations
└── stubs.py              # Stubs to resolve circular imports
```

## Design Patterns

### Command Pattern
The application uses the Command pattern to encapsulate menu actions as command objects. This enables:
- Decoupling the request for an operation from its execution
- Easy addition of new commands without modifying existing code
- Consistent error handling across all commands

### Model-View Separation
Each view module focuses on user interaction while delegating actual data operations to the underlying model (portfolio_cli.py). This separation:
- Keeps the UI logic separate from business logic
- Makes code easier to test
- Prevents duplication of business logic across UI components

### Factory Pattern
UI components are created via a factory class that ensures consistent styling and behavior across the application.

## Key Components

### Command Registry
The `CommandRegistry` class manages all available commands and their execution. Commands are organized by categories for easier navigation.

### UI Components
The `UIComponents` class provides factory methods for creating consistent UI elements:
- Tables
- Headers
- Forms
- Confirmation prompts
- Status messages
- Progress indicators

### Error Handling
A centralized error handling decorator (`error_handler`) provides consistent error reporting across all commands.

## How to Add New Commands

1. Determine which module your command belongs in, or create a new one if needed
2. Create a new command class that inherits from `Command`
3. Implement the `execute()` method that performs the command's action
4. Add a registration function to register the command with the command registry
5. Update the stubs.py file with a stub for your registration function
6. Update main.py to import and call your registration function

Example:

```python
# In your_module.py
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui

class YourCommand(Command):
    def __init__(self):
        super().__init__("Your Command", "Description of your command")
    
    @error_handler("performing your command")
    def execute(self, cli, *args, **kwargs) -> None:
        # Implementation here
        pass

def register_your_commands(registry: CommandRegistry) -> None:
    registry.register("your_command_id", YourCommand(), "your_category")
```

Then add a stub in stubs.py and import it properly in main.py.

## Error Handling

All commands should use the `error_handler` decorator to ensure consistent error reporting. The decorator wraps command execution in a try-except block and handles formatting of error messages.

## UI Guidelines

- Use the UI Components factory for all UI elements to maintain consistency
- Provide progress feedback for long-running operations
- Use color consistently: green for success, yellow for warnings, red for errors
- Use rich-formatted text for better readability
- Ask for confirmation before destructive operations

## Testing

Commands are designed to be testable. The separation of UI logic from business logic makes it easier to test commands in isolation.

## Documentation

All modules, classes, and methods have docstrings that explain:
- What they do
- What parameters they accept
- What they return
- Any exceptions they might raise

## Dependencies

The enhanced CLI depends on:
- rich - For formatted terminal output
- python-dotenv - For environment variable loading
- mysql-connector-python - For database access
