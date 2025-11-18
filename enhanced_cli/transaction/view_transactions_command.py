"""Command to view transaction history."""

from rich.prompt import Prompt

from enhanced_cli.command import Command, error_handler
from enhanced_cli.ui_components import ui


class ViewTransactionsCommand(Command):
    """Command to view transaction history."""

    def __init__(self):
        super().__init__("View Transactions", "View transaction history")

    @error_handler("viewing transactions")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to view transaction history.

        Args:
            cli: The CLI instance
            portfolio_id: Optional portfolio ID
            ticker_symbol: Optional ticker symbol to filter transactions
        """
        from enhanced_cli.portfolio import ListPortfoliosCommand

        portfolio_id = kwargs.get("portfolio_id")
        ticker_symbol = kwargs.get("ticker_symbol")

        if portfolio_id is None:
            # Use selected portfolio if available
            if hasattr(cli, "selected_portfolio") and cli.selected_portfolio:
                portfolio_id = cli.selected_portfolio
            else:
                # First list portfolios for selection
                list_command = ListPortfoliosCommand()
                list_command.execute(cli)

                try:
                    portfolio_id = int(Prompt.ask("[bold]Enter Portfolio ID[/bold]"))
                except ValueError:
                    ui.status_message("Invalid portfolio ID", "error")
                    return

        # Ask if they want to filter by ticker
        if ticker_symbol is None and ui.confirm_action("Filter by ticker symbol?"):
            with ui.progress("Loading tickers...") as progress:
                progress.add_task("", total=None)
                tickers = cli.cli.portfolio_dao.get_tickers_in_portfolio(portfolio_id)

            ui.console.print("[bold]Available Tickers:[/bold]")
            for i, ticker in enumerate(tickers, 1):
                ui.console.print(f"[{i}] {ticker}")

            ticker_symbol = Prompt.ask(
                "[bold]Enter ticker symbol[/bold] (or leave empty for all)"
            ).upper()
            if ticker_symbol == "":
                ticker_symbol = None

        with ui.progress("Loading transactions...") as progress:
            progress.add_task("", total=None)
            portfolio = cli.cli.portfolio_dao.read_portfolio(portfolio_id)

            # Get transactions
            security_id = None
            if ticker_symbol:
                ticker_id = cli.cli.ticker_dao.get_ticker_id(ticker_symbol)
                if ticker_id:
                    security_id = cli.cli.portfolio_dao.get_security_id(
                        portfolio_id, ticker_id
                    )

            transactions = cli.cli.transactions_dao.get_transaction_history(
                portfolio_id, security_id
            )

        # Create header based on filter
        header_text = f"Transaction History for {portfolio['name']}"
        if ticker_symbol:
            header_text += f" - {ticker_symbol}"

        ui.console.print(ui.section_header(header_text))

        if not transactions:
            ui.status_message("No transactions found.", "warning")
            return

        # Prepare table columns
        columns = [
            {"header": "Date", "style": "cyan"},
            {"header": "Type", "style": "green"},
            {"header": "Symbol"},
            {"header": "Shares", "justify": "right"},
            {"header": "Price", "justify": "right"},
            {"header": "Amount", "justify": "right"},
            {"header": "Total", "justify": "right", "style": "bold"},
        ]

        # Prepare table rows
        rows = []
        for t in transactions:
            date = t["transaction_date"].strftime("%Y-%m-%d")
            type_str = t["transaction_type"].capitalize()
            symbol = t["symbol"] if "symbol" in t else "-"

            if t["transaction_type"] in ["buy", "sell"]:
                shares = f"{t['shares']:.2f}"
                price = f"${t['price']:.2f}"
                amount = "—"
                total = f"${t['shares'] * t['price']:.2f}"
            else:  # dividend or cash
                shares = "—"
                price = "—"
                amount = f"${t['amount']:.2f}" if t.get("amount") is not None else "—"
                total = amount

            rows.append([date, type_str, symbol, shares, price, amount, total])

        # Display the table
        table = ui.data_table("Transactions", columns, rows)
        ui.console.print(table)
