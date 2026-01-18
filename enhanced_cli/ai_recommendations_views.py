"""
AI Recommendations Views for Enhanced CLI

This module provides interface for viewing and managing AI trading recommendations.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from data.ai_recommendations_dao import AIRecommendationsDAO
from data.config import Config
from data.ticker_dao import TickerDao
from data.utility import DatabaseConnectionPool


def register_ai_recommendations_commands(command_registry):
    """Register AI recommendations commands with the command registry."""

    @command_registry.register("view_recommendations", "View AI Recommendations", "recommendations")
    def view_recommendations_command(cli_instance, portfolio_id=None):
        """View active AI recommendations."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        view_active_recommendations(cli_instance.console, portfolio_id)

    @command_registry.register("recommendation_history", "View Recommendation History", "recommendations")
    def recommendation_history_command(cli_instance, portfolio_id=None):
        """View historical AI recommendations."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        view_recommendation_history(cli_instance.console, portfolio_id)

    @command_registry.register("add_recommendation", "Add AI Recommendation", "recommendations")
    def add_recommendation_command(cli_instance, portfolio_id=None):
        """Manually add an AI recommendation."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        add_recommendation(cli_instance.console, portfolio_id)

    @command_registry.register("recommendation_stats", "View Recommendation Statistics", "recommendations")
    def recommendation_stats_command(cli_instance, portfolio_id=None):
        """View statistics about AI recommendations."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        view_recommendation_statistics(cli_instance.console, portfolio_id)

    @command_registry.register("update_recommendation_status", "Update Recommendation Status", "recommendations")
    def update_recommendation_status_command(cli_instance, portfolio_id=None):
        """Update the status of a recommendation."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        update_recommendation_status_interactive(cli_instance.console, portfolio_id)


def create_recommendations_dao():
    """Create and configure the AI recommendations DAO."""
    try:
        config = Config()
        db_config = config.get_database_config()

        # Create database connection pool
        db_pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"],
        )

        return AIRecommendationsDAO(db_pool)

    except Exception as e:
        print(f"Error creating recommendations DAO: {e}")
        return None


def view_active_recommendations(console: Console, portfolio_id: int):
    """Display active AI recommendations for a portfolio."""
    console.print(
        Panel(
            "[bold green]Active AI Recommendations[/bold green]\n\n"
            "These are pending recommendations from the AI assistant.",
            title="AI Recommendations",
            border_style="green",
        )
    )

    dao = create_recommendations_dao()
    if not dao:
        console.print("[red]Error: Could not connect to database.[/red]")
        return

    with console.status("[bold green]Loading recommendations...[/bold green]"):
        recommendations = dao.get_active_recommendations(portfolio_id)
        dao.expire_old_recommendations(portfolio_id)

    if not recommendations:
        console.print("\n[yellow]No active recommendations found.[/yellow]")
        return

    # Create table
    table = Table(title="Active Recommendations", show_header=True)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="cyan")
    table.add_column("Ticker", style="bold yellow")
    table.add_column("Action", style="bold")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Confidence", justify="right")
    table.add_column("Reasoning", style="dim", max_width=40)

    for rec in recommendations:
        # Color code the action
        action = rec['recommendation_type']
        if action == 'BUY':
            action_styled = "[green]BUY[/green]"
        elif action == 'SELL':
            action_styled = "[red]SELL[/red]"
        elif action == 'HOLD':
            action_styled = "[yellow]HOLD[/yellow]"
        else:
            action_styled = f"[cyan]{action}[/cyan]"

        # Format confidence score
        confidence = f"{rec['confidence_score']:.1f}%" if rec['confidence_score'] else "N/A"

        # Format date
        rec_date = rec['recommendation_date'].strftime('%Y-%m-%d') if rec['recommendation_date'] else "N/A"

        # Format quantities and prices
        qty = f"{rec['recommended_quantity']:.2f}" if rec['recommended_quantity'] else "N/A"
        price = f"${rec['recommended_price']:.2f}" if rec['recommended_price'] else "N/A"

        # Truncate reasoning
        reasoning = rec['reasoning'][:37] + "..." if rec['reasoning'] and len(rec['reasoning']) > 40 else (rec['reasoning'] or "")

        table.add_row(
            str(rec['id']),
            rec_date,
            rec['ticker_symbol'],
            action_styled,
            qty,
            price,
            confidence,
            reasoning
        )

    console.print(table)

    # Show details option
    if Confirm.ask("\n[cyan]View detailed information for a recommendation?[/cyan]", default=False):
        rec_id = IntPrompt.ask("[cyan]Enter recommendation ID[/cyan]")
        show_recommendation_details(console, rec_id, dao)


def show_recommendation_details(console: Console, rec_id: int, dao: AIRecommendationsDAO):
    """Show detailed information about a specific recommendation."""
    rec = dao.get_recommendation_by_id(rec_id)

    if not rec:
        console.print(f"[red]Recommendation {rec_id} not found.[/red]")
        return

    # Create details panel
    details = f"""
[bold cyan]Ticker:[/bold cyan] {rec['ticker_symbol']} - {rec['ticker_name']}
[bold cyan]Action:[/bold cyan] {rec['recommendation_type']}
[bold cyan]Recommended Quantity:[/bold cyan] {rec['recommended_quantity'] or 'N/A'}
[bold cyan]Recommended Price:[/bold cyan] ${rec['recommended_price']:.2f} if rec['recommended_price'] else 'N/A'
[bold cyan]Confidence Score:[/bold cyan] {rec['confidence_score']:.1f}% if rec['confidence_score'] else 'N/A'
[bold cyan]Sentiment Score:[/bold cyan] {rec['sentiment_score']:.2f} if rec['sentiment_score'] else 'N/A'
[bold cyan]Date:[/bold cyan] {rec['recommendation_date'].strftime('%Y-%m-%d %H:%M') if rec['recommendation_date'] else 'N/A'}
[bold cyan]Status:[/bold cyan] {rec['status']}

[bold cyan]Reasoning:[/bold cyan]
{rec['reasoning'] or 'No reasoning provided'}
"""

    # Add technical indicators if available
    if rec.get('technical_indicators'):
        details += "\n[bold cyan]Technical Indicators:[/bold cyan]\n"
        indicators = rec['technical_indicators']
        for key, value in indicators.items():
            details += f"  • {key}: {value}\n"

    console.print(Panel(details, title=f"Recommendation #{rec_id}", border_style="cyan"))


def view_recommendation_history(console: Console, portfolio_id: int):
    """Display recommendation history for a portfolio."""
    console.print(
        Panel(
            "[bold blue]AI Recommendation History[/bold blue]\n\n"
            "View past AI recommendations and their outcomes.",
            title="Recommendation History",
            border_style="blue",
        )
    )

    dao = create_recommendations_dao()
    if not dao:
        console.print("[red]Error: Could not connect to database.[/red]")
        return

    # Ask for filter
    status_filter = Prompt.ask(
        "[cyan]Filter by status[/cyan]",
        choices=["ALL", "PENDING", "FOLLOWED", "PARTIALLY_FOLLOWED", "IGNORED", "EXPIRED"],
        default="ALL"
    )

    filter_status = None if status_filter == "ALL" else status_filter

    with console.status("[bold green]Loading recommendations...[/bold green]"):
        recommendations = dao.get_recommendations_by_portfolio(portfolio_id, status=filter_status, limit=50)

    if not recommendations:
        console.print("\n[yellow]No recommendations found.[/yellow]")
        return

    # Create table
    table = Table(title=f"Recommendation History ({status_filter})", show_header=True)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="cyan")
    table.add_column("Ticker", style="bold yellow")
    table.add_column("Action", style="bold")
    table.add_column("Status", style="bold")
    table.add_column("Confidence", justify="right")
    table.add_column("Reasoning", style="dim", max_width=30)

    for rec in recommendations:
        # Color code the status
        status = rec['status']
        if status == 'FOLLOWED':
            status_styled = "[green]FOLLOWED[/green]"
        elif status == 'IGNORED':
            status_styled = "[red]IGNORED[/red]"
        elif status == 'PENDING':
            status_styled = "[yellow]PENDING[/yellow]"
        elif status == 'EXPIRED':
            status_styled = "[dim]EXPIRED[/dim]"
        else:
            status_styled = f"[cyan]{status}[/cyan]"

        # Color code the action
        action = rec['recommendation_type']
        if action == 'BUY':
            action_styled = "[green]BUY[/green]"
        elif action == 'SELL':
            action_styled = "[red]SELL[/red]"
        else:
            action_styled = f"[cyan]{action}[/cyan]"

        confidence = f"{rec['confidence_score']:.1f}%" if rec['confidence_score'] else "N/A"
        rec_date = rec['recommendation_date'].strftime('%Y-%m-%d') if rec['recommendation_date'] else "N/A"
        reasoning = rec['reasoning'][:27] + "..." if rec['reasoning'] and len(rec['reasoning']) > 30 else (rec['reasoning'] or "")

        table.add_row(
            str(rec['id']),
            rec_date,
            rec['ticker_symbol'],
            action_styled,
            status_styled,
            confidence,
            reasoning
        )

    console.print(table)


def add_recommendation(console: Console, portfolio_id: int):
    """Manually add an AI recommendation."""
    console.print(
        Panel(
            "[bold green]Add AI Recommendation[/bold green]\n\n"
            "Manually record an AI recommendation for tracking.",
            title="Add Recommendation",
            border_style="green",
        )
    )

    dao = create_recommendations_dao()
    if not dao:
        console.print("[red]Error: Could not connect to database.[/red]")
        return

    try:
        # Get ticker
        ticker_symbol = Prompt.ask("[cyan]Ticker symbol[/cyan]").upper()

        # Get recommendation type
        rec_type = Prompt.ask(
            "[cyan]Recommendation type[/cyan]",
            choices=["BUY", "SELL", "HOLD", "REDUCE", "INCREASE"],
            default="BUY"
        )

        # Get optional details
        quantity = None
        if Confirm.ask("[cyan]Specify quantity?[/cyan]", default=True):
            quantity = FloatPrompt.ask("[cyan]Recommended quantity[/cyan]")

        price = None
        if Confirm.ask("[cyan]Specify price target?[/cyan]", default=True):
            price = FloatPrompt.ask("[cyan]Recommended price[/cyan]")

        confidence = None
        if Confirm.ask("[cyan]Add confidence score?[/cyan]", default=True):
            confidence = FloatPrompt.ask("[cyan]Confidence score (0-100)[/cyan]")

        reasoning = Prompt.ask("[cyan]Reasoning (optional)[/cyan]", default="")

        # Expiration date (default to 7 days from now)
        expires_in_days = IntPrompt.ask("[cyan]Expires in how many days?[/cyan]", default=7)
        expires_date = datetime.now() + timedelta(days=expires_in_days)

        # Save recommendation
        rec_id = dao.save_recommendation(
            portfolio_id=portfolio_id,
            ticker_symbol=ticker_symbol,
            recommendation_type=rec_type,
            recommended_quantity=quantity,
            recommended_price=price,
            confidence_score=confidence,
            reasoning=reasoning if reasoning else None,
            expires_date=expires_date
        )

        if rec_id:
            console.print(f"\n[green]✅ Recommendation #{rec_id} added successfully![/green]")
        else:
            console.print("\n[red]❌ Failed to add recommendation. Please check the ticker symbol exists.[/red]")

    except Exception as e:
        console.print(f"\n[red]Error adding recommendation: {e}[/red]")


def view_recommendation_statistics(console: Console, portfolio_id: int):
    """Display statistics about AI recommendations."""
    console.print(
        Panel(
            "[bold cyan]AI Recommendation Statistics[/bold cyan]\n\n"
            "Overview of recommendation performance and tracking.",
            title="Statistics",
            border_style="cyan",
        )
    )

    dao = create_recommendations_dao()
    if not dao:
        console.print("[red]Error: Could not connect to database.[/red]")
        return

    with console.status("[bold green]Calculating statistics...[/bold green]"):
        stats = dao.get_recommendation_statistics(portfolio_id)

    if stats['total'] == 0:
        console.print("\n[yellow]No recommendations found for this portfolio.[/yellow]")
        return

    # Create statistics table
    table = Table(title=f"Total Recommendations: {stats['total']}", show_header=True)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("% of Total", justify="right")
    table.add_column("Avg Confidence", justify="right")

    for status, data in stats['by_status'].items():
        count = data['count']
        percentage = (count / stats['total']) * 100
        avg_conf = data['avg_confidence']

        # Color code by status
        if status == 'FOLLOWED':
            status_styled = "[green]FOLLOWED[/green]"
        elif status == 'IGNORED':
            status_styled = "[red]IGNORED[/red]"
        elif status == 'PENDING':
            status_styled = "[yellow]PENDING[/yellow]"
        elif status == 'EXPIRED':
            status_styled = "[dim]EXPIRED[/dim]"
        else:
            status_styled = status

        table.add_row(
            status_styled,
            str(count),
            f"{percentage:.1f}%",
            f"{avg_conf:.1f}%" if avg_conf > 0 else "N/A"
        )

    console.print(table)

    # Calculate follow rate
    followed = stats['by_status'].get('FOLLOWED', {}).get('count', 0)
    partially_followed = stats['by_status'].get('PARTIALLY_FOLLOWED', {}).get('count', 0)
    ignored = stats['by_status'].get('IGNORED', {}).get('count', 0)
    total_resolved = followed + partially_followed + ignored

    if total_resolved > 0:
        follow_rate = ((followed + partially_followed) / total_resolved) * 100
        console.print(f"\n[cyan]Follow Rate:[/cyan] [bold]{follow_rate:.1f}%[/bold] (recommendations followed or partially followed)")


def update_recommendation_status_interactive(console: Console, portfolio_id: int):
    """Interactively update the status of a recommendation."""
    console.print(
        Panel(
            "[bold yellow]Update Recommendation Status[/bold yellow]\n\n"
            "Mark recommendations as followed, ignored, etc.",
            title="Update Status",
            border_style="yellow",
        )
    )

    dao = create_recommendations_dao()
    if not dao:
        console.print("[red]Error: Could not connect to database.[/red]")
        return

    # Show active recommendations
    with console.status("[bold green]Loading recommendations...[/bold green]"):
        recommendations = dao.get_active_recommendations(portfolio_id)

    if not recommendations:
        console.print("\n[yellow]No active recommendations to update.[/yellow]")
        return

    # Quick list
    console.print("\n[bold]Active Recommendations:[/bold]")
    for rec in recommendations:
        console.print(f"  {rec['id']}: {rec['ticker_symbol']} - {rec['recommendation_type']}")

    # Get recommendation ID
    rec_id = IntPrompt.ask("\n[cyan]Enter recommendation ID to update[/cyan]")

    # Verify it exists
    rec = dao.get_recommendation_by_id(rec_id)
    if not rec:
        console.print(f"[red]Recommendation {rec_id} not found.[/red]")
        return

    console.print(f"\nUpdating: {rec['ticker_symbol']} - {rec['recommendation_type']}")

    # Get new status
    new_status = Prompt.ask(
        "[cyan]New status[/cyan]",
        choices=["FOLLOWED", "PARTIALLY_FOLLOWED", "IGNORED", "EXPIRED"],
        default="FOLLOWED"
    )

    # Update status
    if dao.update_recommendation_status(rec_id, new_status):
        console.print(f"\n[green]✅ Recommendation #{rec_id} status updated to {new_status}[/green]")
    else:
        console.print("\n[red]❌ Failed to update recommendation status.[/red]")
