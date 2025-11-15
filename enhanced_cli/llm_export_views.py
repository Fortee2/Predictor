"""
LLM Export views for the Enhanced CLI.

This module provides commands for generating LLM-friendly portfolio data exports
in structured JSON format for analysis and recommendations.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from rich.prompt import Prompt

from enhanced_cli.command import Command, CommandRegistry, error_handler
from enhanced_cli.ui_components import ui


class PortfolioSnapshotCommand(Command):
    """Command to generate a comprehensive LLM-friendly portfolio snapshot."""

    def __init__(self):
        super().__init__(
            "Portfolio Snapshot", "Generate LLM-friendly portfolio analysis data"
        )

    @error_handler("generating portfolio snapshot")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to generate a comprehensive portfolio snapshot.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # List portfolios and ask for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand

                list_command = ListPortfoliosCommand()
                list_command.execute(cli)

                try:
                    portfolio_id = int(
                        Prompt.ask("[bold]Enter Portfolio ID for snapshot[/bold]")
                    )
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return

        # Get portfolio info
        portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)
        if not portfolio:
            ui.status_message(f"Portfolio with ID {portfolio_id} not found.", "error")
            return

        ui.console.print(
            ui.section_header(f"Generating Portfolio Snapshot: {portfolio['name']}")
        )

        with ui.progress("Gathering portfolio data...") as progress:
            task = progress.add_task("Collecting data...", total=100)

            # Generate comprehensive snapshot
            snapshot = self._generate_portfolio_snapshot(
                cli, portfolio_id, portfolio, progress, task
            )

        if snapshot:
            # Display the JSON output
            ui.console.print(
                "\n[bold green]Portfolio Snapshot (LLM-Ready Format):[/bold green]"
            )
            ui.console.print("=" * 80)

            # Pretty print the JSON
            json_output = json.dumps(snapshot, indent=2, default=self._json_serializer)
            ui.console.print(json_output)

            # Ask if user wants to save to file
            if ui.confirm_action("Save snapshot to file?"):
                filename = f"portfolio_snapshot_{portfolio_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(filename, "w") as f:
                        json.dump(snapshot, f, indent=2, default=self._json_serializer)
                    ui.status_message(f"Snapshot saved to {filename}", "success")
                except Exception as e:
                    ui.status_message(f"Error saving file: {e}", "error")
        else:
            ui.status_message("Failed to generate portfolio snapshot", "error")

    def _generate_portfolio_snapshot(
        self, cli, portfolio_id: int, portfolio: Dict, progress, task
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive portfolio snapshot.

        Args:
            cli: The CLI instance
            portfolio_id: Portfolio ID
            portfolio: Portfolio data
            progress: Progress tracker
            task: Progress task

        Returns:
            Dictionary containing comprehensive portfolio data
        """
        try:
            snapshot = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "portfolio_id": portfolio_id,
                    "data_version": "1.0",
                },
                "portfolio_info": {},
                "financial_summary": {},
                "holdings": [],
                "performance_metrics": {},
                "technical_analysis": {},
                "risk_analysis": {},
                "market_context": {},
            }

            # Basic portfolio information
            progress.update(task, advance=10)
            snapshot["portfolio_info"] = {
                "name": portfolio["name"],
                "description": portfolio.get("description", ""),
                "created_date": (
                    portfolio["date_added"].isoformat()
                    if portfolio["date_added"]
                    else None
                ),
                "active": portfolio.get("active", True),
                "last_updated": datetime.now().isoformat(),
            }

            # Financial summary using universal value service
            progress.update(task, advance=10)

            # Use universal value service for consistent calculations
            portfolio_result = cli.cli.value_service.calculate_portfolio_value(
                portfolio_id,
                include_cash=True,
                include_dividends=True,  # Include for comprehensive LLM analysis
                use_current_prices=True,
            )

            holdings_data = []
            if portfolio_result["positions"]:
                for ticker_id, position in portfolio_result["positions"].items():
                    # Get additional ticker data for company name
                    ticker_data = cli.cli.ticker_dao.get_ticker_data(ticker_id)

                    holding = {
                        "symbol": position["symbol"],
                        "company_name": ticker_data.get("name", ""),
                        "shares": position["shares"],
                        "average_cost": position["avg_price"],
                        "current_price": position["current_price"],
                        "market_value": position["position_value"],
                        "unrealized_gain_loss": position["gain_loss"],
                        "unrealized_gain_loss_percent": position["gain_loss_pct"],
                        "weight_percent": position["weight_pct"],
                    }
                    holdings_data.append(holding)

            snapshot["financial_summary"] = {
                "cash_balance": portfolio_result["cash_balance"],
                "total_stock_value": portfolio_result["stock_value"],
                "dividend_value": portfolio_result["dividend_value"],
                "total_portfolio_value": portfolio_result["total_value"],
                "number_of_holdings": len(holdings_data),
                "currency": "USD",
            }

            snapshot["holdings"] = holdings_data
            progress.update(task, advance=20)

            # Performance metrics (if available)
            try:
                from data.multi_timeframe_analyzer import MultiTimeframeAnalyzer

                analyzer = MultiTimeframeAnalyzer()
                portfolio_metrics = analyzer.get_portfolio_metrics(
                    portfolio_id, date.today()
                )
                if portfolio_metrics:
                    snapshot["performance_metrics"] = portfolio_metrics
                analyzer.close_connection()
            except Exception as e:
                snapshot["performance_metrics"] = {
                    "error": f"Could not load performance metrics: {str(e)}"
                }

            progress.update(task, advance=20)

            # Technical analysis for holdings
            technical_data = {}
            for holding in holdings_data:
                symbol = holding["symbol"]
                try:
                    ticker_id = cli.cli.ticker_dao.get_ticker_id(symbol)
                    if ticker_id:
                        tech_analysis = {}

                        # Get RSI
                        try:
                            cli.cli.rsi_calc.calculateRSI(ticker_id)
                            rsi_result = cli.cli.rsi_calc.retrievePrices(1, ticker_id)
                            if not rsi_result.empty:
                                latest_rsi = rsi_result.iloc[-1]
                                tech_analysis["rsi"] = {
                                    "value": float(latest_rsi["rsi"]),
                                    "date": rsi_result.index[-1].strftime("%Y-%m-%d"),
                                    "status": (
                                        "Overbought"
                                        if latest_rsi["rsi"] > 70
                                        else (
                                            "Oversold"
                                            if latest_rsi["rsi"] < 30
                                            else "Neutral"
                                        )
                                    ),
                                }
                        except Exception as e:
                            tech_analysis["rsi"] = {
                                "error": f"RSI calculation failed: {str(e)}"
                            }

                        # Get moving averages
                        try:
                            ma_data = cli.cli.moving_avg.update_moving_averages(
                                ticker_id, 20
                            )
                            if not ma_data.empty:
                                latest_ma = ma_data.iloc[-1]
                                date_str = str(ma_data.index[-1]).split()[0]
                                tech_analysis["moving_average_20"] = {
                                    "value": float(latest_ma.iloc[0]),
                                    "date": date_str,
                                }
                        except Exception as e:
                            tech_analysis["moving_average_20"] = {
                                "error": f"MA calculation failed: {str(e)}"
                            }

                        # Get Bollinger Bands
                        try:
                            bb_data = cli.cli.bb_analyzer.generate_bollinger_band_data(
                                ticker_id
                            )
                            if bb_data:
                                tech_analysis["bollinger_bands"] = {
                                    "mean": float(bb_data["bollinger_bands"]["mean"]),
                                    "stddev": float(
                                        bb_data["bollinger_bands"]["stddev"]
                                    ),
                                }
                        except Exception as e:
                            tech_analysis["bollinger_bands"] = {
                                "error": f"BB calculation failed: {str(e)}"
                            }

                        technical_data[symbol] = tech_analysis
                    else:
                        technical_data[symbol] = {"error": "Ticker ID not found"}
                except Exception as e:
                    technical_data[symbol] = {
                        "error": f"Could not load technical data: {str(e)}"
                    }

            snapshot["technical_analysis"] = technical_data
            progress.update(task, advance=20)

            # Risk analysis
            snapshot["risk_analysis"] = self._calculate_risk_metrics(
                holdings_data, portfolio_result["total_value"]
            )
            progress.update(task, advance=10)

            # Market context (news sentiment if available)
            market_context = {}
            for holding in holdings_data:
                symbol = holding["symbol"]
                try:
                    ticker_id = cli.cli.ticker_dao.get_ticker_id(symbol)
                    if ticker_id:
                        sentiment_data = cli.cli.news_analyzer.get_sentiment_summary(
                            ticker_id, symbol
                        )
                        if (
                            sentiment_data
                            and sentiment_data["status"]
                            != "No sentiment data available"
                        ):
                            market_context[symbol] = {
                                "status": sentiment_data["status"],
                                "average_sentiment": sentiment_data[
                                    "average_sentiment"
                                ],
                                "article_count": sentiment_data["article_count"],
                            }
                        else:
                            market_context[symbol] = {
                                "status": "No sentiment data available"
                            }
                    else:
                        market_context[symbol] = {"error": "Ticker ID not found"}
                except Exception as e:
                    market_context[symbol] = {
                        "error": f"Could not load sentiment data: {str(e)}"
                    }

            snapshot["market_context"] = market_context
            progress.update(task, advance=10)

            return snapshot

        except Exception as e:
            ui.status_message(f"Error generating snapshot: {e}", "error")
            return None

    def _calculate_risk_metrics(
        self, holdings_data: List[Dict], total_value: float
    ) -> Dict[str, Any]:
        """
        Calculate basic risk metrics from holdings data.

        Args:
            holdings_data: List of holding dictionaries
            total_value: Total portfolio value

        Returns:
            Dictionary of risk metrics
        """
        if not holdings_data or total_value <= 0:
            return {"error": "Insufficient data for risk calculation"}

        # Concentration risk
        max_weight = max(holding["weight_percent"] for holding in holdings_data)
        top_3_weight = sum(
            sorted(
                [holding["weight_percent"] for holding in holdings_data], reverse=True
            )[:3]
        )

        # Sector diversification (basic - would need sector data for full analysis)
        num_holdings = len(holdings_data)

        return {
            "concentration_risk": {
                "largest_position_percent": max_weight,
                "top_3_positions_percent": top_3_weight,
                "number_of_holdings": num_holdings,
            },
            "diversification_score": min(
                100, (num_holdings / 20) * 100
            ),  # Simple score based on number of holdings
            "risk_level": (
                "High" if max_weight > 20 else "Medium" if max_weight > 10 else "Low"
            ),
        }

    def _json_serializer(self, obj):
        """JSON serializer for special types."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class LLMAnalysisPromptCommand(Command):
    """Command to generate analysis prompts for LLM consumption."""

    def __init__(self):
        super().__init__("LLM Analysis Prompt", "Generate analysis prompts for LLM")

    @error_handler("generating LLM prompt")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to generate LLM analysis prompts.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
        """
        portfolio_id = kwargs.get("portfolio_id")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # List portfolios and ask for selection
                from enhanced_cli.portfolio_views import ListPortfoliosCommand

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

        ui.console.print(ui.section_header(f"LLM Analysis Prompt: {portfolio['name']}"))

        # Generate snapshot first
        snapshot_cmd = PortfolioSnapshotCommand()
        with ui.progress("Generating portfolio data...") as progress:
            task = progress.add_task("", total=100)
            snapshot = snapshot_cmd._generate_portfolio_snapshot(
                cli, portfolio_id, portfolio, progress, task
            )

        if not snapshot:
            ui.status_message("Failed to generate portfolio data", "error")
            return

        # Generate analysis prompt
        prompt = self._generate_analysis_prompt(snapshot)

        ui.console.print("\n[bold green]LLM Analysis Prompt:[/bold green]")
        ui.console.print("=" * 80)
        ui.console.print(prompt)

        # Ask if user wants to save to file
        if ui.confirm_action("Save prompt to file?"):
            filename = f"llm_prompt_{portfolio_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(filename, "w") as f:
                    f.write(prompt)
                ui.status_message(f"Prompt saved to {filename}", "success")
            except Exception as e:
                ui.status_message(f"Error saving file: {e}", "error")

    def _generate_analysis_prompt(self, snapshot: Dict[str, Any]) -> str:
        """
        Generate a comprehensive analysis prompt for LLM.

        Args:
            snapshot: Portfolio snapshot data

        Returns:
            Formatted prompt string
        """
        portfolio_name = snapshot["portfolio_info"]["name"]
        total_value = snapshot["financial_summary"]["total_portfolio_value"]
        num_holdings = snapshot["financial_summary"]["number_of_holdings"]

        prompt = f"""Please analyze the following investment portfolio and provide recommendations:

PORTFOLIO OVERVIEW:
Name: {portfolio_name}
Total Value: ${total_value:,.2f}
Number of Holdings: {num_holdings}
Cash Balance: ${snapshot["financial_summary"]["cash_balance"]:,.2f}

PORTFOLIO DATA:
{json.dumps(snapshot, indent=2, default=lambda x: x.isoformat() if isinstance(x, (datetime, date)) else float(x) if isinstance(x, Decimal) else str(x))}

ANALYSIS REQUESTED:
1. Portfolio Composition Analysis
   - Evaluate asset allocation and diversification
   - Identify concentration risks
   - Assess sector/geographic exposure

2. Performance Assessment
   - Analyze returns across different timeframes
   - Compare against benchmarks (S&P 500)
   - Evaluate risk-adjusted returns (Sharpe ratio, etc.)

3. Risk Analysis
   - Identify key risk factors
   - Assess portfolio volatility
   - Evaluate maximum drawdown scenarios

4. Technical Analysis Summary
   - Review RSI indicators for holdings
   - Analyze moving average trends
   - Assess Bollinger Bands signals

5. Recommendations
   - Suggest portfolio rebalancing if needed
   - Identify potential buying/selling opportunities
   - Recommend risk management strategies
   - Suggest diversification improvements

Please provide specific, actionable recommendations based on the data provided."""

        return prompt


def register_llm_export_commands(registry: CommandRegistry) -> None:
    """
    Register LLM export commands with the command registry.

    Args:
        registry: The command registry to register commands with
    """
    registry.register("portfolio_snapshot", PortfolioSnapshotCommand(), "export")
    registry.register("llm_analysis_prompt", LLMAnalysisPromptCommand(), "export")
