from datetime import date
from typing import Dict, List, Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text


class ComprehensivePerformanceFormatter:
    """
    Formats comprehensive portfolio performance data into readable tables and reports.
    Supports the requested tabular format: Holding | 1M | 3M | 6M | 1Y | 2Y | 5Y | Max DD | Sharpe | vs S&P500
    """

    def __init__(self):
        self.console = Console()

    def format_percentage(self, value: Optional[float], precision: int = 1) -> str:
        """Format a percentage value with proper styling."""
        if value is None:
            return "N/A"

        formatted = f"{value:.{precision}f}%"
        return formatted

    def format_ratio(self, value: Optional[float], precision: int = 2) -> str:
        """Format a ratio value."""
        if value is None:
            return "N/A"
        return f"{value:.{precision}f}"

    def get_performance_color(self, value: Optional[float]) -> str:
        """Get color for performance values (green for positive, red for negative)."""
        if value is None:
            return "white"
        return "green" if value >= 0 else "red"

    def create_portfolio_summary_table(
        self, portfolio_metrics: Dict, portfolio_name: str
    ) -> Table:
        """
        Create a summary table for portfolio performance across timeframes.

        Args:
            portfolio_metrics: Dictionary of metrics by timeframe
            portfolio_name: Name of the portfolio

        Returns:
            Rich Table object
        """
        table = Table(
            title=f"Portfolio Performance Summary: {portfolio_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold blue",
        )

        # Add columns
        table.add_column("Metric", style="bold", width=20)

        timeframes = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
        for tf in timeframes:
            if tf in portfolio_metrics:
                table.add_column(tf, justify="right", width=10)

        # Define metrics to display
        metrics_config = [
            ("Total Return", "total_return_pct", self.format_percentage, True),
            (
                "Annualized Return",
                "annualized_return_pct",
                self.format_percentage,
                True,
            ),
            ("Volatility", "volatility_pct", self.format_percentage, False),
            ("Sharpe Ratio", "sharpe_ratio", self.format_ratio, True),
            ("Max Drawdown", "max_drawdown_pct", self.format_percentage, False),
            ("Alpha", "alpha", self.format_percentage, True),
            ("Beta", "beta", self.format_ratio, False),
            ("vs S&P 500", "excess_return_pct", self.format_percentage, True),
        ]

        # Add rows for each metric
        for metric_name, metric_key, formatter, is_performance in metrics_config:
            row_data = [metric_name]

            for tf in timeframes:
                if tf in portfolio_metrics and metric_key in portfolio_metrics[tf]:
                    value = portfolio_metrics[tf][metric_key]
                    formatted_value = formatter(value)

                    if is_performance and value is not None:
                        color = self.get_performance_color(value)
                        row_data.append(f"[{color}]{formatted_value}[/{color}]")
                    else:
                        row_data.append(formatted_value)
                else:
                    row_data.append("N/A")

            table.add_row(*row_data)

        return table

    def create_holdings_performance_table(
        self, holdings_metrics: Dict, portfolio_name: str
    ) -> Table:
        """
        Create the requested tabular format for individual holdings.
        Format: Holding | 1M | 3M | 6M | 1Y | 2Y | 5Y | Max DD | Sharpe | vs S&P500

        Args:
            holdings_metrics: Dictionary of holdings metrics by ticker symbol
            portfolio_name: Name of the portfolio

        Returns:
            Rich Table object
        """
        table = Table(
            title=f"Holdings Performance Analysis: {portfolio_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold blue",
        )

        # Add columns
        table.add_column("Holding", style="bold", width=8)
        table.add_column("1M", justify="right", width=8)
        table.add_column("3M", justify="right", width=8)
        table.add_column("6M", justify="right", width=8)
        table.add_column("1Y", justify="right", width=8)
        table.add_column("2Y", justify="right", width=8)
        table.add_column("5Y", justify="right", width=8)
        table.add_column("Max DD", justify="right", width=8)
        table.add_column("Sharpe", justify="right", width=8)
        table.add_column("vs S&P500", justify="right", width=10)

        # Add rows for each holding
        for ticker_symbol, timeframe_metrics in holdings_metrics.items():
            row_data = [ticker_symbol]

            # Add return data for each timeframe
            timeframes = ["1M", "3M", "6M", "1Y", "2Y", "5Y"]
            for tf in timeframes:
                if tf in timeframe_metrics:
                    value = timeframe_metrics[tf].get("total_return_pct")
                    formatted_value = self.format_percentage(value)

                    if value is not None:
                        color = self.get_performance_color(value)
                        row_data.append(f"[{color}]{formatted_value}[/{color}]")
                    else:
                        row_data.append("N/A")
                else:
                    row_data.append("N/A")

            # Add Max Drawdown (use 1Y timeframe as representative)
            max_dd = None
            for tf in ["1Y", "6M", "3M", "1M"]:  # Try timeframes in order of preference
                if (
                    tf in timeframe_metrics
                    and "max_drawdown_pct" in timeframe_metrics[tf]
                ):
                    max_dd = timeframe_metrics[tf]["max_drawdown_pct"]
                    break

            max_dd_formatted = self.format_percentage(max_dd)
            if max_dd is not None:
                row_data.append(f"[red]{max_dd_formatted}[/red]")
            else:
                row_data.append("N/A")

            # Add Sharpe Ratio (use 1Y timeframe as representative)
            sharpe = None
            for tf in ["1Y", "6M", "3M", "1M"]:
                if tf in timeframe_metrics and "sharpe_ratio" in timeframe_metrics[tf]:
                    sharpe = timeframe_metrics[tf]["sharpe_ratio"]
                    break

            sharpe_formatted = self.format_ratio(sharpe)
            if sharpe is not None:
                color = self.get_performance_color(sharpe)
                row_data.append(f"[{color}]{sharpe_formatted}[/{color}]")
            else:
                row_data.append("N/A")

            # Add vs S&P 500 (use 1Y timeframe as representative)
            excess_return = None
            for tf in ["1Y", "6M", "3M", "1M"]:
                if (
                    tf in timeframe_metrics
                    and "excess_return_pct" in timeframe_metrics[tf]
                ):
                    excess_return = timeframe_metrics[tf]["excess_return_pct"]
                    break

            excess_formatted = self.format_percentage(excess_return)
            if excess_return is not None:
                color = self.get_performance_color(excess_return)
                row_data.append(f"[{color}]{excess_formatted}[/{color}]")
            else:
                row_data.append("N/A")

            table.add_row(*row_data)

        return table

    def create_risk_metrics_table(
        self, portfolio_metrics: Dict, portfolio_name: str
    ) -> Table:
        """
        Create a detailed risk metrics table.

        Args:
            portfolio_metrics: Dictionary of metrics by timeframe
            portfolio_name: Name of the portfolio

        Returns:
            Rich Table object
        """
        table = Table(
            title=f"Risk Analysis: {portfolio_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold red",
        )

        # Add columns
        table.add_column("Risk Metric", style="bold", width=20)

        timeframes = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
        for tf in timeframes:
            if tf in portfolio_metrics:
                table.add_column(tf, justify="right", width=10)

        # Risk metrics to display
        risk_metrics = [
            ("Volatility", "volatility_pct", self.format_percentage),
            ("Max Drawdown", "max_drawdown_pct", self.format_percentage),
            ("Beta", "beta", self.format_ratio),
            ("Up Capture", "up_capture_ratio", self.format_ratio),
            ("Down Capture", "down_capture_ratio", self.format_ratio),
        ]

        # Add rows for each risk metric
        for metric_name, metric_key, formatter in risk_metrics:
            row_data = [metric_name]

            for tf in timeframes:
                if tf in portfolio_metrics and metric_key in portfolio_metrics[tf]:
                    value = portfolio_metrics[tf][metric_key]
                    formatted_value = formatter(value)

                    # Color coding for risk metrics
                    if (
                        metric_key in ["volatility_pct", "max_drawdown_pct"]
                        and value is not None
                    ):
                        # Higher volatility/drawdown = red, lower = green
                        color = (
                            "red" if value > 15 else "yellow" if value > 10 else "green"
                        )
                        row_data.append(f"[{color}]{formatted_value}[/{color}]")
                    elif metric_key == "beta" and value is not None:
                        # Beta > 1 = red (more volatile), < 1 = green (less volatile)
                        color = (
                            "red"
                            if value > 1.2
                            else "yellow" if value > 0.8 else "green"
                        )
                        row_data.append(f"[{color}]{formatted_value}[/{color}]")
                    else:
                        row_data.append(formatted_value)
                else:
                    row_data.append("N/A")

            table.add_row(*row_data)

        return table

    def create_benchmark_comparison_table(
        self, portfolio_metrics: Dict, portfolio_name: str
    ) -> Table:
        """
        Create a benchmark comparison table.

        Args:
            portfolio_metrics: Dictionary of metrics by timeframe
            portfolio_name: Name of the portfolio

        Returns:
            Rich Table object
        """
        table = Table(
            title=f"Benchmark Comparison: {portfolio_name} vs S&P 500",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        # Add columns
        table.add_column("Timeframe", style="bold", width=12)
        table.add_column("Portfolio", justify="right", width=12)
        table.add_column("S&P 500", justify="right", width=12)
        table.add_column("Excess Return", justify="right", width=12)
        table.add_column("Alpha", justify="right", width=10)
        table.add_column("Beta", justify="right", width=8)

        timeframes = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]

        for tf in timeframes:
            if tf not in portfolio_metrics:
                continue

            metrics = portfolio_metrics[tf]

            # Portfolio return
            portfolio_return = metrics.get("total_return_pct")
            portfolio_formatted = self.format_percentage(portfolio_return)
            if portfolio_return is not None:
                port_color = self.get_performance_color(portfolio_return)
                portfolio_formatted = (
                    f"[{port_color}]{portfolio_formatted}[/{port_color}]"
                )

            # Benchmark return
            benchmark_return = metrics.get("benchmark_return_pct")
            benchmark_formatted = self.format_percentage(benchmark_return)
            if benchmark_return is not None:
                bench_color = self.get_performance_color(benchmark_return)
                benchmark_formatted = (
                    f"[{bench_color}]{benchmark_formatted}[/{bench_color}]"
                )

            # Excess return
            excess_return = metrics.get("excess_return_pct")
            excess_formatted = self.format_percentage(excess_return)
            if excess_return is not None:
                excess_color = self.get_performance_color(excess_return)
                excess_formatted = (
                    f"[{excess_color}]{excess_formatted}[/{excess_color}]"
                )

            # Alpha
            alpha = metrics.get("alpha")
            alpha_formatted = self.format_percentage(alpha)
            if alpha is not None:
                alpha_color = self.get_performance_color(alpha)
                alpha_formatted = f"[{alpha_color}]{alpha_formatted}[/{alpha_color}]"

            # Beta
            beta = metrics.get("beta")
            beta_formatted = self.format_ratio(beta)

            table.add_row(
                tf,
                portfolio_formatted,
                benchmark_formatted,
                excess_formatted,
                alpha_formatted,
                beta_formatted,
            )

        return table

    def create_market_events_context_table(
        self, portfolio_id: int, market_events_performance: Dict
    ) -> Table:
        """
        Create a table showing portfolio performance during major market events.

        Args:
            portfolio_id: Portfolio ID
            market_events_performance: Dictionary of performance during market events

        Returns:
            Rich Table object
        """
        table = Table(
            title="Performance During Major Market Events",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        # Add columns
        table.add_column("Event", style="bold", width=25)
        table.add_column("Period", width=20)
        table.add_column("Portfolio", justify="right", width=12)
        table.add_column("S&P 500", justify="right", width=12)
        table.add_column("Relative", justify="right", width=12)
        table.add_column("Severity", justify="center", width=10)

        # Add rows for each market event
        for event_name, event_data in market_events_performance.items():
            period = f"{event_data.get('start_date', 'N/A')} to {event_data.get('end_date', 'N/A')}"

            portfolio_return = event_data.get("portfolio_return_pct")
            portfolio_formatted = self.format_percentage(portfolio_return)
            if portfolio_return is not None:
                port_color = self.get_performance_color(portfolio_return)
                portfolio_formatted = (
                    f"[{port_color}]{portfolio_formatted}[/{port_color}]"
                )

            benchmark_return = event_data.get("benchmark_return_pct")
            benchmark_formatted = self.format_percentage(benchmark_return)
            if benchmark_return is not None:
                bench_color = self.get_performance_color(benchmark_return)
                benchmark_formatted = (
                    f"[{bench_color}]{benchmark_formatted}[/{bench_color}]"
                )

            relative_return = event_data.get("relative_return_pct")
            relative_formatted = self.format_percentage(relative_return)
            if relative_return is not None:
                rel_color = self.get_performance_color(relative_return)
                relative_formatted = f"[{rel_color}]{relative_formatted}[/{rel_color}]"

            severity = event_data.get("severity", "N/A")
            severity_color = {
                "LOW": "green",
                "MEDIUM": "yellow",
                "HIGH": "red",
                "EXTREME": "bright_red",
            }.get(severity, "white")

            table.add_row(
                event_name,
                period,
                portfolio_formatted,
                benchmark_formatted,
                relative_formatted,
                f"[{severity_color}]{severity}[/{severity_color}]",
            )

        return table

    def display_comprehensive_analysis(
        self,
        portfolio_metrics: Dict,
        holdings_metrics: Dict = None,
        portfolio_name: str = "Portfolio",
        market_events_performance: Dict = None,
    ):
        """
        Display the complete comprehensive analysis with all tables.

        Args:
            portfolio_metrics: Portfolio-level metrics by timeframe
            holdings_metrics: Individual holdings metrics (optional)
            portfolio_name: Name of the portfolio
            market_events_performance: Performance during market events (optional)
        """
        self.console.print("\n")
        self.console.print("=" * 100, style="bold blue")
        self.console.print(
            f"COMPREHENSIVE PORTFOLIO ANALYSIS", style="bold blue", justify="center"
        )
        self.console.print("=" * 100, style="bold blue")
        self.console.print("\n")

        # Portfolio Summary Table
        if portfolio_metrics:
            summary_table = self.create_portfolio_summary_table(
                portfolio_metrics, portfolio_name
            )
            self.console.print(summary_table)
            self.console.print("\n")

        # Holdings Performance Table (the requested format)
        if holdings_metrics:
            holdings_table = self.create_holdings_performance_table(
                holdings_metrics, portfolio_name
            )
            self.console.print(holdings_table)
            self.console.print("\n")

        # Risk Metrics Table
        if portfolio_metrics:
            risk_table = self.create_risk_metrics_table(
                portfolio_metrics, portfolio_name
            )
            self.console.print(risk_table)
            self.console.print("\n")

        # Benchmark Comparison Table
        if portfolio_metrics:
            benchmark_table = self.create_benchmark_comparison_table(
                portfolio_metrics, portfolio_name
            )
            self.console.print(benchmark_table)
            self.console.print("\n")

        # Market Events Context Table
        if market_events_performance:
            events_table = self.create_market_events_context_table(
                1, market_events_performance
            )
            self.console.print(events_table)
            self.console.print("\n")

        self.console.print("=" * 100, style="bold blue")
        self.console.print(
            "Analysis complete. Data as of:",
            date.today().strftime("%Y-%m-%d"),
            style="italic",
        )
        self.console.print("=" * 100, style="bold blue")
