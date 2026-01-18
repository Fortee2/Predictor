"""
AI Assistant Views for Portfolio Analysis

This module provides CLI interface for LLM-powered portfolio analysis.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from data.config import Config
from data.llm_portfolio_analyzer import LLMPortfolioAnalyzer
from data.utility import DatabaseConnectionPool


def register_ai_assistant_commands(command_registry):
    """
    Register AI assistant commands with the command registry.
    
    The primary interface is the AI Portfolio Assistant (ai_chat), which provides
    a continuous advisory session where you can ask for any type of analysis,
    recommendations, or risk assessment within a natural conversation.
    """

    @command_registry.register("ai_chat", "AI Portfolio Assistant", "analysis")
    def ai_chat_command(cli_instance, portfolio_id=None):
        """
        Interactive AI Portfolio Assistant - your continuous advisory session.
        
        Ask for:
        - Weekly recommendations
        - Portfolio analysis
        - Risk assessment
        - Technical analysis
        - Investment suggestions
        - Follow-up questions
        
        The AI maintains context throughout your session.
        """
        if not portfolio_id:
            portfolio_id = cli_instance.selected_portfolio

        if not portfolio_id:
            cli_instance.console.print("[red]Please select a portfolio first.[/red]")
            return

        ai_chat_interface(cli_instance.console, portfolio_id)

    @command_registry.register("ai_risk_assessment", "AI Risk Assessment", "analysis")
    def risk_assessment_command(cli_instance, portfolio_id=None):
        """Get AI-powered risk assessment (standalone report)."""
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
        )

        return analyzer

    except Exception as e:
        print(f"Error creating LLM analyzer: {e}")
        return None


def ai_chat_interface(console: Console, portfolio_id: int):
    """
    Interactive chat interface with the AI assistant.
    
    This maintains conversation context throughout the session, allowing the AI to:
    - Remember previous recommendations and track their outcomes
    - Understand why certain actions were suggested
    - Track which suggestions were followed and which weren't
    - Provide context-aware follow-up advice
    - Persist conversations between application restarts
    """

    analyzer = create_llm_analyzer()
    if not analyzer:
        console.print("[red]Error: Could not connect to AI assistant. Please check your configuration.[/red]")
        return

    # Check if there's a saved conversation to resume
    has_saved_session = False
    session_info = None
    
    with console.status("[bold green]Checking for saved conversations...[/bold green]"):
        try:
            # Try to load existing session
            has_saved_session = analyzer.load_conversation_from_db(portfolio_id)
            if has_saved_session:
                session_info = analyzer.get_conversation_stats()
        except Exception as e:
            console.print(f"[yellow]Note: Could not check for saved sessions: {e}[/yellow]")

    # Offer to resume or start fresh
    start_fresh = True
    if has_saved_session and session_info:
        console.print(
            Panel(
                f"[bold cyan]📝 Found Previous Conversation[/bold cyan]\n\n"
                f"Session ID: {session_info['session_id']}\n"
                f"Exchanges: {session_info['exchange_count']}\n"
                f"Messages: {session_info['message_count']}\n\n"
                f"Would you like to continue where you left off?",
                title="Resume Session?",
                border_style="cyan",
            )
        )
        
        resume_choice = Confirm.ask(
            "[bold]Resume previous conversation?[/bold]",
            default=True
        )
        
        if resume_choice:
            start_fresh = False
            console.print("[green]✅ Resuming previous conversation session[/green]\n")
        else:
            analyzer.reset_conversation()
            console.print("[yellow]🆕 Starting fresh conversation (previous session archived)[/yellow]\n")
    else:
        console.print("[cyan]🆕 Starting new conversation session[/cyan]\n")

    # Display welcome message
    console.print(
        Panel(
            "[bold green]🤖 AI Portfolio Assistant - Your Personal Advisor[/bold green]\n\n"
            "Welcome to your continuous portfolio advisory session!\n\n"
            "[bold cyan]Ask me anything:[/bold cyan]\n"
            "• 📈 Weekly recommendations - \"What should I buy this week?\"\n"
            "• 📊 Portfolio analysis - \"How is my portfolio performing?\"\n"
            "• ⚠️  Risk assessment - \"What are my portfolio risks?\"\n"
            "• 🎯 Technical analysis - \"Show me RSI for AAPL\"\n"
            "• 💡 Investment ideas - \"Which stocks look good?\"\n"
            "• 🤔 Follow-up questions - \"Why did you recommend that?\"\n\n"
            "[bold]Conversation persistence:[/bold]\n"
            "• 💾 Auto-saved after each exchange\n"
            "• 🔄 Resume where you left off next time\n"
            "• 📊 Track recommendations over time\n"
            "• 🧠 Remember context across sessions\n\n"
            "[cyan]Commands:[/cyan]\n"
            "  • 'clear' - Archive current & start fresh session\n"
            "  • 'history' - See conversation summary\n"
            "  • 'sessions' - List saved sessions\n"
            "  • 'name <name>' - Name current session\n"
            "[yellow]  • 'exit' - End session (auto-saved)[/yellow]",
            title="AI Portfolio Advisory Session",
            border_style="green",
        )
    )
    
    # Track session state
    first_query = start_fresh
    query_count = 0 if start_fresh else session_info.get('exchange_count', 0)

    try:
        while True:
            # Get user input
            user_question = Prompt.ask("\n[bold blue]Ask your question[/bold blue]", default="")

            if user_question.lower() in ["exit", "quit", "q"]:
                # Show session summary before exiting
                history = analyzer.get_conversation_history()
                console.print(f"\n[cyan]Advisory session ended. Total exchanges: {len(history) // 2}[/cyan]")
                break

            if not user_question.strip():
                continue

            # Handle special commands
            if user_question.lower() in ["clear", "reset", "new"]:
                if Confirm.ask("[yellow]Archive current session and start fresh? (Current session will be saved)[/yellow]"):
                    # Save current session before clearing
                    if len(analyzer.get_conversation_history()) > 0:
                        try:
                            analyzer.conversation_dao.deactivate_session(analyzer.current_session_id)
                            console.print("[cyan]📦 Current session archived[/cyan]")
                        except Exception as e:
                            console.print(f"[yellow]Note: Could not archive session: {e}[/yellow]")
                    
                    analyzer.reset_conversation()
                    first_query = True
                    query_count = 0
                    console.print("[green]✅ Started fresh advisory session.[/green]")
                continue
            
            if user_question.lower() in ["history", "context", "summary"]:
                stats = analyzer.get_conversation_stats()
                console.print(f"\n[cyan]Current advisory session:[/cyan]")
                console.print(f"  • Session ID: {stats['session_id'] or 'Not saved yet'}")
                console.print(f"  • Total exchanges: {stats['exchange_count']}")
                console.print(f"  • Conversation history: {stats['message_count']} messages")
                console.print(f"  • Auto-saved: {'Yes' if analyzer.auto_save else 'No'}")
                console.print(f"  • Session maintains full context of all recommendations and discussions")
                continue
            
            if user_question.lower() == "sessions":
                try:
                    sessions = analyzer.conversation_dao.list_sessions(portfolio_id, limit=10)
                    if sessions:
                        console.print(f"\n[cyan]Recent conversation sessions:[/cyan]")
                        for session in sessions:
                            active_marker = "✓ " if session['is_active'] else "  "
                            session_name = session['session_name'] or "Unnamed"
                            console.print(
                                f"{active_marker}ID {session['id']}: {session_name} "
                                f"({session['exchange_count']} exchanges, "
                                f"last: {session['last_accessed_at'].strftime('%Y-%m-%d %H:%M')})"
                            )
                    else:
                        console.print("[yellow]No saved sessions found[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error listing sessions: {e}[/red]")
                continue
            
            if user_question.lower().startswith("name "):
                session_name = user_question[5:].strip()
                if session_name and analyzer.current_session_id:
                    try:
                        success = analyzer.conversation_dao.set_session_name(
                            analyzer.current_session_id, 
                            session_name
                        )
                        if success:
                            console.print(f"[green]✅ Session renamed to: {session_name}[/green]")
                        else:
                            console.print("[red]Failed to rename session[/red]")
                    except Exception as e:
                        console.print(f"[red]Error renaming session: {e}[/red]")
                else:
                    console.print("[yellow]Usage: name <session_name>[/yellow]")
                continue

            # Increment query counter
            query_count += 1

            # Show thinking indicator
            if first_query:
                status_msg = "[bold green]🤖 Starting advisory session and analyzing your portfolio...[/bold green]"
            else:
                status_msg = f"[bold green]🤖 Continuing advisory session (query {query_count})...[/bold green]"

            with console.status(status_msg):
                try:
                    # Use chat() directly with reset_context=False to maintain conversation
                    # Only reset on first query to start fresh session
                    response = analyzer.chat(
                        user_question,
                        portfolio_id=portfolio_id,
                        reset_context=first_query  # True on first query, False after
                    )
                    first_query = False
                except Exception as e:
                    response = f"I encountered an error while analyzing your portfolio: {str(e)}"

            # Display response
            console.print("\n" + "=" * 80)
            console.print(
                Panel(
                    Markdown(response), 
                    title=f"🤖 AI Assistant Response (Query {query_count})", 
                    border_style="blue", 
                    padding=(1, 2)
                )
            )
            console.print("=" * 80 + "\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Advisory session interrupted.[/yellow]")
        # Auto-save on interrupt
        if len(analyzer.get_conversation_history()) > 0:
            try:
                with console.status("[bold green]💾 Saving conversation...[/bold green]"):
                    analyzer.save_conversation_to_db(portfolio_id)
                console.print("[green]✅ Conversation saved. Resume anytime![/green]")
            except Exception as e:
                console.print(f"[yellow]Note: Could not save conversation: {e}[/yellow]")
    finally:
        # Final save on exit
        if len(analyzer.get_conversation_history()) > 0:
            try:
                analyzer.save_conversation_to_db(portfolio_id)
            except Exception:
                pass  # Already logged in auto-save


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
    # Enter your default region (e.g., us-east-1)Are 

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
