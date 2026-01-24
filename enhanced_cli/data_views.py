"""
Data management views and commands for the Enhanced CLI.

This module provides commands for data management operations such as
updating data for all securities in portfolios.
"""

from enhanced_cli.core.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui

# Import DataRetrieval lazily to avoid startup delay
# This prevents the initial delay caused by DataRetrieval's initialization


class UpdateDataCommand(Command):
    """Command to update data for all securities in portfolios."""

    def __init__(self):
        super().__init__("Update Data", "Update data for all securities in portfolios")

    @error_handler("updating data")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to update data for all securities.

        Args:
            cli: The CLI instance
        """
        if not ui.confirm_action(
            "[bold]This will update data for all securities in your portfolios. "
            "This may take some time. Continue?[/bold]"
        ):
            return

        # Ask if user wants to auto-generate signals after data update
        auto_generate_signals = ui.confirm_action(
            "[bold]Generate trading signals after data update?[/bold]",
            default=True
        )

        # Import here to avoid startup delay
        from data.data_retrieval_consolidated import DataRetrieval

        with ui.progress("Updating stock data...") as progress:
            progress.add_task("", total=None)

            # Create DataRetrieval instance only when needed
            data_retrieval = DataRetrieval(pool=cli.cli.db_pool)
            data_retrieval.update_stock_activity()

        ui.status_message("Data update complete", "success")

        # Auto-generate signals if requested
        if auto_generate_signals:
            ui.console.print("\n[cyan]Generating trading signals with fresh data...[/cyan]")

            try:
                from data.config import Config
                from data.strategy_evaluator import StrategyEvaluator

                config = Config()
                evaluator = StrategyEvaluator(cli.cli.db_pool, config)

                with ui.progress("Evaluating strategies...") as progress:
                    progress.add_task("", total=None)

                    # Generate signals for all active strategies
                    signals = evaluator.batch_evaluate_all_strategies()

                # Display results summary
                if signals:
                    buy_signals = [s for s in signals if s["signal_type"] == "BUY"]
                    sell_signals = [s for s in signals if s["signal_type"] == "SELL"]
                    high_conf = [s for s in signals if s["confidence_score"] >= 80]

                    ui.console.print("\n[bold]Signal Generation Complete:[/bold]")
                    ui.console.print(f"  Total signals: {len(signals)}")
                    ui.console.print(f"  [green]BUY signals: {len(buy_signals)}[/green]")
                    ui.console.print(f"  [red]SELL signals: {len(sell_signals)}[/red]")
                    ui.console.print(f"  [yellow]High confidence (≥80%): {len(high_conf)}[/yellow]")
                    ui.status_message(
                        f"Generated {len(signals)} trading signals",
                        "success"
                    )
                else:
                    ui.status_message(
                        "No signals generated (no strategies active or conditions not met)",
                        "info"
                    )

            except Exception as e:
                ui.status_message(f"Signal generation failed: {str(e)}", "error")


def register_data_commands(registry: CommandRegistry) -> None:
    """
    Register data management commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("update_data", UpdateDataCommand(), "data")
