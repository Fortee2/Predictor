"""Command to list all portfolios."""

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


class ListPortfoliosCommand(Command):
    """Command to list all portfolios."""

    def __init__(self):
        super().__init__("List Portfolios", "Display all portfolios")

    @error_handler("listing portfolios")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to list all portfolios.

        Args:
            cli: The CLI instance
        """
        with ui.progress("Loading portfolios...") as progress:
            progress.add_task("", total=None)

            # Fetch portfolios
            portfolios = []
            try:
                cursor = cli.cli.portfolio_dao.current_connection.cursor(dictionary=True)
                cursor.execute("SELECT * FROM portfolio ORDER BY name")
                portfolios = cursor.fetchall()
                cursor.close()
            except Exception as e:
                ui.status_message(f"Error loading portfolios: {str(e)}", "error")
                return

        if not portfolios:
            ui.status_message("No portfolios found.", "warning")
            return

        # Prepare table columns
        columns = [
            {"header": "ID", "style": "cyan"},
            {"header": "Name", "style": "green"},
            {"header": "Description"},
            {"header": "Tickers", "style": "magenta"},
            {"header": "Status"},
            {"header": "Date Added"},
        ]

        # Prepare table rows
        rows = []
        for portfolio in portfolios:
            ticker_count = len(
                cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio["id"])
            )

            rows.append(
                [
                    str(portfolio["id"]),
                    portfolio["name"],
                    portfolio["description"] or "",
                    str(ticker_count),
                    (
                        "[green]Active[/green]"
                        if portfolio["active"]
                        else "[red]Inactive[/red]"
                    ),
                    portfolio["date_added"].strftime("%Y-%m-%d"),
                ]
            )

        # Display the table
        table = ui.data_table("Your Portfolios", columns, rows)
        ui.console.print(table)
