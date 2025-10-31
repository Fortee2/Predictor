"""
Empty stubs for command registration functions.

This module provides empty implementations of all the command registration functions
to resolve circular import issues during initialization.
"""

from enhanced_cli.command import CommandRegistry


# Empty stub implementations of all registration functions
def register_portfolio_commands(registry: CommandRegistry) -> None:
    """Stub for portfolio command registration."""
    from enhanced_cli.command import Command
    
    class StubListPortfoliosCommand(Command):
        def __init__(self):
            super().__init__("List Portfolios", "Display all portfolios")
        
        def execute(self, cli, *args, **kwargs):
            pass  # Stub implementation, will be replaced by real implementation later
    
    registry.register("list_portfolios", StubListPortfoliosCommand(), "portfolio")


def register_transaction_commands(registry: CommandRegistry) -> None:
    """Stub for transaction command registration."""
    pass


def register_analysis_commands(registry: CommandRegistry) -> None:
    """Stub for analysis command registration."""
    pass


def register_watchlist_commands(registry: CommandRegistry) -> None:
    """Stub for watchlist command registration."""
    pass


def register_settings_commands(registry: CommandRegistry) -> None:
    """Stub for settings command registration."""
    pass


def register_cash_management_commands(registry: CommandRegistry) -> None:
    """Stub for cash management command registration."""
    pass


def register_data_commands(registry: CommandRegistry) -> None:
    """Stub for data command registration."""
    pass
