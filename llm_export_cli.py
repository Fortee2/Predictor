#!/usr/bin/env python3
"""
LLM Export CLI - Command line interface for LLM-friendly portfolio exports.

This script provides a command-line interface to the LLM export functionality
for use by the MCP server and other external tools.
"""

import argparse
import json
import sys

from enhanced_cli.llm_export_views import LLMAnalysisPromptCommand, PortfolioSnapshotCommand
from portfolio_cli import PortfolioCLI


class MockCLI:
    """Mock CLI object for command execution."""

    def __init__(self):
        self.cli = PortfolioCLI()


def portfolio_snapshot(portfolio_id: str, save_to_file: bool = False) -> None:
    """
    Generate a portfolio snapshot.

    Args:
        portfolio_id: Portfolio ID
        save_to_file: Whether to save to file
    """
    try:
        mock_cli = MockCLI()
        command = PortfolioSnapshotCommand()

        # Execute the command with the portfolio ID
        kwargs = {"portfolio_id": int(portfolio_id)}
        if save_to_file:
            kwargs["save_to_file"] = True

        # Capture the snapshot data by calling the internal method
        portfolio = mock_cli.cli.portfolio_dao.read_portfolio(int(portfolio_id))
        if not portfolio:
            print(json.dumps({"error": f"Portfolio with ID {portfolio_id} not found"}))
            return

        # Create a mock progress object
        class MockProgress:
            def add_task(self, description, total=None):
                return "task"

            def update(self, task, advance=0):
                pass

        progress = MockProgress()
        task = "mock_task"

        snapshot = command._generate_portfolio_snapshot(mock_cli, int(portfolio_id), portfolio, progress, task)

        if snapshot:
            print(json.dumps(snapshot, indent=2, default=command._json_serializer))
        else:
            print(json.dumps({"error": "Failed to generate portfolio snapshot"}))

    except Exception as e:
        print(json.dumps({"error": f"Error generating snapshot: {str(e)}"}))


def llm_analysis_prompt(portfolio_id: str, save_to_file: bool = False) -> None:
    """
    Generate an LLM analysis prompt.

    Args:
        portfolio_id: Portfolio ID
        save_to_file: Whether to save to file
    """
    try:
        mock_cli = MockCLI()
        command = LLMAnalysisPromptCommand()

        # Get portfolio info
        portfolio = mock_cli.cli.portfolio_dao.read_portfolio(int(portfolio_id))
        if not portfolio:
            print(f"Error: Portfolio with ID {portfolio_id} not found")
            return

        # Generate snapshot first
        snapshot_cmd = PortfolioSnapshotCommand()

        # Create a mock progress object
        class MockProgress:
            def add_task(self, description, total=None):
                return "task"

            def update(self, task, advance=0):
                pass

        progress = MockProgress()
        task = "mock_task"

        snapshot = snapshot_cmd._generate_portfolio_snapshot(mock_cli, int(portfolio_id), portfolio, progress, task)

        if not snapshot:
            print("Error: Failed to generate portfolio data")
            return

        # Generate analysis prompt
        prompt = command._generate_analysis_prompt(snapshot)
        print(prompt)

    except Exception as e:
        print(f"Error generating LLM prompt: {str(e)}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="LLM Export CLI for Portfolio Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Portfolio snapshot command
    snapshot_parser = subparsers.add_parser("portfolio_snapshot", help="Generate portfolio snapshot")
    snapshot_parser.add_argument("portfolio_id", help="Portfolio ID")
    snapshot_parser.add_argument("--save", action="store_true", help="Save to file")

    # LLM analysis prompt command
    prompt_parser = subparsers.add_parser("llm_analysis_prompt", help="Generate LLM analysis prompt")
    prompt_parser.add_argument("portfolio_id", help="Portfolio ID")
    prompt_parser.add_argument("--save", action="store_true", help="Save to file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "portfolio_snapshot":
        portfolio_snapshot(args.portfolio_id, args.save)
    elif args.command == "llm_analysis_prompt":
        llm_analysis_prompt(args.portfolio_id, args.save)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
