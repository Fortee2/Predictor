"""
Transaction views and commands for the Enhanced CLI.

This module provides the registration function for transaction management commands.
Individual command classes are defined in separate files within this package.
"""

from enhanced_cli.command import CommandRegistry
from enhanced_cli.transaction import LogTransactionCommand, ViewTransactionsCommand


def register_transaction_commands(registry: CommandRegistry, pool=None) -> None:
    """
    Register transaction-related commands with the command registry.

    Args:
        registry: The command registry to register commands with
        pool: Optional database connection pool for commands that need it
    """
    # LogTransactionCommand requires a database pool
    if pool:
        registry.register("log_transaction", LogTransactionCommand(pool), "transaction")
    registry.register("view_transactions", ViewTransactionsCommand(), "transaction")
