"""
Trading Strategy views and commands for the Enhanced CLI.

This module provides commands for creating, managing, and executing
trading strategies with technical analysis signals.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from data.config import Config
from data.strategy_backtester import StrategyBacktester
from data.strategy_evaluator import StrategyEvaluator
from data.strategy_performance_dao import StrategyPerformanceDAO
from data.ticker_dao import TickerDao
from data.trading_signal_dao import TradingSignalDAO
from data.trading_strategy_dao import TradingStrategyDAO
from data.utility import DatabaseConnectionPool
from enhanced_cli.core.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class CreateStrategyCommand(Command):
    """Command to create a new trading strategy from templates."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Create Strategy", "Create a new trading strategy from template")
        self.pool = pool
        self.strategy_dao = TradingStrategyDAO(pool)

    @error_handler("creating strategy")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Create New Trading Strategy"))

        # Load templates
        templates = self.strategy_dao.load_templates()
        if not templates:
            ui.status_message("No strategy templates available", "error")
            return

        # Display templates
        ui.console.print("\n[bold]Available Strategy Templates:[/bold]\n")
        template_map = {}
        for i, template in enumerate(templates, 1):
            template_map[str(i)] = template
            ui.console.print(f"[cyan]{i}.[/cyan] [bold]{template['name']}[/bold]")
            ui.console.print(f"   {template['description'][:80]}...")
            ui.console.print(f"   Type: {template['strategy_type']}, Anchor: {template['anchor_indicator']}\n")

        # Select template
        choice = Prompt.ask(
            "[bold]Select template number[/bold]",
            choices=list(template_map.keys()),
            show_choices=False,
        )
        template = template_map[choice]

        # Customize strategy name
        default_name = template["name"]
        custom_name = Prompt.ask("[bold]Strategy name[/bold]", default=default_name)

        # Ask for portfolio/watchlist assignment
        assign_to = ui.menu(
            "Assign strategy to",
            {
                "1": "All portfolios (global)",
                "2": "Specific portfolio",
                "3": "Specific watchlist",
            },
        )

        portfolio_id = None
        watch_list_id = None

        if assign_to == "2":
            portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
        elif assign_to == "3":
            watch_list_id = int(Prompt.ask("[bold]Enter Watchlist ID[/bold]"))

        # Create strategy
        with ui.progress("Creating strategy...") as progress:
            progress.add_task("", total=None)
            strategy_id = self.strategy_dao.create_strategy_from_template(
                template_id=template["id"],
                portfolio_id=portfolio_id,
                watch_list_id=watch_list_id,
                custom_name=custom_name,
            )

        if strategy_id:
            ui.status_message(
                f"Strategy created successfully with ID {strategy_id}", "success"
            )
        else:
            ui.status_message("Failed to create strategy", "error")

        ui.wait_for_user()


class ListStrategiesCommand(Command):
    """Command to list all strategies."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("List Strategies", "List all trading strategies")
        self.pool = pool
        self.strategy_dao = TradingStrategyDAO(pool)

    @error_handler("listing strategies")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Trading Strategies"))

        include_inactive = Confirm.ask("Include inactive strategies?", default=False)

        strategies = self.strategy_dao.get_all_strategies(include_inactive=include_inactive)

        if not strategies:
            ui.status_message("No strategies found", "warning")
            ui.wait_for_user()
            return

        # Create table
        table = Table(title=f"Trading Strategies ({len(strategies)} total)")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Name", style="bold")
        table.add_column("Type", style="blue")
        table.add_column("Anchor", style="green")
        table.add_column("Status", width=10)
        table.add_column("Scope", width=12)

        for strategy in strategies:
            status = "[green]Active[/green]" if strategy["active"] else "[dim]Inactive[/dim]"

            scope = "Global"
            if strategy.get("portfolio_id"):
                scope = f"Portfolio {strategy['portfolio_id']}"
            elif strategy.get("watch_list_id"):
                scope = f"Watchlist {strategy['watch_list_id']}"

            table.add_row(
                str(strategy["id"]),
                strategy["name"][:30],
                strategy["strategy_type"].replace("_", " "),
                strategy["anchor_indicator"],
                status,
                scope,
            )

        ui.console.print(table)
        ui.wait_for_user()


class ViewStrategyDetailsCommand(Command):
    """Command to view detailed strategy information."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("View Strategy Details", "View detailed strategy configuration")
        self.pool = pool
        self.strategy_dao = TradingStrategyDAO(pool)
        self.signal_dao = TradingSignalDAO(pool)

    @error_handler("viewing strategy details")
    def execute(self, cli, *args, **kwargs) -> None:
        strategy_id = kwargs.get("strategy_id")

        if not strategy_id:
            strategy_id = int(Prompt.ask("[bold]Enter Strategy ID[/bold]"))

        strategy = self.strategy_dao.get_strategy(strategy_id)
        if not strategy:
            ui.status_message(f"Strategy {strategy_id} not found", "error")
            ui.wait_for_user()
            return

        # Get statistics
        stats = self.strategy_dao.get_strategy_statistics(strategy_id)

        # Display strategy details
        ui.console.print(ui.section_header(f"Strategy: {strategy['name']}"))

        # Basic info panel
        info_lines = [
            f"[cyan]ID:[/cyan] {strategy['id']}",
            f"[cyan]Type:[/cyan] {strategy['strategy_type'].replace('_', ' ')}",
            f"[cyan]Status:[/cyan] {'Active' if strategy['active'] else 'Inactive'}",
            f"[cyan]Created:[/cyan] {strategy['created_at']}",
        ]

        if strategy.get("description"):
            info_lines.append(f"\n[cyan]Description:[/cyan] {strategy['description']}")

        ui.console.print(Panel("\n".join(info_lines), title="Strategy Information"))

        # Anchor indicator
        anchor_info = [
            f"[yellow]Indicator:[/yellow] {strategy['anchor_indicator']}",
            f"[yellow]Configuration:[/yellow] {strategy['anchor_config']}",
        ]
        ui.console.print(Panel("\n".join(anchor_info), title="Anchor Indicator"))

        # Confirmation indicators
        if strategy.get("confirmation_indicators"):
            conf_lines = []
            for i, conf in enumerate(strategy["confirmation_indicators"], 1):
                required = "Required" if conf.get("required") else "Optional"
                conf_lines.append(
                    f"{i}. {conf['indicator']} ({required}) - Weight: {conf.get('weight', 10)}"
                )
            ui.console.print(
                Panel("\n".join(conf_lines), title="Confirmation Indicators")
            )

        # Performance statistics
        if stats:
            stats_lines = [
                f"[green]Total Signals:[/green] {stats.get('total_signals', 0)}",
                f"[green]Buy Signals:[/green] {stats.get('buy_signals', 0)}",
                f"[green]Sell Signals:[/green] {stats.get('sell_signals', 0)}",
                f"[green]Pending:[/green] {stats.get('pending_signals', 0)}",
            ]

            if stats.get("win_rate") is not None:
                stats_lines.append(f"[green]Win Rate:[/green] {stats['win_rate']:.1f}%")

            ui.console.print(Panel("\n".join(stats_lines), title="Performance Statistics"))

        # Recent signals
        recent_signals = self.signal_dao.get_signal_history(
            strategy_id=strategy_id, limit=5
        )
        if recent_signals:
            ui.console.print("\n[bold]Recent Signals:[/bold]")
            for signal in recent_signals:
                signal_color = "green" if signal["signal_type"] == "BUY" else "red"
                ui.console.print(
                    f"  [{signal_color}]{signal['signal_type']}[/{signal_color}] "
                    f"{signal['ticker_symbol']} @ ${signal['price_at_signal']:.2f} "
                    f"({signal['confidence_score']:.0f}% confidence) - {signal['signal_date'].strftime('%Y-%m-%d')}"
                )

        ui.wait_for_user()


class DeleteStrategyCommand(Command):
    """Command to delete a strategy."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Delete Strategy", "Delete a trading strategy")
        self.pool = pool
        self.strategy_dao = TradingStrategyDAO(pool)

    @error_handler("deleting strategy")
    def execute(self, cli, *args, **kwargs) -> None:
        strategy_id = int(Prompt.ask("[bold]Enter Strategy ID to delete[/bold]"))

        strategy = self.strategy_dao.get_strategy(strategy_id)
        if not strategy:
            ui.status_message(f"Strategy {strategy_id} not found", "error")
            ui.wait_for_user()
            return

        # Show strategy info
        ui.console.print(f"\n[bold]Strategy:[/bold] {strategy['name']}")
        ui.console.print(f"[bold]Type:[/bold] {strategy['strategy_type']}")

        # Confirm deletion
        if not ui.confirm_action(
            f"Delete strategy '{strategy['name']}'? This will also delete all associated signals."
        ):
            ui.status_message("Deletion cancelled", "info")
            ui.wait_for_user()
            return

        # Delete
        success = self.strategy_dao.delete_strategy(strategy_id)

        if success:
            ui.status_message(f"Strategy {strategy_id} deleted successfully", "success")
        else:
            ui.status_message("Failed to delete strategy", "error")

        ui.wait_for_user()


class ToggleStrategyCommand(Command):
    """Command to enable/disable a strategy."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Toggle Strategy", "Enable or disable a strategy")
        self.pool = pool
        self.strategy_dao = TradingStrategyDAO(pool)

    @error_handler("toggling strategy")
    def execute(self, cli, *args, **kwargs) -> None:
        strategy_id = int(Prompt.ask("[bold]Enter Strategy ID[/bold]"))

        strategy = self.strategy_dao.get_strategy(strategy_id)
        if not strategy:
            ui.status_message(f"Strategy {strategy_id} not found", "error")
            ui.wait_for_user()
            return

        current_status = "Active" if strategy["active"] else "Inactive"
        new_status = not strategy["active"]

        ui.console.print(
            f"\n[bold]Strategy:[/bold] {strategy['name']} (Currently: {current_status})"
        )

        action = "Enable" if new_status else "Disable"
        if not ui.confirm_action(f"{action} this strategy?"):
            ui.status_message("Action cancelled", "info")
            ui.wait_for_user()
            return

        success = self.strategy_dao.toggle_strategy(strategy_id, new_status)

        if success:
            new_status_str = "enabled" if new_status else "disabled"
            ui.status_message(f"Strategy {new_status_str} successfully", "success")
        else:
            ui.status_message("Failed to update strategy", "error")

        ui.wait_for_user()


class GenerateSignalsCommand(Command):
    """Command to generate signals for active strategies."""

    def __init__(self, pool: DatabaseConnectionPool, config: Config):
        super().__init__("Generate Signals", "Evaluate strategies and generate signals")
        self.pool = pool
        self.config = config
        self.evaluator = StrategyEvaluator(pool, config)

    @error_handler("generating signals")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Generate Trading Signals"))

        # Select target
        target = ui.menu(
            "Generate signals for",
            {
                "1": "Current Portfolio",
                "2": "Specific Watchlist",
                "3": "Cancel",
            },
        )

        if target == "3":
            return

        signals = []

        def update_progress(current, total, message):
            """Callback to update progress bar."""
            progress.update(task, completed=current, total=total, description=message)

        stats = {}
        if target == "1":
            # Portfolio
            portfolio_id = cli.selected_portfolio if hasattr(cli, "selected_portfolio") else None
            if not portfolio_id:
                portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))

            with ui.progress("Evaluating strategies...") as progress:
                task = progress.add_task("Generating signals...", total=100)
                signals, stats = self.evaluator.batch_evaluate_portfolio(
                    portfolio_id, progress_callback=update_progress
                )
                progress.update(task, completed=True)

        elif target == "2":
            # Watchlist
            watchlist_id = int(Prompt.ask("[bold]Enter Watchlist ID[/bold]"))

            with ui.progress("Evaluating strategies...") as progress:
                task = progress.add_task("Generating signals...", total=100)
                signals, stats = self.evaluator.batch_evaluate_watchlist(
                    watchlist_id, progress_callback=update_progress
                )
                progress.update(task, completed=True)

        # Display results
        ui.console.print(f"\n[bold]Signal Generation Complete:[/bold]")
        ui.console.print(f"  Total signals generated: {len(signals)}")
        
        if stats:
            ui.console.print("\n[bold]Evaluation Statistics:[/bold]")
            ui.console.print(f"  Processed: {stats.get('processed', 0)}")
            ui.console.print(f"  Generated: {stats.get('generated', 0)}")
            ui.console.print(f"  Skipped (Delisted): {stats.get('skipped_delisted', 0)}")
            ui.console.print(f"  Skipped (Duplicate): {stats.get('skipped_duplicate', 0)}")
            ui.console.print(f"  No Signal: {stats.get('no_signal', 0)}")
            if stats.get('errors', 0) > 0:
                ui.console.print(f"  [red]Errors: {stats.get('errors', 0)}[/red]")
            
            if stats.get('last_error'):
                ui.console.print(f"\n[red]Last Error:[/red] {stats['last_error']}")

        if signals:
            buy_signals = [s for s in signals if s["signal_type"] == "BUY"]
            sell_signals = [s for s in signals if s["signal_type"] == "SELL"]
            high_conf = [s for s in signals if s["confidence_score"] >= 80]

            ui.console.print(f"  [green]BUY signals: {len(buy_signals)}[/green]")
            ui.console.print(f"  [red]SELL signals: {len(sell_signals)}[/red]")
            ui.console.print(
                f"  [yellow]High confidence (≥80%): {len(high_conf)}[/yellow]"
            )

            if ui.confirm_action("View active signals now?"):
                ViewActiveSignalsCommand(self.pool).execute(cli)
                return

        ui.wait_for_user()


class ViewActiveSignalsCommand(Command):
    """Command to view active trading signals."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("View Active Signals", "View pending trading signals")
        self.pool = pool
        self.signal_dao = TradingSignalDAO(pool)

    @error_handler("viewing active signals")
    def execute(self, cli, *args, **kwargs) -> None:
        portfolio_id = kwargs.get("portfolio_id")
        if not portfolio_id and hasattr(cli, "selected_portfolio"):
            portfolio_id = cli.selected_portfolio

        ui.console.print(ui.section_header("Active Trading Signals"))

        signals = self.signal_dao.get_active_signals(portfolio_id=portfolio_id)

        if not signals:
            ui.status_message("No active signals found", "warning")
            ui.wait_for_user()
            return

        # Create table
        table = Table(title=f"Active Signals ({len(signals)} total)")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Ticker", style="bold", width=8)
        table.add_column("Strategy", width=20)
        table.add_column("Signal", width=6)
        table.add_column("Confidence", justify="right", width=10)
        table.add_column("Price", justify="right", width=10)
        table.add_column("Date", width=12)

        for signal in signals:
            signal_color = "green" if signal["signal_type"] == "BUY" else "red"
            conf_color = (
                "green"
                if signal["confidence_score"] >= 80
                else "yellow" if signal["confidence_score"] >= 60 else "white"
            )

            table.add_row(
                str(signal["id"]),
                signal["ticker_symbol"],
                signal["strategy_name"][:18],
                f"[{signal_color}]{signal['signal_type']}[/{signal_color}]",
                f"[{conf_color}]{signal['confidence_score']:.0f}%[/{conf_color}]",
                f"${signal['price_at_signal']:.2f}",
                signal["signal_date"].strftime("%Y-%m-%d"),
            )

        ui.console.print(table)

        # Options
        if ui.confirm_action("View details for a specific signal?"):
            signal_id = int(Prompt.ask("[bold]Enter Signal ID[/bold]"))
            ViewSignalDetailsCommand(self.pool).execute(cli, signal_id=signal_id)
            return

        ui.wait_for_user()


class ViewSignalDetailsCommand(Command):
    """Command to view detailed signal information."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("View Signal Details", "View detailed signal information")
        self.pool = pool
        self.signal_dao = TradingSignalDAO(pool)

    @error_handler("viewing signal details")
    def execute(self, cli, *args, **kwargs) -> None:
        signal_id = kwargs.get("signal_id")
        if not signal_id:
            signal_id = int(Prompt.ask("[bold]Enter Signal ID[/bold]"))

        signal = self.signal_dao.get_signal(signal_id)
        if not signal:
            ui.status_message(f"Signal {signal_id} not found", "error")
            ui.wait_for_user()
            return

        ui.console.print(ui.section_header(f"Signal Details: {signal['ticker_symbol']}"))

        # Signal info
        signal_color = "green" if signal["signal_type"] == "BUY" else "red"
        info_lines = [
            f"[cyan]Signal ID:[/cyan] {signal['id']}",
            f"[cyan]Ticker:[/cyan] {signal['ticker_symbol']} ({signal['ticker_name']})",
            f"[cyan]Strategy:[/cyan] {signal['strategy_name']}",
            f"[{signal_color}]Signal Type:[/{signal_color}] [{signal_color}]{signal['signal_type']}[/{signal_color}]",
            f"[cyan]Strength:[/cyan] {signal['signal_strength']}",
            f"[cyan]Confidence:[/cyan] {signal['confidence_score']:.1f}%",
            f"[cyan]Price at Signal:[/cyan] ${signal['price_at_signal']:.2f}",
            f"[cyan]Date:[/cyan] {signal['signal_date'].strftime('%Y-%m-%d %H:%M')}",
            f"[cyan]Status:[/cyan] {signal['status']}",
        ]

        if signal.get("expires_date"):
            info_lines.append(
                f"[cyan]Expires:[/cyan] {signal['expires_date'].strftime('%Y-%m-%d')}"
            )

        ui.console.print(Panel("\n".join(info_lines), title="Signal Information"))

        # Indicator snapshot
        snapshot = signal.get("indicator_snapshot", {})
        if snapshot:
            ui.console.print("\n[bold]Indicator Values at Signal Time:[/bold]")
            all_indicators = snapshot.get("all_indicators", {})

            for indicator_name, indicator_data in all_indicators.items():
                if isinstance(indicator_data, dict):
                    ui.console.print(f"\n[yellow]{indicator_name.upper()}:[/yellow]")
                    for key, value in indicator_data.items():
                        if key not in ["success", "error"]:
                            ui.console.print(f"  {key}: {value}")

        # Linked items
        if signal.get("recommendation_id"):
            ui.console.print(
                f"\n[cyan]Linked AI Recommendation:[/cyan] #{signal['recommendation_id']}"
            )

        if signal.get("transaction_id"):
            ui.console.print(
                f"[cyan]Linked Transaction:[/cyan] #{signal['transaction_id']}"
            )

        ui.wait_for_user()


class BacktestStrategyCommand(Command):
    """Command to backtest a strategy on historical data."""

    def __init__(self, pool: DatabaseConnectionPool, config: Config):
        super().__init__("Backtest Strategy", "Test strategy on historical data")
        self.pool = pool
        self.config = config
        self.backtester = StrategyBacktester(pool, config)
        self.ticker_dao = TickerDao(pool)

    @error_handler("backtesting strategy")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Backtest Trading Strategy"))

        # Get inputs
        strategy_id = int(Prompt.ask("[bold]Enter Strategy ID[/bold]"))
        ticker_symbol = Prompt.ask("[bold]Enter Ticker Symbol[/bold]").upper()
        ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)

        if not ticker_id:
            ui.status_message(f"Ticker {ticker_symbol} not found", "error")
            ui.wait_for_user()
            return

        # Date range
        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        date_input = Prompt.ask(
            "[bold]Start date (YYYY-MM-DD)[/bold]", default=start_date.strftime("%Y-%m-%d")
        )
        start_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        # Run backtest
        with ui.progress("Running backtest...") as progress:
            task = progress.add_task("Backtesting...", total=None)
            result = self.backtester.backtest_strategy(
                strategy_id, ticker_id, start_date, end_date
            )
            progress.update(task, completed=True)

        if not result.get("success"):
            ui.status_message(f"Backtest failed: {result.get('error')}", "error")
            ui.wait_for_user()
            return

        # Display results
        ui.console.print("\n[bold green]Backtest Results:[/bold green]\n")

        # Performance summary
        table = Table(title="Performance Summary", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        return_color = "green" if result["total_return_pct"] >= 0 else "red"

        table.add_row("Initial Capital", f"${result['initial_capital']:,.2f}")
        table.add_row("Final Value", f"${result['final_value']:,.2f}")
        table.add_row(
            "Total Return",
            f"[{return_color}]{result['total_return_pct']:+.2f}%[/{return_color}]",
        )
        table.add_row("Annualized Return", f"{result['annualized_return_pct']:+.2f}%")
        table.add_row("Total Trades", str(result["total_trades"]))
        table.add_row("Win Rate", f"{result['win_rate']:.1f}%")
        table.add_row("Max Drawdown", f"{result['max_drawdown_pct']:.2f}%")
        table.add_row("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")

        if result.get("profit_factor"):
            table.add_row("Profit Factor", f"{result['profit_factor']:.2f}")

        ui.console.print(table)

        ui.wait_for_user()


class StrategyPerformanceCommand(Command):
    """Command to view strategy performance metrics."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Strategy Performance", "View strategy performance metrics")
        self.pool = pool
        self.performance_dao = StrategyPerformanceDAO(pool)
        self.strategy_dao = TradingStrategyDAO(pool)

    @error_handler("viewing performance")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Strategy Performance"))

        strategy_id = int(Prompt.ask("[bold]Enter Strategy ID[/bold]"))

        strategy = self.strategy_dao.get_strategy(strategy_id)
        if not strategy:
            ui.status_message(f"Strategy {strategy_id} not found", "error")
            ui.wait_for_user()
            return

        ui.console.print(f"\n[bold]Strategy:[/bold] {strategy['name']}\n")

        # Get performance for different timeframes
        timeframes = [("7D", 7), ("30D", 30), ("90D", 90)]

        table = Table(title="Performance by Timeframe")
        table.add_column("Period", style="cyan")
        table.add_column("Signals", justify="right")
        table.add_column("Win Rate", justify="right")
        table.add_column("Avg Conf.", justify="right")

        for name, days in timeframes:
            metrics = self.performance_dao.get_timeframe_metrics(strategy_id, name)
            if metrics:
                win_rate_color = (
                    "green"
                    if metrics.get("win_rate", 0) >= 60
                    else "yellow" if metrics.get("win_rate", 0) >= 40 else "red"
                )

                table.add_row(
                    name,
                    str(metrics.get("total_signals", 0)),
                    f"[{win_rate_color}]{metrics.get('win_rate', 0):.1f}%[/{win_rate_color}]",
                    f"{metrics.get('avg_confidence', 0):.1f}%",
                )

        ui.console.print(table)

        # Get overall statistics
        stats = self.strategy_dao.get_strategy_statistics(strategy_id)
        if stats:
            ui.console.print("\n[bold]Overall Statistics:[/bold]")
            ui.console.print(f"  Total Signals: {stats.get('total_signals', 0)}")
            ui.console.print(
                f"  [green]Buy:[/green] {stats.get('buy_signals', 0)}, "
                f"[red]Sell:[/red] {stats.get('sell_signals', 0)}"
            )
            ui.console.print(
                f"  Signals Acted On: {stats.get('acted_on_signals', 0)}"
            )

            if stats.get("total_profit_loss") is not None:
                pl_color = "green" if stats["total_profit_loss"] >= 0 else "red"
                ui.console.print(
                    f"  Total P/L: [{pl_color}]${stats['total_profit_loss']:,.2f}[/{pl_color}]"
                )

        ui.wait_for_user()


class StrategyLeaderboardCommand(Command):
    """Command to view top performing strategies."""

    def __init__(self, pool: DatabaseConnectionPool):
        super().__init__("Strategy Leaderboard", "View top performing strategies")
        self.pool = pool
        self.performance_dao = StrategyPerformanceDAO(pool)

    @error_handler("viewing leaderboard")
    def execute(self, cli, *args, **kwargs) -> None:
        ui.console.print(ui.section_header("Strategy Leaderboard"))

        # Select ranking metric
        metric_choice = ui.menu(
            "Rank by",
            {
                "1": "Win Rate",
                "2": "Total Profit/Loss",
                "3": "Signal Count",
            },
        )

        metric_map = {
            "1": "win_rate",
            "2": "total_profit_loss",
            "3": "total_signals",
        }
        metric = metric_map.get(metric_choice, "win_rate")

        # Get leaderboard
        leaderboard = self.performance_dao.get_strategy_leaderboard(metric=metric, limit=10)

        if not leaderboard:
            ui.status_message("No strategy data available", "warning")
            ui.wait_for_user()
            return

        # Display table
        table = Table(title=f"Top Strategies (by {metric.replace('_', ' ').title()})")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Strategy", style="bold")
        table.add_column("Type", style="blue", width=15)
        table.add_column("Signals", justify="right", width=8)
        table.add_column("Win Rate", justify="right", width=10)
        table.add_column("Total P/L", justify="right", width=12)

        for rank, strat in enumerate(leaderboard, 1):
            win_rate_color = (
                "green"
                if strat.get("win_rate", 0) >= 60
                else "yellow" if strat.get("win_rate", 0) >= 40 else "red"
            )

            pl_value = strat.get("total_profit_loss", 0) or 0
            pl_color = "green" if pl_value >= 0 else "red"

            table.add_row(
                str(rank),
                strat["strategy_name"][:25],
                strat["strategy_type"].replace("_", " "),
                str(strat.get("total_signals", 0)),
                f"[{win_rate_color}]{strat.get('win_rate', 0):.1f}%[/{win_rate_color}]",
                f"[{pl_color}]${pl_value:,.2f}[/{pl_color}]",
            )

        ui.console.print(table)
        ui.wait_for_user()


def register_trading_strategy_commands(
    command_registry: CommandRegistry, pool: DatabaseConnectionPool
) -> None:
    """
    Register all trading strategy commands with the command registry.

    Args:
        command_registry: The command registry
        pool: Database connection pool
    """
    config = Config()

    # Strategy Management
    command_registry.register(
        "create_strategy", CreateStrategyCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "list_strategies", ListStrategiesCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "view_strategy_details", ViewStrategyDetailsCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "delete_strategy", DeleteStrategyCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "toggle_strategy", ToggleStrategyCommand(pool), "trading_strategies"
    )

    # Signal Generation & Viewing
    command_registry.register(
        "generate_signals", GenerateSignalsCommand(pool, config), "trading_strategies"
    )
    command_registry.register(
        "view_active_signals", ViewActiveSignalsCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "view_signal_details", ViewSignalDetailsCommand(pool), "trading_strategies"
    )

    # Performance & Backtesting
    command_registry.register(
        "backtest_strategy", BacktestStrategyCommand(pool, config), "trading_strategies"
    )
    command_registry.register(
        "strategy_performance", StrategyPerformanceCommand(pool), "trading_strategies"
    )
    command_registry.register(
        "strategy_leaderboard", StrategyLeaderboardCommand(pool), "trading_strategies"
    )
