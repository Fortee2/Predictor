"""
Watchlist views and commands for the Enhanced CLI.

This module provides commands for watchlist management operations such as
creating, viewing, and managing watchlists.
"""

from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from datetime import datetime

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class ListWatchListsCommand(Command):
    """Command to list all watchlists."""
    
    def __init__(self):
        super().__init__("List Watch Lists", "Display all watchlists")
    
    @error_handler("listing watchlists")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to list all watchlists.
        
        Args:
            cli: The CLI instance
        """
        with ui.progress("Loading watch lists...") as progress:
            progress.add_task("", total=None)
            watch_lists = cli.cli.watch_list_dao.get_watch_list()
        
        if not watch_lists:
            ui.status_message("No watch lists found.", "warning")
            if ui.confirm_action("Create a new watch list?"):
                create_command = CreateWatchListCommand()
                create_command.execute(cli)
            return
        
        # Prepare table columns
        columns = [
            {'header': 'ID', 'style': 'cyan'},
            {'header': 'Name', 'style': 'green'},
            {'header': 'Description'},
            {'header': 'Tickers', 'style': 'magenta'},
            {'header': 'Date Created'}
        ]
        
        # Prepare table rows
        rows = []
        for wl in watch_lists:
            ticker_count = len(cli.cli.watch_list_dao.get_tickers_in_watch_list(wl['id']))
            
            rows.append([
                str(wl['id']),
                wl['name'],
                wl['description'] or "",
                str(ticker_count),
                wl['date_created'].strftime('%Y-%m-%d')
            ])
        
        # Display the table
        table = ui.data_table("Your Watch Lists", columns, rows)
        ui.console.print(table)
        
        # Ask if user wants to view a specific watch list
        if ui.confirm_action("View a specific watch list?"):
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
                view_command = ViewWatchListCommand()
                view_command.execute(cli, watch_list_id=watch_list_id)
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")


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
            {
                'name': 'name',
                'prompt': "[bold]Watch List Name[/bold]"
            },
            {
                'name': 'description',
                'prompt': "[bold]Description[/bold] (optional)"
            }
        ]
        
        # Get form data
        data = ui.input_form(fields)
        
        if ui.confirm_action(f"Create watch list [bold]{data['name']}[/bold] with description: [italic]{data['description']}[/italic]?"):
            with ui.progress("Creating watch list...") as progress:
                progress.add_task("", total=None)
                watch_list_id = cli.cli.create_watch_list(data['name'], data['description'])
            
            if watch_list_id:
                ui.status_message(f"Watch list created successfully with ID: {watch_list_id}", "success")
                
                if ui.confirm_action("Would you like to add tickers to this watch list now?"):
                    add_tickers_command = AddTickersToWatchListCommand()
                    add_tickers_command.execute(cli, watch_list_id=watch_list_id)
            else:
                ui.status_message("Failed to create watch list", "error")


class ViewWatchListCommand(Command):
    """Command to view and manage a watchlist."""
    
    def __init__(self):
        super().__init__("View Watch List", "View and manage a watchlist")
    
    @error_handler("viewing watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view and manage a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID to view
        """
        watch_list_id = kwargs.get('watch_list_id')
        
        if watch_list_id is None:
            # Get all watch lists
            with ui.progress("Loading watch lists...") as progress:
                progress.add_task("", total=None)
                watch_lists = cli.cli.watch_list_dao.get_watch_list()
            
            if not watch_lists:
                ui.status_message("No watch lists found.", "warning")
                return
            
            # Display basic table to select from
            columns = [
                {'header': 'ID', 'style': 'cyan'},
                {'header': 'Name', 'style': 'green'}
            ]
            
            rows = []
            for wl in watch_lists:
                rows.append([str(wl['id']), wl['name']])
            
            table = ui.data_table("Your Watch Lists", columns, rows)
            ui.console.print(table)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to view[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list details
        with ui.progress("Loading watch list details...") as progress:
            progress.add_task("", total=None)
            watch_list = cli.cli.watch_list_dao.get_watch_list(watch_list_id)
            
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return
        
        # Watch List header
        ui.console.print(ui.header(watch_list['name'], f"Watch List #{watch_list_id}"))
        
        # Watch List details
        if watch_list['description']:
            ui.console.print(f"[bold]Description:[/bold] {watch_list['description']}")
        ui.console.print(f"[bold]Date Created:[/bold] {watch_list['date_created'].strftime('%Y-%m-%d')}")
        
        # Get tickers in watch list
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if tickers:
            # Prepare ticker table columns
            columns = [
                {'header': 'Symbol', 'style': 'cyan'},
                {'header': 'Name'},
                {'header': 'Notes'},
                {'header': 'Date Added'}
            ]
            
            # Prepare ticker table rows
            rows = []
            for ticker in tickers:
                rows.append([
                    ticker['symbol'],
                    ticker['name'],
                    ticker['notes'] or "",
                    ticker['date_added'].strftime('%Y-%m-%d')
                ])
            
            # Display the ticker table
            ticker_table = ui.data_table("Tickers in Watch List", columns, rows)
            ui.console.print(ticker_table)
        else:
            ui.status_message("No tickers in this watch list.", "warning")
        
        # Watch List Actions Menu
        options = {
            "1": "Add Tickers",
            "2": "Remove Tickers",
            "3": "Update Ticker Notes",
            "4": "Analyze Watch List",
            "5": "Back to Watch Lists"
        }
        
        choice = ui.menu("Watch List Actions", options)
        
        if choice == "1":
            add_tickers_command = AddTickersToWatchListCommand()
            add_tickers_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "2":
            remove_tickers_command = RemoveTickersFromWatchListCommand()
            remove_tickers_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "3":
            update_notes_command = UpdateTickerNotesCommand()
            update_notes_command.execute(cli, watch_list_id=watch_list_id)
        elif choice == "4":
            analyze_command = AnalyzeWatchListCommand()
            analyze_command.execute(cli, watch_list_id=watch_list_id)
        # choice 5 returns to watch list menu


class AddTickersToWatchListCommand(Command):
    """Command to add tickers to a watchlist."""
    
    def __init__(self):
        super().__init__("Add Tickers to Watch List", "Add tickers to a watchlist")
    
    @error_handler("adding tickers to watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to add tickers to a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
        """
        watch_list_id = kwargs.get('watch_list_id')
        
        if watch_list_id is None:
            # First list watch lists for selection
            list_command = ListWatchListsCommand()
            list_command.execute(cli)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list details for header
        watch_list = cli.cli.watch_list_dao.get_watch_list(watch_list_id)
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return
            
        ui.console.print(ui.section_header(f"Add Tickers to Watch List #{watch_list_id} - {watch_list['name']}"))
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols[/bold] (separated by spaces)")
        ticker_symbols = ticker_input.upper().split()
        
        if not ticker_symbols:
            ui.status_message("No tickers entered.", "warning")
            return
            
        notes = Prompt.ask("[bold]Notes[/bold] (optional, will apply to all tickers)")
        
        if ui.confirm_action(f"Add {len(ticker_symbols)} ticker(s) to watch list #{watch_list_id}?"):
            with ui.progress("Adding tickers...") as progress:
                progress.add_task("", total=None)
                for symbol in ticker_symbols:
                    cli.cli.add_watch_list_ticker(watch_list_id, [symbol], notes)
            
            ui.status_message("Tickers added successfully", "success")


class RemoveTickersFromWatchListCommand(Command):
    """Command to remove tickers from a watchlist."""
    
    def __init__(self):
        super().__init__("Remove Tickers from Watch List", "Remove tickers from a watchlist")
    
    @error_handler("removing tickers from watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to remove tickers from a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
        """
        watch_list_id = kwargs.get('watch_list_id')
        
        if watch_list_id is None:
            # First list watch lists for selection
            list_command = ListWatchListsCommand()
            list_command.execute(cli)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list details
        watch_list = cli.cli.watch_list_dao.get_watch_list(watch_list_id)
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return
            
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            ui.status_message("This watch list has no tickers to remove.", "warning")
            return
        
        # Show current tickers
        ui.console.print("[bold]Current Tickers:[/bold]")
        ticker_symbols = []
        for ticker in tickers:
            ui.console.print(f"- {ticker['symbol']}")
            ticker_symbols.append(ticker['symbol'])
        
        ticker_input = Prompt.ask("[bold]Enter ticker symbols to remove[/bold] (separated by spaces)")
        to_remove = ticker_input.upper().split()
        
        valid_tickers = [t for t in to_remove if t in ticker_symbols]
        if not valid_tickers:
            ui.status_message("No valid tickers selected for removal.", "warning")
            return
        
        if ui.confirm_action(f"Remove {len(valid_tickers)} ticker(s) from watch list #{watch_list_id}?"):
            with ui.progress("Removing tickers...") as progress:
                progress.add_task("", total=None)
                cli.cli.remove_watch_list_ticker(watch_list_id, valid_tickers)
            
            ui.status_message("Tickers removed successfully", "success")


class UpdateTickerNotesCommand(Command):
    """Command to update notes for a ticker in a watchlist."""
    
    def __init__(self):
        super().__init__("Update Ticker Notes", "Update notes for a ticker in a watchlist")
    
    @error_handler("updating ticker notes")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to update notes for a ticker in a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
        """
        watch_list_id = kwargs.get('watch_list_id')
        
        if watch_list_id is None:
            # First list watch lists for selection
            list_command = ListWatchListsCommand()
            list_command.execute(cli)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list tickers
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            ui.status_message("This watch list has no tickers.", "warning")
            return
        
        # Show current tickers with notes
        columns = [
            {'header': 'Symbol', 'style': 'cyan'},
            {'header': 'Notes'}
        ]
        
        rows = []
        for ticker in tickers:
            rows.append([ticker['symbol'], ticker['notes'] or ""])
        
        table = ui.data_table("Current Tickers", columns, rows)
        ui.console.print(table)
        
        ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to update[/bold]").upper()
        
        # Check if ticker exists in the watch list
        ticker_exists = any(t['symbol'] == ticker_symbol for t in tickers)
        if not ticker_exists:
            ui.status_message(f"Ticker {ticker_symbol} not found in this watch list.", "error")
            return
        
        # Get current notes
        current_notes = next((t['notes'] for t in tickers if t['symbol'] == ticker_symbol), "")
        notes = Prompt.ask("[bold]Enter new notes[/bold]", default=current_notes or "")
        
        if ui.confirm_action(f"Update notes for {ticker_symbol}?"):
            with ui.progress("Updating notes...") as progress:
                progress.add_task("", total=None)
                cli.cli.update_watch_list_ticker_notes(watch_list_id, ticker_symbol, notes)
            
            ui.status_message("Notes updated successfully", "success")


class DeleteWatchListCommand(Command):
    """Command to delete a watchlist."""
    
    def __init__(self):
        super().__init__("Delete Watch List", "Delete a watchlist")
    
    @error_handler("deleting watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to delete a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID to delete
        """
        watch_list_id = kwargs.get('watch_list_id')
        
        if watch_list_id is None:
            # First list watch lists for selection
            with ui.progress("Loading watch lists...") as progress:
                progress.add_task("", total=None)
                watch_lists = cli.cli.watch_list_dao.get_watch_list()
            
            if not watch_lists:
                ui.status_message("No watch lists found.", "warning")
                return
            
            # Show table for selection
            columns = [
                {'header': 'ID', 'style': 'cyan'},
                {'header': 'Name', 'style': 'green'},
                {'header': 'Tickers', 'style': 'magenta'}
            ]
            
            rows = []
            for wl in watch_lists:
                ticker_count = len(cli.cli.watch_list_dao.get_tickers_in_watch_list(wl['id']))
                rows.append([str(wl['id']), wl['name'], str(ticker_count)])
            
            table = ui.data_table("Your Watch Lists", columns, rows)
            ui.console.print(table)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID to delete[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list details for confirmation
        with ui.progress("Loading watch list details...") as progress:
            progress.add_task("", total=None)
            watch_list = cli.cli.watch_list_dao.get_watch_list(watch_list_id)
        
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return
        
        # Confirm deletion with a stronger warning
        if ui.confirm_action(
            f"[bold red]Are you sure you want to delete watch list '{watch_list['name']}'? "
            f"This cannot be undone.[/bold red]", 
            default=False
        ):
            with ui.progress("Deleting watch list...") as progress:
                progress.add_task("", total=None)
                cli.cli.delete_watch_list(watch_list_id)
            
            ui.status_message("Watch list deleted successfully", "success")


class AnalyzeWatchListCommand(Command):
    """Command to analyze tickers in a watchlist."""
    
    def __init__(self):
        super().__init__("Analyze Watch List", "Analyze tickers in a watchlist")
    
    @error_handler("analyzing watchlist")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to analyze tickers in a watchlist.
        
        Args:
            cli: The CLI instance
            watch_list_id: Optional watchlist ID
            ticker_symbol: Optional ticker symbol to analyze
        """
        watch_list_id = kwargs.get('watch_list_id')
        ticker_symbol = kwargs.get('ticker_symbol')
        
        if watch_list_id is None:
            # First list watch lists for selection
            list_command = ListWatchListsCommand()
            list_command.execute(cli)
            
            try:
                watch_list_id = int(Prompt.ask("[bold]Enter Watch List ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid watch list ID", "error")
                return
        
        # Get watch list details
        watch_list = cli.cli.watch_list_dao.get_watch_list(watch_list_id)
        if not watch_list:
            ui.status_message(f"Watch list with ID {watch_list_id} not found.", "error")
            return
            
        # Get tickers in watch list
        with ui.progress("Loading tickers...") as progress:
            progress.add_task("", total=None)
            tickers = cli.cli.watch_list_dao.get_tickers_in_watch_list(watch_list_id)
        
        if not tickers:
            ui.status_message("This watch list has no tickers to analyze.", "warning")
            return
        
        # Ask if they want to analyze a specific ticker
        if ticker_symbol is None:
            ui.console.print("[bold]Available Tickers:[/bold]")
            for ticker in tickers:
                ui.console.print(f"- {ticker['symbol']}")
            
            analyze_all = ui.confirm_action("Analyze all tickers?", True)
            if not analyze_all:
                ticker_symbol = Prompt.ask("[bold]Enter ticker symbol to analyze[/bold]").upper()
                # Check if ticker exists in the watch list
                ticker_exists = any(t['symbol'] == ticker_symbol for t in tickers)
                if not ticker_exists:
                    ui.status_message(f"Ticker {ticker_symbol} not found in this watch list.", "error")
                    return
        
        header_text = f"Analyzing Watch List: {watch_list['name']}"
        if ticker_symbol:
            header_text += f" - {ticker_symbol}"
        ui.console.print(ui.section_header(header_text))
        
        with ui.progress("Running analysis...") as progress:
            progress.add_task("", total=None)
            # Use the CLI's analyze_watch_list method
            cli.cli.analyze_watch_list(watch_list_id, ticker_symbol)
        
        # Analysis results are printed directly by the CLI analyze_watch_list method
        # After analysis is complete, wait for user input to continue
        ui.wait_for_user()


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
