"""
AI Assistant Views for Portfolio Analysis

This module provides CLI interface for LLM-powered portfolio analysis.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from data.config import Config
from data.llm_integration import LLMPortfolioAnalyzer
from data.utility import DatabaseConnectionPool


def register_ai_assistant_commands(command_registry):
    """Register AI assistant commands with the command registry."""

    @command_registry.register("ai_chat", "AI Portfolio Assistant", "analysis")
    def ai_chat_command(cli_instance, portfolio_id=None):
        """Interactive chat with AI assistant."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        ai_chat_interface(cli_instance.console, portfolio_id)

    @command_registry.register("weekly_recommendations", "Weekly Portfolio Recommendations", "analysis")
    def weekly_recommendations_command(cli_instance, portfolio_id=None):
        """Get weekly recommendations for portfolio."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        get_weekly_recommendations(cli_instance.console, portfolio_id)

    @command_registry.register("portfolio_analysis", "Comprehensive Portfolio Analysis", "analysis")
    def portfolio_analysis_command(cli_instance, portfolio_id=None):
        """Get comprehensive portfolio analysis."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        analyze_portfolio_performance(cli_instance.console, portfolio_id)

    @command_registry.register("ai_risk_assessment", "AI Risk Assessment", "analysis")
    def risk_assessment_command(cli_instance, portfolio_id=None):
        """Get AI-powered risk assessment."""
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        get_risk_assessment(cli_instance.console, portfolio_id)


def create_llm_analyzer():
    """Create and configure the LLM analyzer."""
    try:
        config = Config()
        db_config = config.get_database_config()
        model_config = config.get_bedrock_config()

        # Create database connection pool
        db_pool = DatabaseConnectionPool(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            database=db_config["database"],
        )

        # Create analyzer with the connection pool
        analyzer = LLMPortfolioAnalyzer(
            pool=db_pool,
            aws_region=model_config["aws_region"],
            model_name=model_config["model"],
            embed_model=model_config["embed_model"],
        )

        return analyzer

    except Exception as e:
        print(f"Error creating LLM analyzer: {e}")
        return None


def ai_chat_interface(console: Console, portfolio_id: int):
    """Interactive chat interface with the AI assistant."""

    console.print(
        Panel(
            "[bold green]🤖 AI Portfolio Assistant[/bold green]\n\n"
            "Ask me anything about your portfolio! I can help with:\n"
            "• Portfolio performance analysis\n"
            "• Weekly recommendations\n"
            "• Risk assessment\n"
            "• Technical analysis interpretation\n"
            "• Investment suggestions\n\n"
            "[cyan]💡 Tip: Type 'refresh' to reload fresh portfolio data[/cyan]\n"
            "[yellow]Type 'exit' to return to main menu[/yellow]",
            title="Welcome to AI Assistant",
            border_style="green",
        )
    )

    analyzer = create_llm_analyzer()
    if not analyzer:
        console.print("[red]Error: Could not connect to AI assistant. Please check your configuration.[/red]")
        return

    # Track if this is the first query (always refresh on first query)
    first_query = True

    try:
        while True:
            # Get user input
            user_question = Prompt.ask("\n[bold blue]Ask your question[/bold blue]", default="")

            if user_question.lower() in ["exit", "quit", "q"]:
                break

            if not user_question.strip():
                continue

            # Check for refresh command
            if user_question.lower() in ["refresh", "reload", "update"]:
                console.print("[cyan]♻️  Refreshing portfolio data...[/cyan]")
                with console.status("[bold green]Reloading fresh data...[/bold green]"):
                    try:
                        # Force rebuild the index
                        analyzer.query_portfolio(portfolio_id, "Portfolio overview", force_refresh=True)
                        console.print("[green]✅ Portfolio data refreshed successfully![/green]")
                        first_query = False
                    except Exception as e:
                        console.print(f"[red]Error refreshing data: {str(e)}[/red]")
                continue

            # Show thinking indicator
            status_msg = (
                "[bold green]🤖 Loading fresh portfolio data and analyzing...[/bold green]"
                if first_query
                else "[bold green]🤖 Analyzing your portfolio...[/bold green]"
            )

            with console.status(status_msg):
                try:
                    # Always force refresh on first query to ensure fresh data
                    response = analyzer.query_portfolio(
                        portfolio_id, user_question, force_refresh=first_query
                    )
                    first_query = False
                except Exception as e:
                    response = f"I encountered an error while analyzing your portfolio: {str(e)}"

            # Display response
            console.print("\n" + "=" * 80)
            console.print(
                Panel(Markdown(response), title="🤖 AI Assistant Response", border_style="blue", padding=(1, 2))
            )
            console.print("=" * 80 + "\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Chat session ended.[/yellow]")


def get_weekly_recommendations(console: Console, portfolio_id: int):
    """Get and display weekly recommendations."""

    console.print(
        Panel(
            "[bold blue]📈 Weekly Portfolio Recommendations[/bold blue]\n"
            "Generating personalized recommendations based on your portfolio data...",
            title="AI Analysis",
            border_style="blue",
        )
    )

    analyzer = create_llm_analyzer()
    if not analyzer:
        console.print("[red]Error: Could not connect to AI assistant.[/red]")
        return

    try:
        with console.status("[bold green]🤖 Analyzing market conditions and portfolio data...[/bold green]"):
            recommendations = analyzer.get_weekly_recommendations(portfolio_id)

        console.print("\n" + "=" * 100)
        console.print(
            Panel(Markdown(recommendations), title="📈 Weekly Recommendations", border_style="green", padding=(1, 2))
        )
        console.print("=" * 100)

        # Ask if user wants to save recommendations
        if Confirm.ask("\n[bold]Would you like to save these recommendations to a file?[/bold]"):
            save_analysis_to_file(console, recommendations, f"weekly_recommendations_portfolio_{portfolio_id}")

    except Exception as e:
        console.print(f"[red]Error generating recommendations: {str(e)}[/red]")


def analyze_portfolio_performance(console: Console, portfolio_id: int):
    """Get and display comprehensive portfolio analysis."""

    console.print(
        Panel(
            "[bold blue]📊 Comprehensive Portfolio Analysis[/bold blue]\n"
            "Performing deep analysis of your portfolio performance...",
            title="AI Analysis",
            border_style="blue",
        )
    )

    analyzer = create_llm_analyzer()
    if not analyzer:
        console.print("[red]Error: Could not connect to AI assistant.[/red]")
        return

    try:
        with console.status("[bold green]🤖 Processing portfolio data and generating insights...[/bold green]"):
            analysis = analyzer.analyze_portfolio_performance(portfolio_id)

        console.print("\n" + "=" * 100)
        console.print(
            Panel(Markdown(analysis), title="📊 Portfolio Performance Analysis", border_style="cyan", padding=(1, 2))
        )
        console.print("=" * 100)

        # Ask if user wants to save analysis
        if Confirm.ask("\n[bold]Would you like to save this analysis to a file?[/bold]"):
            save_analysis_to_file(console, analysis, f"portfolio_analysis_portfolio_{portfolio_id}")

    except Exception as e:
        console.print(f"[red]Error generating analysis: {str(e)}[/red]")


def get_risk_assessment(console: Console, portfolio_id: int):
    """Get AI-powered risk assessment."""

    risk_prompt = """
    Please provide a comprehensive risk assessment of this portfolio including:

    1. **Overall Risk Level** - Assess the portfolio's risk on a scale of 1-10
    2. **Concentration Risk** - Analysis of sector/stock concentration
    3. **Volatility Assessment** - Based on technical indicators and price movements
    4. **Market Risk Exposure** - How vulnerable is this portfolio to market downturns
    5. **Specific Risk Factors** - Individual stocks or positions of concern
    6. **Risk Mitigation Suggestions** - Concrete steps to reduce portfolio risk
    7. **Diversification Recommendations** - How to improve portfolio balance

    Be specific with numbers and provide actionable recommendations.
    """

    console.print(
        Panel(
            "[bold red]⚠️  Portfolio Risk Assessment[/bold red]\n"
            "Analyzing portfolio risks and generating mitigation strategies...",
            title="Risk Analysis",
            border_style="red",
        )
    )

    analyzer = create_llm_analyzer()
    if not analyzer:
        console.print("[red]Error: Could not connect to AI assistant.[/red]")
        return

    try:
        with console.status("[bold green]🤖 Evaluating portfolio risks...[/bold green]"):
            risk_analysis = analyzer.query_portfolio(portfolio_id, risk_prompt)

        console.print("\n" + "=" * 100)
        console.print(
            Panel(Markdown(risk_analysis), title="⚠️ Risk Assessment Report", border_style="red", padding=(1, 2))
        )
        console.print("=" * 100)

        # Ask if user wants to save analysis
        if Confirm.ask("\n[bold]Would you like to save this risk assessment to a file?[/bold]"):
            save_analysis_to_file(console, risk_analysis, f"risk_assessment_portfolio_{portfolio_id}")

    except Exception as e:
        console.print(f"[red]Error generating risk assessment: {str(e)}[/red]")


def save_analysis_to_file(console: Console, content: str, filename_prefix: str):
    """Save analysis content to a file."""
    try:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Portfolio Analysis Report\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(content)

        console.print(f"[green]✅ Analysis saved to: {filename}[/green]")

    except Exception as e:
        console.print(f"[red]Error saving file: {str(e)}[/red]")


def check_bedrock_connection():
    """Check if AWS Bedrock credentials are configured."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        client = boto3.client("bedrock-runtime", region_name="us-east-1")
        # Try to list foundation models to verify connection
        client.list_foundation_models()
        return True
    except (NoCredentialsError, ClientError):
        return False
    except Exception:
        return False


def display_ai_setup_help(console: Console):
    """Display help for setting up AI assistant."""

    setup_text = """
    # 🤖 AI Assistant Setup Guide (AWS Bedrock)

    ## Prerequisites

    1. **AWS Account**: You need an active AWS account with Bedrock access
    2. **AWS CLI**: Install and configure AWS CLI with your credentials
    3. **Python packages**: Run `pip install -r requirements.txt`
    4. **Bedrock Model Access**: Request access to Claude and Titan models in AWS Console

    ## Configuration

    ### Option 1: AWS CLI (Recommended)
    ```bash
    aws configure
    # Enter your AWS Access Key ID
    # Enter your AWS Secret Access Key
    # Enter your default region (e.g., us-east-1)
    ```

    ### Option 2: Environment Variables
    Create a `.env` file in the project root:
    ```
    AWS_ACCESS_KEY_ID=your_access_key
    AWS_SECRET_ACCESS_KEY=your_secret_key
    AWS_REGION=us-east-1
    BEDROCK_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
    BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
    ```

    ## Enable Bedrock Models

    1. Go to AWS Console → Amazon Bedrock
    2. Navigate to "Model access" in the left sidebar
    3. Request access to:
       - **Anthropic Claude 3.5 Sonnet** (for AI analysis)
       - **Amazon Titan Embeddings** (for vector search)

    ## Verification

    Test your AWS credentials:
    ```bash
    aws bedrock list-foundation-models --region us-east-1
    ```

    ## Troubleshooting

    - **Credentials Error**: Run `aws configure` to set up credentials
    - **Access Denied**: Request model access in AWS Bedrock Console
    - **Region Error**: Ensure Bedrock is available in your region (us-east-1, us-west-2)
    - **Quota Exceeded**: Check your AWS Bedrock usage limits

    ## Available Models

    - `anthropic.claude-3-5-sonnet-20241022-v2:0` - Advanced analysis (recommended)
    - `anthropic.claude-3-haiku-20240307-v1:0` - Faster, lower cost
    - `amazon.titan-embed-text-v2:0` - Embedding model for search

    ## Cost Considerations

    AWS Bedrock charges per API call. Typical costs:
    - Claude 3.5 Sonnet: ~$3 per million input tokens
    - Titan Embeddings: ~$0.10 per million tokens

    Monitor your usage in AWS Cost Explorer.
    """

    console.print(
        Panel(Markdown(setup_text), title="🤖 AI Assistant Setup (AWS Bedrock)", border_style="yellow", padding=(1, 2))
    )
