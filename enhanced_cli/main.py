"""
Main entry point for the Enhanced CLI application.

This module contains the core CLI class that coordinates all components
and provides the main menu and application flow.
"""

import os
import logging
from rich.console import Console
from rich.prompt import Prompt

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class EnhancedCLI:
    """Enhanced CLI application with modular design."""
    
    def __init__(self):
        """Initialize the Enhanced CLI application."""
        self.console = Console()
        self.cli = PortfolioCLI()
        self.command_registry = CommandRegistry(self.console)
        self.selected_portfolio = None
        self.configure_logging()
        self.register_commands()
    
    def configure_logging(self):
        """Configure logging to redirect logs to a file."""
        log_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one directory since we're in the enhanced_cli subdirectory
        log_dir = os.path.dirname(log_dir)
        log_file = os.path.join(log_dir, "analysis.log")
        
        # Remove existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='a'
        )
        
        # Configure application loggers
        loggers = [
            logging.getLogger('moving_averages'),
            logging.getLogger('config'),
            logging.getLogger('portfolio_cli'),
            logging.getLogger('bollinger_bands'),
            logging.getLogger('data_retrieval_consolidated'),
            logging.getLogger('ticker_dao'),
            logging.getLogger('rsi_calculations'),
            logging.getLogger('macd'),
            logging.getLogger('options_data'),
            logging.getLogger('news_sentiment')
        ]
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        for logger in loggers:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            logger.addHandler(file_handler)
            logger.propagate = False
    
    def register_commands(self):
        """Register all available commands with the command registry."""
        # First use stubs to avoid circular imports during initialization
        from enhanced_cli.stubs import (
            register_portfolio_commands,
            register_transaction_commands,
            register_analysis_commands,
            register_watchlist_commands,
            register_settings_commands,
            register_cash_management_commands,
            register_data_commands
        )
        
        # Register stub commands initially
        register_portfolio_commands(self.command_registry)
        register_transaction_commands(self.command_registry)
        register_analysis_commands(self.command_registry)
        register_watchlist_commands(self.command_registry)
        register_settings_commands(self.command_registry)
        register_cash_management_commands(self.command_registry)
        register_data_commands(self.command_registry)
        
        # Now we can safely import the real implementations
        from enhanced_cli.portfolio_views import register_portfolio_commands as real_register_portfolio_commands
        from enhanced_cli.transaction_views import register_transaction_commands as real_register_transaction_commands
        from enhanced_cli.analysis_views import register_analysis_commands as real_register_analysis_commands
        from enhanced_cli.watchlist_views import register_watchlist_commands as real_register_watchlist_commands
        from enhanced_cli.settings_views import register_settings_commands as real_register_settings_commands
        from enhanced_cli.cash_management_views import register_cash_management_commands as real_register_cash_management_commands
        from enhanced_cli.data_views import register_data_commands as real_register_data_commands
        from enhanced_cli.comprehensive_analysis_views import register_comprehensive_analysis_commands
        
        # Register actual commands from each module
        real_register_portfolio_commands(self.command_registry)
        real_register_transaction_commands(self.command_registry)
        real_register_analysis_commands(self.command_registry)
        real_register_watchlist_commands(self.command_registry)
        real_register_settings_commands(self.command_registry)
        real_register_cash_management_commands(self.command_registry)
        real_register_data_commands(self.command_registry)
        register_comprehensive_analysis_commands(self.command_registry)
    
    def display_header(self):
        """Display application header."""
        header = ui.header("Portfolio & Stock Management System", "v1.0.0")
        self.console.print(header)
        if self.selected_portfolio:
            portfolio = self.cli.portfolio_dao.read_portfolio(self.selected_portfolio)
            if portfolio:
                self.console.print(f"\n[bold blue]Selected Portfolio:[/bold blue] [green]{portfolio['name']}[/green] (ID: {portfolio['id']})")
    
    def display_main_menu(self) -> str:
        """
        Display the main menu and get user selection.
        
        Returns:
            Selected menu option
        """
        # Create menu options from command categories
        menu_options = {}
        
        # Portfolio selection
        menu_options["1"] = "Select Portfolio" if not self.selected_portfolio else "Change Portfolio"
        # Portfolio commands
        menu_options["2"] = "Portfolio Management"
        # Transaction commands
        menu_options["3"] = "Transactions"
        # Analysis commands
        menu_options["4"] = "Analysis Tools"
        # Watchlist commands
        menu_options["5"] = "Watch List Management"
        # Data commands
        menu_options["6"] = "Data Management"
        # Settings
        menu_options["7"] = "Settings"
        # Exit
        menu_options["0"] = "Exit"
        
        return ui.menu("Main Menu", menu_options)
    
    def handle_main_menu(self, choice: str) -> bool:
        """
        Handle the main menu selection.
        
        Args:
            choice: Selected menu option
            
        Returns:
            False if the application should exit, True otherwise
        """
        if choice == "1":
            self.select_portfolio()
        elif choice == "2":
            self.show_portfolio_menu()
        elif choice == "3":
            if not self.selected_portfolio:
                self.console.print("[yellow]Please select a portfolio first.[/yellow]")
            else:
                self.show_transaction_menu()
        elif choice == "4":
            if not self.selected_portfolio:
                self.console.print("[yellow]Please select a portfolio first.[/yellow]")
            else:
                self.show_analysis_menu()
        elif choice == "5":
            self.show_watchlist_menu()
        elif choice == "6":
            self.show_data_menu()
        elif choice == "7":
            self.show_settings_menu()
        elif choice == "0":
            self.console.print("[bold green]Thank you for using the Portfolio Management System![/bold green]")
            return False
        
        return True
    
    def show_portfolio_menu(self):
        """Display the portfolio management menu."""
        options = {
            "1": "List Portfolios",
            "2": "Create Portfolio",
            "3": "View/Manage Portfolio",
            "4": "Back to Main Menu"
        }
        
        choice = ui.menu("Portfolio Management", options)
        
        if choice == "1":
            self.command_registry.execute("list_portfolios", self)
        elif choice == "2":
            self.command_registry.execute("create_portfolio", self)
        elif choice == "3":
            self.command_registry.execute("view_portfolio", self)
        # choice 4 returns to main menu
    
    def select_portfolio(self):
        """Select a portfolio to work with."""
        self.command_registry.execute("list_portfolios", self)
        try:
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to select[/bold]"))
            portfolio = self.cli.portfolio_dao.read_portfolio(portfolio_id)
            if portfolio:
                self.selected_portfolio = portfolio_id
                self.console.print(f"[green]Selected portfolio: {portfolio['name']}[/green]")
            else:
                self.console.print("[red]Portfolio not found.[/red]")
        except ValueError:
            self.console.print("[red]Invalid portfolio ID.[/red]")

    def show_transaction_menu(self):
        """Display the transaction management menu."""
        options = {
            "1": "Log Transaction",
            "2": "View Transactions",
            "3": "Back to Main Menu"
        }
        
        choice = ui.menu("Transaction Management", options)
        
        if choice == "1":
            self.command_registry.execute("log_transaction", self, portfolio_id=self.selected_portfolio)
        elif choice == "2":
            self.command_registry.execute("view_transactions", self, portfolio_id=self.selected_portfolio)
        # choice 3 returns to main menu
    
    def show_analysis_menu(self):
        """Display the analysis tools menu."""
        options = {
            "1": "Analyze Portfolio",
            "2": "View Portfolio Performance",
            "3": "Comprehensive Analysis",
            "4": "View Saved Metrics",
            "5": "Update Benchmark Data",
            "6": "Back to Main Menu"
        }
        
        choice = ui.menu("Analysis Tools", options)
        
        if choice == "1":
            self.command_registry.execute("analyze_portfolio", self, portfolio_id=self.selected_portfolio)
        elif choice == "2":
            self.command_registry.execute("view_performance", self, portfolio_id=self.selected_portfolio)
        elif choice == "3":
            self.command_registry.execute("comprehensive_analysis", self, portfolio_id=self.selected_portfolio)
        elif choice == "4":
            self.command_registry.execute("view_saved_metrics", self)
        elif choice == "5":
            self.command_registry.execute("update_benchmark_data", self)
        # choice 6 returns to main menu
    
    def show_watchlist_menu(self):
        """Display the watch list management menu."""
        options = {
            "1": "View All Watch Lists",
            "2": "Create New Watch List",
            "3": "View/Edit Watch List",
            "4": "Delete Watch List",
            "5": "Back to Main Menu"
        }
        
        choice = ui.menu("Watch List Management", options)
        
        if choice == "1":
            self.command_registry.execute("list_watch_lists", self)
        elif choice == "2":
            self.command_registry.execute("create_watch_list", self)
        elif choice == "3":
            self.command_registry.execute("view_watch_list", self)
        elif choice == "4":
            self.command_registry.execute("delete_watch_list", self)
        # choice 5 returns to main menu
    
    def show_data_menu(self):
        """Display the data management menu."""
        options = {
            "1": "Update Data",
            "2": "Back to Main Menu"
        }
        
        choice = ui.menu("Data Management", options)
        
        if choice == "1":
            self.command_registry.execute("update_data", self)
        # choice 2 returns to main menu
    
    def show_settings_menu(self):
        """Display the settings menu."""
        options = {
            "1": "Database Settings",
            "2": "UI Settings",
            "3": "Analysis Settings",
            "4": "Watchlist Settings",
            "5": "Logging Settings",
            "6": "Chart Settings",
            "7": "Back to Main Menu"
        }
        
        choice = ui.menu("Application Settings", options)
        
        if choice not in ["7"]:
            # All settings use the same command with different category
            self.command_registry.execute("edit_settings", self, category={
                "1": "database",
                "2": "ui",
                "3": "analysis",
                "4": "watchlist",
                "5": "logging",
                "6": "chart"
            }.get(choice))
        # choice 7 returns to main menu
    
    @error_handler("application execution")
    def run(self):
        """Run the Enhanced CLI application."""
        try:
            while True:
                self.display_header()
                choice = self.display_main_menu()
                continue_running = self.handle_main_menu(choice)
                
                if not continue_running:
                    break
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Program interrupted. Exiting...[/bold yellow]")
        except Exception as e:
            self.console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point for the application."""
    cli = EnhancedCLI()
    cli.run()


if __name__ == "__main__":
    main()
