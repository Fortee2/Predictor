"""
Watchlist views and commands for the Enhanced CLI.

This module provides commands for watchlist management operations such as
creating, viewing, and managing watch lists.
"""

from enhanced_cli.core.command import CommandRegistry
from enhanced_cli.watchlist.view_watch_list_command import ViewWatchListCommand
from enhanced_cli.watchlist.list_watch_lists_command import ListWatchListsCommand
from enhanced_cli.watchlist.create_watchlists_command import CreateWatchListCommand
from enhanced_cli.watchlist.add_tickers_command import AddTickersToWatchListCommand
from enhanced_cli.watchlist.remove_tickers_command import RemoveTickersFromWatchListCommand
from enhanced_cli.watchlist.update_ticker_notes_command import UpdateTickerNotesCommand
from enhanced_cli.watchlist.delete_watchlist_command import DeleteWatchListCommand
from enhanced_cli.watchlist.analyze_watch_llist_command import AnalyzeWatchListCommand

def register_watchlist_commands(registry: CommandRegistry) -> None:
    """
    Register watchlist-related commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """


    registry.register("list_watch_lists", ListWatchListsCommand(), "watchlist")
    registry.register("create_watch_list", CreateWatchListCommand(), "watchlist")
    registry.register("view_watch_list", ViewWatchListCommand(), "watchlist")
    registry.register("add_watch_list_ticker", AddTickersToWatchListCommand(), "watchlist")
    registry.register("remove_watch_list_ticker", RemoveTickersFromWatchListCommand(), "watchlist")
    registry.register("update_watch_list_notes", UpdateTickerNotesCommand(), "watchlist")
    registry.register("delete_watch_list", DeleteWatchListCommand(), "watchlist")
    registry.register("analyze_watch_list", AnalyzeWatchListCommand(), "watchlist")
