"""
Analysis views and commands for the Enhanced CLI.

This module provides commands for portfolio analysis operations such as
technical analysis and performance tracking.
"""

from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from datetime import datetime, timedelta

from portfolio_cli import PortfolioCLI
from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class AnalyzePortfolioCommand(Command):
    """Command to analyze a portfolio with technical indicators."""
    
    def __init__(self):
        super().__init__("Analyze Portfolio", "Analyze portfolio with technical indicators")
    
    @error_handler("analyzing portfolio")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to analyze a portfolio.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
            ticker_symbol: Optional ticker symbol to analyze
        """
        portfolio_id = kwargs.get('portfolio_id')
        ticker_symbol = kwargs.get('ticker_symbol')
        
        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, 'selected_portfolio') and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)
                
                try:
                    portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID to analyze[/bold]"))
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return
        
        # Ask if they want to analyze a specific ticker
        if ticker_symbol is None and ui.confirm_action("Analyze specific ticker?"):
            with ui.progress("Loading tickers...") as progress:
                progress.add_task("", total=None)
                tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            ui.console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                ui.console.print(f"[{i}] {ticker}")
            
            ticker_symbol = Prompt.ask("[bold]Enter ticker symbol[/bold] (or leave empty for all)").upper()
            if ticker_symbol == "":
                ticker_symbol = None
        
        # Get portfolio info for header
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
            
        header_text = f"Portfolio Analysis: {portfolio['name']}"
        if ticker_symbol:
            header_text += f" - {ticker_symbol}"
        ui.console.print(ui.section_header(header_text))
        
        with ui.progress("Running portfolio analysis...") as progress:
            progress.add_task("", total=None)
            # Use the CLI's analyze_portfolio method
            cli.cli.analyze_portfolio(portfolio_id, ticker_symbol)
            
        # Analysis results are printed directly by the CLI analyze_portfolio method
        # After analysis is complete, wait for user input to continue
        ui.wait_for_user()


class ViewPerformanceCommand(Command):
    """Command to view portfolio performance over time."""
    
    def __init__(self):
        super().__init__("View Performance", "View portfolio performance over time")
    
    @error_handler("viewing performance")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view portfolio performance.
        
        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get('portfolio_id')
        
        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, 'selected_portfolio') and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)
                
                try:
                    portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return
        
        # Get portfolio info for header
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return
            
        ui.console.print(ui.section_header(f"Portfolio Performance: {portfolio['name']}"))
        
        # Time period options
        options = {
            "1": "Last 30 days",
            "2": "Last 3 months",
            "3": "Last 6 months",
            "4": "Year to date",
            "5": "Last 1 year",
            "6": "Custom range"
        }
        
        period_choice = ui.menu("Select Time Period", options)
        
        today = datetime.now().date()
        start_date = None
        end_date = today.strftime('%Y-%m-%d')
        days = 30
        
        if period_choice == "1":  # 30 days
            start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            days = 30
        elif period_choice == "2":  # 3 months
            start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
            days = 90
        elif period_choice == "3":  # 6 months
            start_date = (today - timedelta(days=180)).strftime('%Y-%m-%d')
            days = 180
        elif period_choice == "4":  # YTD
            start_date = datetime(today.year, 1, 1).strftime('%Y-%m-%d')
            days = (today - datetime(today.year, 1, 1).date()).days
        elif period_choice == "5":  # 1 year
            start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
            days = 365
        elif period_choice == "6":  # Custom
            while True:
                start_date = Prompt.ask("[bold]Start date[/bold] (YYYY-MM-DD)")
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                    break
                except ValueError:
                    ui.status_message("Invalid date format. Please use YYYY-MM-DD.", "error")
            
            while True:
                end_date = Prompt.ask(
                    "[bold]End date[/bold] (YYYY-MM-DD)",
                    default=today.strftime('%Y-%m-%d')
                )
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    if end_date_obj > today:
                        ui.status_message("End date cannot be in the future. Using today's date.", "warning")
                        end_date = today.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    ui.status_message("Invalid date format. Please use YYYY-MM-DD.", "error")
        
        # Ask about chart generation
        generate_chart = ui.confirm_action("Generate performance chart?")
        
        with ui.progress("Calculating performance...") as progress:
            progress.add_task("", total=None)
            
            # Use the universal value service for consistent calculations
            if start_date and end_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                from datetime import date
                end_date_obj = date.today()
                start_date_obj = end_date_obj - timedelta(days=days)
                start_date = start_date_obj.strftime('%Y-%m-%d')
                end_date = end_date_obj.strftime('%Y-%m-%d')
            
            # Get initial and final portfolio values using the universal service
            initial_result = cli.cli.value_service.calculate_portfolio_value(
                portfolio_id, 
                calculation_date=start_date_obj,
                include_cash=True, 
                include_dividends=True,  # Include dividends in performance view
                use_current_prices=False
            )
            
            final_result = cli.cli.value_service.calculate_portfolio_value(
                portfolio_id, 
                calculation_date=end_date_obj,
                include_cash=True, 
                include_dividends=True,  # Include dividends in performance view
                use_current_prices=(end_date_obj == date.today())
            )
        
        # Display performance metrics
        ui.console.print(f"\n[bold]Performance Metrics:[/bold]")
        ui.console.print(f"Period: {start_date} to {end_date}")
        ui.console.print(f"Initial Value: ${initial_result['total_value']:,.2f}")
        ui.console.print(f"Final Value: ${final_result['total_value']:,.2f}")
        
        # Calculate returns
        if initial_result['total_value'] > 0:
            total_return = ((final_result['total_value'] / initial_result['total_value']) - 1) * 100
            ui.console.print(f"Total Return: {total_return:+.2f}%")
            
            # Calculate annualized return if period is longer than a day
            period_days = (end_date_obj - start_date_obj).days
            if period_days > 0:
                annualized_return = ((1 + (total_return/100)) ** (365/period_days) - 1) * 100
                ui.console.print(f"Annualized Return: {annualized_return:+.2f}%")
        else:
            ui.console.print("Total Return: N/A (no initial value)")
        
        # Show breakdown
        ui.console.print(f"\n[bold]Value Breakdown:[/bold]")
        ui.console.print(f"Stock Value: ${final_result['stock_value']:,.2f}")
        ui.console.print(f"Cash Balance: ${final_result['cash_balance']:,.2f}")
        if final_result['dividend_value'] > 0:
            ui.console.print(f"Cumulative Dividends: ${final_result['dividend_value']:,.2f}")
        
        # Generate chart if requested
        if generate_chart:
            try:
                chart_path = cli.cli.value_calculator.generate_performance_chart(portfolio_id, start_date, end_date)
                if chart_path:
                    ui.console.print(f"\n[green]Performance chart saved to:[/green] {chart_path}")
                    # Try to open the chart
                    try:
                        import platform
                        import os
                        system = platform.system()
                        if system == "Darwin":  # macOS
                            os.system(f"open {chart_path}")
                        elif system == "Windows":
                            os.system(f"start {chart_path}")
                        elif system == "Linux":
                            os.system(f"xdg-open {chart_path}")
                    except Exception as e:
                        ui.console.print(f"[yellow]Note: Could not automatically open the chart: {e}[/yellow]")
            except Exception as e:
                ui.console.print(f"[red]Error generating chart: {e}[/red]")
        
        # Wait for user input to continue
        ui.wait_for_user()


def register_analysis_commands(registry: CommandRegistry) -> None:
    """
    Register analysis-related commands with the command registry.
    
    Args:
        registry: The command registry to register commands with
    """
    registry.register("analyze_portfolio", AnalyzePortfolioCommand(), "analysis")
    registry.register("view_performance", ViewPerformanceCommand(), "analysis")
