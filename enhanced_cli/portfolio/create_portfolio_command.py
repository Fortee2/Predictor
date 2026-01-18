"""Command to create a new portfolio."""

from enhanced_cli.core.command import Command, error_handler
from enhanced_cli.ui_components import ui


class CreatePortfolioCommand(Command):
    """Command to create a new portfolio."""

    def __init__(self):
        super().__init__("Create Portfolio", "Create a new portfolio")

    @error_handler("creating portfolio")
    def execute(self, cli, *args, **kwargs) -> None:
        """
        Execute the command to create a new portfolio.

        Args:
            cli: The CLI instance
        """
        # Import here to avoid circular dependency
        from enhanced_cli.portfolio.add_tickers_command import AddTickersCommand

        # Display form header
        ui.console.print(ui.section_header("Create a New Portfolio"))

        # Define form fields
        fields = [
            {"name": "name", "prompt": "[bold]Portfolio Name[/bold]"},
            {"name": "description", "prompt": "[bold]Description[/bold] (optional)"},
            {
                "name": "initial_cash",
                "prompt": "[bold]Initial Cash Balance ($)[/bold]",
                "type": float,
                "default": "0.00",
            },
        ]

        # Get form data
        data = ui.input_form(fields)

        # Confirm
        if ui.confirm_action(
            f"Create portfolio [bold]{data['name']}[/bold] with description: [italic]{data['description']}[/italic] and ${data['initial_cash']:.2f} cash?"
        ):
            with ui.progress("Creating portfolio...") as progress:
                progress.add_task("", total=None)
                portfolio_id = cli.cli.portfolio_dao.create_portfolio(
                    data["name"], data["description"], data["initial_cash"]
                )

            if portfolio_id:
                ui.status_message(f"Portfolio created successfully with ID: {portfolio_id}", "success")

                # Ask if user wants to add tickers
                if ui.confirm_action("Would you like to add tickers to this portfolio now?"):
                    add_tickers_command = AddTickersCommand()
                    add_tickers_command.execute(cli, portfolio_id=portfolio_id)
            else:
                ui.status_message("Failed to create portfolio", "error")
