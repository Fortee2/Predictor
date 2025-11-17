"""
Portfolio views and commands for the Enhanced CLI.

This module provides the registration function for portfolio management commands.
Individual command classes are defined in separate files within this package.
"""

from enhanced_cli.command import CommandRegistry
from enhanced_cli.portfolio import (
    AddTickersCommand,
    CreatePortfolioCommand,
    ListPortfoliosCommand,
    RecalculatePortfolioValuesCommand,
    RemoveTickersCommand,
    ViewPortfolioCommand,
)


def register_portfolio_commands(registry: CommandRegistry) -> None:
    """
    Register portfolio-related commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("list_portfolios", ListPortfoliosCommand(), "portfolio")
    registry.register("create_portfolio", CreatePortfolioCommand(), "portfolio")
    registry.register("view_portfolio", ViewPortfolioCommand(), "portfolio")
    registry.register("add_tickers", AddTickersCommand(), "portfolio")
    registry.register("remove_tickers", RemoveTickersCommand(), "portfolio")
    registry.register(
        "recalculate_portfolio_values", RecalculatePortfolioValuesCommand(), "portfolio"
    )
