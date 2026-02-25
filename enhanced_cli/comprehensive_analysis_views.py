"""
Comprehensive analysis views for the Enhanced CLI.

This module provides commands for comprehensive multi-timeframe portfolio analysis
with advanced metrics, benchmark comparisons, and risk analysis.
"""

from datetime import date, datetime
from typing import Dict

from rich.prompt import Prompt

from data.comprehensive_performance_formatter import ComprehensivePerformanceFormatter
from data.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from data.utility import DatabaseConnectionPool
from enhanced_cli.core.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class ComprehensiveAnalysisCommand(Command):
    """Command to perform comprehensive multi-timeframe portfolio analysis."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__(
            "Comprehensive Analysis",
            "Comprehensive multi-timeframe portfolio analysis with benchmarks",
        )
        self.pool = pool

    @error_handler("performing comprehensive analysis")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute comprehensive portfolio analysis.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # First list portfolios for selection
            from enhanced_cli.portfolio import ListPortfoliosCommand

            list_command = ListPortfoliosCommand()
            list_command.execute(cli)

            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID for comprehensive analysis[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return

        # Get portfolio info for header
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return

        portfolio_name = portfolio["name"]
        ui.console.print(ui.section_header(f"Comprehensive Analysis: {portfolio_name}"))

        # Load the most recent comprehensive analysis metrics
        with ui.progress("Loading comprehensive analysis metrics...") as progress:
            progress.add_task("Fetching metrics...", total=None)
            try:
                analyzer = MultiTimeframeAnalyzer(self.pool)
                # We fetch for today's date, as calculations are now tied to data updates
                analysis_date = date.today()
                portfolio_metrics = analyzer.get_portfolio_metrics(portfolio_id, analysis_date)

                if not portfolio_metrics:
                    ui.status_message(
                        f"No metrics found for {analysis_date}. Please update market data first.",
                        "warning"
                    )
                    ui.console.print("[dim]You can update data by running 'data' -> 'Update Market Data'.[/dim]")
                    ui.wait_for_user()
                    return

                # Placeholders for future implementations
                holdings_metrics = {}
                market_events_performance = {}

            except Exception as e:
                ui.status_message(f"Error loading analysis metrics: {e}", "error")
                return

        # Display comprehensive results
        ui.console.print("\n")
        ui.status_message("Displaying latest comprehensive analysis...", "success")

        try:
            formatter = ComprehensivePerformanceFormatter()
            formatter.display_comprehensive_analysis(
                portfolio_metrics=portfolio_metrics,
                holdings_metrics=holdings_metrics,
                portfolio_name=portfolio_name,
                market_events_performance=market_events_performance,
            )
        except Exception as e:
            ui.status_message(f"Error displaying results: {e}", "error")
            # Fallback to simple display
            self._display_simple_results(portfolio_metrics, portfolio_name)

        # Display active trading signals summary
        try:
            from data.trading_signal_dao import TradingSignalDAO

            signal_dao = TradingSignalDAO(self.pool)
            signals = signal_dao.get_active_signals(portfolio_id=portfolio_id)

            if signals:
                ui.console.print("\n" + ui.section_header("Trading Signals Summary"))

                buy_signals = [s for s in signals if s["signal_type"] == "BUY"]
                sell_signals = [s for s in signals if s["signal_type"] == "SELL"]

                ui.console.print(f"[green]● {len(buy_signals)} BUY signals[/green]")
                ui.console.print(f"[red]● {len(sell_signals)} SELL signals[/red]")

                if buy_signals or sell_signals:
                    high_confidence = [s for s in signals if s["confidence_score"] >= 80]
                    if high_confidence:
                        ui.console.print(
                            f"\n[bold yellow]⚠  {len(high_confidence)} high-confidence signals (≥80%)[/bold yellow]"
                        )
                        for signal in high_confidence[:3]:  # Show top 3
                            signal_color = "green" if signal["signal_type"] == "BUY" else "red"
                            ui.console.print(
                                f"  • [{signal_color}]{signal['ticker_symbol']}[/{signal_color}]: "
                                f"[{signal_color}]{signal['signal_type']}[/{signal_color}] "
                                f"at ${signal['price_at_signal']:.2f} ({signal['confidence_score']:.0f}%)"
                            )

                ui.console.print(
                    "\n[dim]View all signals: Trading Strategies → View Active Signals[/dim]"
                )

        except ImportError:
            # Trading strategies module not available
            pass
        except Exception:
            # Silently ignore errors in signal display
            pass

        # Wait for user input to continue
        ui.wait_for_user()

    def _get_holdings_analysis(self, analyzer: MultiTimeframeAnalyzer, portfolio_id: int) -> Dict:
        """
        Get individual holdings analysis (placeholder for future implementation).

        Args:
            analyzer: MultiTimeframeAnalyzer instance
            portfolio_id: Portfolio ID

        Returns:
            Dictionary of holdings metrics by ticker symbol
        """
        # For now, return empty dict - this would be implemented to analyze individual holdings
        # across timeframes similar to portfolio analysis
        return {}

    def _get_market_events_analysis(self, analyzer: MultiTimeframeAnalyzer, portfolio_id: int) -> Dict:
        """
        Get market events performance analysis (placeholder for future implementation).

        Args:
            analyzer: MultiTimeframeAnalyzer instance
            portfolio_id: Portfolio ID

        Returns:
            Dictionary of performance during market events
        """
        # Placeholder for market events analysis
        # This would analyze portfolio performance during major market events
        return {}

    def _display_simple_results(self, portfolio_metrics: Dict, portfolio_name: str):
        """
        Simple fallback display of results if formatter fails.

        Args:
            portfolio_metrics: Portfolio metrics by timeframe
            portfolio_name: Portfolio name
        """
        ui.console.print(f"\n[bold blue]Performance Summary for {portfolio_name}[/bold blue]")
        ui.console.print("=" * 80)

        timeframes = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]

        for timeframe in timeframes:
            if timeframe in portfolio_metrics:
                metrics = portfolio_metrics[timeframe]
                ui.console.print(f"\n[bold]{timeframe} Performance:[/bold]")

                total_return = metrics.get("total_return_pct")
                if total_return is not None:
                    color = "green" if total_return >= 0 else "red"
                    ui.console.print(f"  Total Return: [{color}]{total_return:.2f}%[/{color}]")

                annualized_return = metrics.get("annualized_return_pct")
                if annualized_return is not None:
                    color = "green" if annualized_return >= 0 else "red"
                    ui.console.print(f"  Annualized Return: [{color}]{annualized_return:.2f}%[/{color}]")

                volatility = metrics.get("volatility_pct")
                if volatility is not None:
                    ui.console.print(f"  Volatility: {volatility:.2f}%")

                sharpe_ratio = metrics.get("sharpe_ratio")
                if sharpe_ratio is not None:
                    color = "green" if sharpe_ratio >= 0 else "red"
                    ui.console.print(f"  Sharpe Ratio: [{color}]{sharpe_ratio:.2f}[/{color}]")

                max_drawdown = metrics.get("max_drawdown_pct")
                if max_drawdown is not None:
                    ui.console.print(f"  Max Drawdown: [red]{max_drawdown:.2f}%[/red]")

                excess_return = metrics.get("excess_return_pct")
                if excess_return is not None:
                    color = "green" if excess_return >= 0 else "red"
                    ui.console.print(f"  vs S&P 500: [{color}]{excess_return:.2f}%[/{color}]")


class ViewSavedMetricsCommand(Command):
    """Command to view previously saved comprehensive metrics."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("View Saved Metrics", "View previously calculated comprehensive metrics")
        self.pool = pool

    @error_handler("viewing saved metrics")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute view saved metrics command.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # First list portfolios for selection
            from enhanced_cli.portfolio.portfolio_views import ListPortfoliosCommand

            list_command = ListPortfoliosCommand()
            list_command.execute(cli)

            try:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
            except ValueError:
                ui.status_message("Invalid portfolio ID", "error")
                return

        # Get portfolio info
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return

        portfolio_name = portfolio["name"]

        # Ask for date
        date_input = Prompt.ask(
            "[bold]Enter date for metrics (YYYY-MM-DD)[/bold]",
            default=date.today().strftime("%Y-%m-%d"),
        )

        try:
            analysis_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            ui.status_message("Invalid date format. Please use YYYY-MM-DD.", "error")
            return

        # Retrieve saved metrics
        with ui.progress("Loading saved metrics...") as progress:
            progress.add_task("", total=None)

            try:
                analyzer = MultiTimeframeAnalyzer(self.pool)
                portfolio_metrics = analyzer.get_portfolio_metrics(portfolio_id, analysis_date)

                if not portfolio_metrics:
                    ui.status_message(f"No saved metrics found for {analysis_date}", "warning")
                    return

            except Exception as e:
                ui.status_message(f"Error loading metrics: {e}", "error")
                return

        # Display results
        try:
            formatter = ComprehensivePerformanceFormatter()
            formatter.display_comprehensive_analysis(portfolio_metrics=portfolio_metrics, portfolio_name=portfolio_name)
        except Exception as e:
            ui.status_message(f"Error displaying results: {e}", "error")
            # Fallback to simple display
            self._display_simple_results(portfolio_metrics, portfolio_name)

        ui.wait_for_user()

    def _display_simple_results(self, portfolio_metrics: Dict, portfolio_name: str):
        """Simple fallback display of results."""
        ui.console.print(f"\n[bold blue]Saved Metrics for {portfolio_name}[/bold blue]")
        ui.console.print("=" * 80)

        for timeframe, metrics in portfolio_metrics.items():
            ui.console.print(f"\n[bold]{timeframe}:[/bold]")
            for key, value in metrics.items():
                if value is not None:
                    if "pct" in key:
                        ui.console.print(f"  {key}: {value:.2f}%")
                    else:
                        ui.console.print(f"  {key}: {value:.2f}")


class UpdateBenchmarkDataCommand(Command):
    """Command to update benchmark data (S&P 500)."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Update Benchmark Data", "Update S&P 500 and other benchmark data")
        self.pool = pool

    @error_handler("updating benchmark data")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute update benchmark data command.

        Args:
            cli: The CLI instance
        """
        ui.console.print(ui.section_header("Update Benchmark Data"))

        if not ui.confirm_action("Update S&P 500 benchmark data?"):
            return

        with ui.progress("Updating benchmark data...") as progress:
            task = progress.add_task("Updating S&P 500 data...", total=100)

            try:
                analyzer = MultiTimeframeAnalyzer(self.pool)
                progress.update(task, advance=50)

                analyzer.update_sp500_data()
                progress.update(task, advance=50)

                ui.status_message("Benchmark data updated successfully", "success")

            except Exception as e:
                ui.status_message(f"Error updating benchmark data: {e}", "error")

        ui.wait_for_user()


def register_comprehensive_analysis_commands(registry: CommandRegistry, pool: DatabaseConnectionPool) -> None:
    """
    Register comprehensive analysis commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("comprehensive_analysis", ComprehensiveAnalysisCommand(pool), "analysis")
    registry.register("view_saved_metrics", ViewSavedMetricsCommand(pool), "analysis")
    registry.register("update_benchmark_data", UpdateBenchmarkDataCommand(pool), "analysis")
