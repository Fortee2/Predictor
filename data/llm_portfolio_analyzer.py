"""
LLM Integration Module for Portfolio Analysis

This module provides LLM-powered analysis of portfolio data using llama-index and AWS Bedrock.
It creates vector indices of portfolio data and enables natural language queries.
"""

import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional

import boto3
from duckduckgo_search import DDGS

from .bollinger_bands import BollingerBandAnalyzer
from .llm_tool_definitions import get_tool_config
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .trend_analyzer import TrendAnalyzer
from .utility import DatabaseConnectionPool

# Default Bedrock configuration
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_LLM_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

from .ai_recommendations_dao import AIRecommendationsDAO
from .conversation_history_dao import ConversationHistoryDAO
from .fundamental_data_dao import FundamentalDataDAO
from .macd import MACD
from .moving_averages import moving_averages
from .options_data import OptionsData
from .portfolio_dao import PortfolioDAO
from .portfolio_transactions_dao import PortfolioTransactionsDAO
from .rsi_calculations import rsi_calculations
from .shared_analysis_metrics import SharedAnalysisMetrics
from .stochastic_oscillator import StochasticOscillator
from .ticker_dao import TickerDao
from .watch_list_dao import WatchListDAO


class LLMPortfolioAnalyzer:
    """Main class for LLM-powered portfolio analysis."""

    def __init__(
        self,
        pool: DatabaseConnectionPool,
        aws_region: str = DEFAULT_AWS_REGION,
        model_name: str = DEFAULT_LLM_MODEL,
    ):
        """
        Initialize the LLM Portfolio Analyzer.

        Args:
            pool: Database connection pool
            aws_region: AWS region for Bedrock
            model_name: Name of the Bedrock model to use
        """
        self.db_pool = pool
        self.aws_region = aws_region
        self.model_name = model_name

        # Initialize DAOs
        self.portfolio_dao = PortfolioDAO(pool=self.db_pool)
        self.ticker_dao = TickerDao(pool=self.db_pool)
        self.transactions_dao = PortfolioTransactionsDAO(pool=self.db_pool)
        self.watchlist_dao = WatchListDAO(pool=self.db_pool)
        self.news_analyzer = NewsSentimentAnalyzer(pool=self.db_pool)
        self.fundamental_dao = FundamentalDataDAO(pool=self.db_pool)
        self.recommendations_dao = AIRecommendationsDAO(pool=self.db_pool)
        self.conversation_dao = ConversationHistoryDAO(pool=self.db_pool)

        # Initialize technical analysis tools
        self.rsi_calc = rsi_calculations(pool=self.db_pool)
        self.ma_calc = moving_averages(pool=self.db_pool)
        self.bb_calc = BollingerBandAnalyzer(self.ticker_dao)
        self.macd_calc = MACD(pool=self.db_pool)
        self.stoch_calc = StochasticOscillator(pool=self.db_pool)
        self.options_calc = OptionsData(pool=self.db_pool)
        self.trend_analyzer = TrendAnalyzer(pool=self.db_pool)
        self.shared_metrics = SharedAnalysisMetrics(
            self.rsi_calc, self.ma_calc, self.bb_calc, self.macd_calc,
            self.fundamental_dao, self.news_analyzer, self.options_calc,
            self.trend_analyzer, self.stoch_calc
        )
        # Initialize Bedrock client
        self.bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.aws_region
        )

        # Conversation history
        self.conversation_history = []
        self.current_session_id = None
        self.auto_save = True  # Automatically save conversation after each exchange

        # Logger
        self.logger = logging.getLogger(__name__)

    def _serialize_result(self, obj):
        """Recursively serialize result objects to JSON-compatible format."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_result(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_result(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._serialize_result(obj.__dict__)
        return obj

    def _format_tool_result(self, tool_use_id: str, tool_result: Dict) -> Dict:
        """
        Format tool execution results for Bedrock Converse API.

        Args:
            tool_use_id: The ID from the tool use request
            tool_result: Dictionary containing tool execution results

        Returns:
            Formatted tool result message
        """
        # Check if there was an error
        if "error" in tool_result:
            return {
                "toolUseId": tool_use_id,
                "content": [{"json": tool_result}],
                "status": "error"
            }

        # Convert any non-JSON-serializable types
        serialized_result = self._serialize_result(tool_result)

        return {
            "toolUseId": tool_use_id,
            "content": [{"json": serialized_result}]
        }

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Execute a tool call and return results.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Dictionary of input parameters

        Returns:
            Dictionary containing tool results or error information
        """
        try:
            # Portfolio Query Tools
            if tool_name == "get_portfolio_list":
                result = self.portfolio_dao.get_portfolio_list()
                return {"portfolios": result}

            elif tool_name == "get_portfolio_details":
                portfolio_id = tool_input["portfolio_id"]
                portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
                if portfolio:
                    cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                    positions = self.transactions_dao.get_current_positions(portfolio_id)
                    return {
                        "portfolio": portfolio,
                        "cash_balance": cash_balance,
                        "num_positions": len(positions)
                    }
                return {"error": f"Portfolio {portfolio_id} not found"}

            elif tool_name == "get_current_positions":
                portfolio_id = tool_input["portfolio_id"]
                positions = self.transactions_dao.get_current_positions(portfolio_id)
                # Enhance with current prices
                enhanced_positions = {}
                for ticker_id, position in positions.items():
                    ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                    if ticker_data:
                        position["current_price"] = ticker_data.get("last_price", 0)
                        position["current_value"] = position["shares"] * position["current_price"]
                    enhanced_positions[ticker_id] = position
                return {"positions": enhanced_positions}

            elif tool_name == "get_cash_balance":
                portfolio_id = tool_input["portfolio_id"]
                cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                return {"cash_balance": cash_balance}

            elif tool_name == "get_transaction_history":
                portfolio_id = tool_input["portfolio_id"]
                limit = tool_input.get("limit", 50)
                transactions = self.transactions_dao.get_transaction_history(portfolio_id)
                return {"transactions": transactions[:limit]}

            elif tool_name == "get_transaction_history_by_date":
                portfolio_id = tool_input["portfolio_id"]
                start_date_str = tool_input.get("start_date")
                end_date_str = tool_input.get("end_date")

                # Convert string dates to date objects if provided
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

                transactions = self.transactions_dao.get_transaction_history_by_date(
                    portfolio_id, start_date, end_date
                )
                return {"transactions": transactions}

            # Technical Analysis Tools
            elif tool_name == "calculate_rsi":
                ticker_id = tool_input["ticker_id"]
                # RSI is pre-calculated during data updates, just retrieve it
                rsi_data = self.rsi_calc.retrievePrices(1, ticker_id)
                if not rsi_data.empty and not rsi_data["rsi"].isna().all():
                    latest = rsi_data.iloc[-1]
                    rsi_value = float(latest["rsi"])
                    return {
                        "rsi_value": rsi_value,
                        "date": str(rsi_data.index[-1]),
                        "status": "Overbought" if rsi_value > 70 else "Oversold" if rsi_value < 30 else "Neutral"
                    }
                return {"error": "No RSI data available"}

            elif tool_name == "calculate_macd":
                ticker_id = tool_input["ticker_id"]
                # MACD is pre-calculated during data updates, just retrieve it
                macd_result = self.macd_calc.load_macd_from_db(ticker_id)
                if macd_result is not None and not macd_result.empty:
                    signals = self.macd_calc.get_macd_signals(ticker_id)
                    return {
                        "macd": macd_result,
                        "signals": signals
                    }
                return {"error": "No MACD data available"}

            elif tool_name == "get_comprehensive_analysis":
                ticker_id = tool_input["ticker_id"]
                symbol = tool_input.get("symbol")

                analysis = self.shared_metrics.get_comprehensive_analysis(
                    ticker_id=ticker_id,
                    symbol=symbol
                )
                return analysis

            elif tool_name == "get_ticker_data":
                ticker_id = tool_input["ticker_id"]
                ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                return {"ticker_data": ticker_data} if ticker_data else {"error": "Ticker data not found"}

            elif tool_name == "get_ticker_id_by_symbol":
                symbol = tool_input["symbol"]
                ticker_id = self.ticker_dao.get_ticker_id(symbol)
                return {"ticker_id": ticker_id} if ticker_id else {"error": f"Ticker {symbol} not found"}

            # News & Fundamental Tools
            elif tool_name == "web_search":
                query = tool_input["query"]
                try:
                    with DDGS() as ddgs:
                        # Perform search and get top 5 results
                        results = list(ddgs.text(query, max_results=5))
                        if results:
                            return {"search_results": results}
                        else:
                            return {"message": "No results found for your query."}
                except Exception as e:
                    return {"error": f"Search failed: {str(e)}"}

            elif tool_name == "get_news_sentiment":
                ticker_id = tool_input["ticker_id"]
                symbol = tool_input["symbol"]
                result = self.news_analyzer.fetch_and_analyze_news(ticker_id, symbol)
                return result if result else {"error": "No news data available"}

            elif tool_name == "get_fundamental_data":
                ticker_id = tool_input["ticker_id"]
                fund_data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                return {"fundamental_data": fund_data} if fund_data else {"error": "No fundamental data available"}

            # Write Operation Tools
            elif tool_name == "log_transaction":
                portfolio_id = tool_input["portfolio_id"]
                ticker_symbol = tool_input["ticker_symbol"]
                transaction_type = tool_input["transaction_type"]
                shares = tool_input["shares"]
                price = tool_input["price"]
                transaction_date = tool_input.get("transaction_date")

                success = self.portfolio_dao.log_transaction(
                    portfolio_id=portfolio_id,
                    ticker_symbol=ticker_symbol,
                    transaction_type=transaction_type,
                    shares=shares,
                    price=price,
                    transaction_date=transaction_date
                )
                return {"success": success}

            elif tool_name == "add_cash":
                portfolio_id = tool_input["portfolio_id"]
                amount = tool_input["amount"]
                success = self.portfolio_dao.add_cash(portfolio_id, amount)
                new_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                return {"success": success, "new_balance": new_balance}

            elif tool_name == "withdraw_cash":
                portfolio_id = tool_input["portfolio_id"]
                amount = tool_input["amount"]
                success = self.portfolio_dao.withdraw_cash(portfolio_id, amount)
                new_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
                return {"success": success, "new_balance": new_balance}

            # AI Recommendation Tools
            elif tool_name == "save_recommendation":
                portfolio_id = tool_input["portfolio_id"]
                ticker_symbol = tool_input["ticker_symbol"]
                recommendation_type = tool_input["recommendation_type"]
                recommended_quantity = tool_input.get("recommended_quantity")
                recommended_price = tool_input.get("recommended_price")
                confidence_score = tool_input.get("confidence_score")
                reasoning = tool_input["reasoning"]
                technical_indicators = tool_input.get("technical_indicators")
                sentiment_score = tool_input.get("sentiment_score")
                expires_days = tool_input.get("expires_days", 7)

                # Calculate expiration date
                expires_date = datetime.now() + timedelta(days=expires_days)

                rec_id = self.recommendations_dao.save_recommendation(
                    portfolio_id=portfolio_id,
                    ticker_symbol=ticker_symbol,
                    recommendation_type=recommendation_type,
                    recommended_quantity=recommended_quantity,
                    recommended_price=recommended_price,
                    confidence_score=confidence_score,
                    reasoning=reasoning,
                    technical_indicators=technical_indicators,
                    sentiment_score=sentiment_score,
                    expires_date=expires_date
                )

                if rec_id:
                    return {
                        "success": True,
                        "recommendation_id": rec_id,
                        "message": f"Recommendation saved successfully with ID {rec_id}. It will expire in {expires_days} days."
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to save recommendation. Check that the ticker symbol exists in the database."
                    }

            elif tool_name == "get_active_recommendations":
                portfolio_id = tool_input["portfolio_id"]
                recommendations = self.recommendations_dao.get_active_recommendations(portfolio_id)

                # Expire old recommendations while we're at it
                self.recommendations_dao.expire_old_recommendations(portfolio_id)

                return {
                    "active_recommendations": recommendations,
                    "count": len(recommendations)
                }

            # Watchlist Tools
            elif tool_name == "get_watchlists":
                watchlists = self.watchlist_dao.get_watch_list()
                return {"watchlists": watchlists}

            elif tool_name == "get_watchlist_tickers":
                watchlist_id = tool_input["watchlist_id"]
                tickers = self.watchlist_dao.get_tickers_in_watch_list(watchlist_id)
                return {"tickers": tickers}

            # Web Search Tools
            elif tool_name == "web_search":
                query = tool_input["query"]
                max_results = tool_input.get("max_results", 5)

                # Limit max_results to 10
                if max_results > 10:
                    max_results = 10

                try:
                    # Use DuckDuckGo search
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, max_results=max_results))

                    if results:
                        # Format results for better readability
                        formatted_results = []
                        for i, result in enumerate(results, 1):
                            formatted_results.append({
                                "position": i,
                                "title": result.get("title", ""),
                                "snippet": result.get("body", ""),
                                "url": result.get("href", "")
                            })

                        return {
                            "query": query,
                            "results_count": len(formatted_results),
                            "results": formatted_results
                        }
                    else:
                        return {
                            "query": query,
                            "results_count": 0,
                            "results": [],
                            "message": "No results found for this query"
                        }
                except Exception as search_error:
                    self.logger.error(f"DuckDuckGo search error: {search_error}")
                    return {
                        "error": f"Search failed: {str(search_error)}",
                        "query": query
                    }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}

    def _get_system_prompt(self, portfolio_id: Optional[int] = None) -> List[Dict]:
        """
        Get system prompt configuration for the LLM.

        Returns:
            System prompt configuration
        """
        base_prompt = """You are a professional financial advisor and portfolio analyst.
You have access to comprehensive portfolio data, technical analysis tools, fundamental metrics,
and news sentiment analysis.

IMPORTANT INSTRUCTIONS:
1. Always use the available tools to get accurate, up-to-date information
2. Provide specific, actionable insights backed by data
3. When analyzing portfolios, consider the 70/30 Core Strategy (use 'is_core_holding' field in position data to identify designated core positions):
   - Core positions (70%): Long-term holds (VTI, FSPSX, VEA, JNJ, BND, KO, quality dividend stocks)
     - Entry: Fundamental strength + reasonable valuation
     - Exit: Only on fundamental breakdown or major trend reversal
     - Technical analysis: Use for sizing (add on dips), NOT for selling

   - Swing positions (30%): Tactical opportunities (weeks to 6 months)
     - 3-6 positions at any time
     - Entry: Technical setup (oversold RSI, MACD buy, support bounce)
     - Exit: Technical signals (overbought, MACD sell, resistance)
     - Stop-losses: Always use, 5-8% max loss

4. When recommending trades, always consider:
   - Current cash balance
   - Position sizing
   - Risk management
   - Technical and fundamental signals

5. Format numbers clearly (use $ for dollars, % for percentages)
6. Explain your reasoning and cite specific data points
7. If you need more information, use additional tools
8. Handle errors gracefully and explain any data limitations

Available tool categories:
- Portfolio queries: Get portfolios, positions, balances, transactions
- Technical analysis: RSI, MACD, Moving Averages, Bollinger Bands, Stochastic, Trends
- Fundamental data: P/E ratios, market cap, dividend yields, growth metrics
- Web search: Find current information about stocks, market events, and economic data
- News sentiment: Recent news analysis with sentiment scores
- Write operations: Log transactions, manage cash, add/remove tickers
- Watchlists: Manage and analyze watchlist securities
- Web search: Search DuckDuckGo for current market news, earnings reports, company information, and financial topics
"""

        return [{"text": base_prompt}]

    def _extract_text_from_message(self, message: Dict) -> str:
        """Extract text content from assistant message."""
        text_parts = []
        for content_block in message.get("content", []):
            if "text" in content_block:
                text_parts.append(content_block["text"])
        return "\n".join(text_parts)

    def _validate_conversation_history(self, history: List[Dict]) -> List[Dict]:
        """
        Validate conversation history and remove incomplete tool exchanges.

        AWS Bedrock Converse API requires that every assistant message with tool_use blocks
        must be immediately followed by a user message with matching tool_result blocks.

        This method detects incomplete tool exchanges (e.g., when conversation was saved
        mid-execution) and truncates the history to maintain a valid state.

        Args:
            history: Raw conversation history

        Returns:
            Validated conversation history with incomplete exchanges removed
        """
        if not history:
            return history

        validated = []
        i = 0

        while i < len(history):
            message = history[i]

            # Add current message to validated list
            validated.append(message)

            # Check if this is an assistant message with tool_use
            if message.get("role") == "assistant":
                tool_use_blocks = []
                for content_block in message.get("content", []):
                    if "toolUse" in content_block:
                        tool_use_blocks.append(content_block["toolUse"]["toolUseId"])

                # If assistant requested tools, verify the next message has matching results
                if tool_use_blocks:
                    if i + 1 >= len(history):
                        # No next message - incomplete exchange, truncate here
                        self.logger.warning(
                            f"Incomplete tool exchange detected: assistant requested {len(tool_use_blocks)} "
                            f"tools but conversation ended. Truncating history."
                        )
                        validated.pop()  # Remove the incomplete assistant message
                        break

                    next_message = history[i + 1]

                    # Next message must be from user with tool results
                    if next_message.get("role") != "user":
                        self.logger.warning(
                            f"Invalid conversation structure: assistant tool_use not followed by user message. "
                            f"Truncating history at message {i}."
                        )
                        validated.pop()  # Remove the incomplete assistant message
                        break

                    # Count tool results in next message
                    tool_result_blocks = []
                    for content_block in next_message.get("content", []):
                        if "toolResult" in content_block:
                            tool_result_blocks.append(content_block["toolResult"]["toolUseId"])

                    # Verify counts match
                    if len(tool_result_blocks) != len(tool_use_blocks):
                        self.logger.warning(
                            f"Tool use/result mismatch: expected {len(tool_use_blocks)} results, "
                            f"found {len(tool_result_blocks)}. Truncating history at message {i}."
                        )
                        validated.pop()  # Remove the incomplete assistant message
                        break

                    # Verify all tool IDs match
                    if set(tool_result_blocks) != set(tool_use_blocks):
                        self.logger.warning(
                            f"Tool ID mismatch: tool results don't match tool requests. "
                            f"Truncating history at message {i}."
                        )
                        validated.pop()  # Remove the incomplete assistant message
                        break

            i += 1

        if len(validated) < len(history):
            self.logger.info(
                f"Conversation history validated: removed {len(history) - len(validated)} "
                f"incomplete messages (kept {len(validated)} valid messages)"
            )

        return validated

    def chat(
        self,
        user_message: str,
        portfolio_id: Optional[int] = None,
        max_turns: int = 10,
        reset_context: bool = True
    ) -> str:
        """
        Chat with the LLM using tool calling for portfolio analysis.

        Args:
            user_message: The user's question or request
            portfolio_id: Optional portfolio ID for context
            max_turns: Maximum number of conversation turns (prevents infinite loops)
            reset_context: If True, clears conversation history before this request.
                          This ensures consistent, context-free analysis for each query.
                          Set to False only when explicitly continuing a conversation.

        Returns:
            The assistant's final response as a string
        """
        try:
            # Clear history for consistent, context-free analysis
            if reset_context:
                self.reset_conversation()

            # Add portfolio context to user message if provided
            if portfolio_id is not None:
                portfolio = self.portfolio_dao.read_portfolio(portfolio_id)
                if portfolio:
                    context = f"\nContext: Analyzing portfolio '{portfolio['name']}' (ID: {portfolio_id})"
                    user_message = user_message + context

            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": [{"text": user_message}]
            })

            # Get tool configuration
            tool_config = get_tool_config()

            # Conversation loop
            turn_count = 0
            while turn_count < max_turns:
                turn_count += 1

                # Call Bedrock Converse API
                response = self.bedrock_client.converse(
                    modelId=self.model_name,
                    messages=self.conversation_history,
                    toolConfig=tool_config,
                    system=self._get_system_prompt(portfolio_id),
                    inferenceConfig={
                        "temperature": 0.0,  # Maximum determinism for consistent results
                        "maxTokens": 4096
                    }
                )

                # Extract response content
                output_message = response["output"]["message"]
                stop_reason = response["stopReason"]

                # Add assistant response to history
                self.conversation_history.append(output_message)

                # Check if we're done
                if stop_reason == "end_turn":
                    # Extract final text response
                    return self._extract_text_from_message(output_message)

                # Handle tool use
                elif stop_reason == "tool_use":
                    # Execute all requested tools
                    tool_results = []

                    for content_block in output_message["content"]:
                        if "toolUse" in content_block:
                            tool_use = content_block["toolUse"]
                            tool_name = tool_use["name"]
                            tool_input = tool_use["input"]
                            tool_use_id = tool_use["toolUseId"]

                            self.logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                            # Execute tool
                            result = self._execute_tool(tool_name, tool_input)

                            # Format result
                            formatted_result = self._format_tool_result(tool_use_id, result)
                            tool_results.append({"toolResult": formatted_result})

                    # Add tool results to conversation
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue conversation loop
                    continue

                else:
                    # Unexpected stop reason
                    self.logger.warning(f"Unexpected stop reason: {stop_reason}")
                    return "I encountered an unexpected situation. Please try again."

            # Max turns reached
            return "I apologize, but I couldn't complete your request within the maximum number of steps. Please try breaking your question into smaller parts."

        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return f"I encountered an error: {str(e)}"
        finally:
            # Auto-save conversation to database after each interaction
            # Only save if conversation is in a valid state (no incomplete tool exchanges)
            if self.auto_save and portfolio_id and len(self.conversation_history) > 0:
                try:
                    # Validate before saving to ensure we don't persist incomplete tool exchanges
                    validated_history = self._validate_conversation_history(self.conversation_history)
                    if len(validated_history) < len(self.conversation_history):
                        self.logger.warning(
                            "Skipping auto-save: conversation has incomplete tool exchanges. "
                            "Conversation will be saved once tool execution completes."
                        )
                        # Don't save incomplete state
                    else:
                        self.save_conversation_to_db(portfolio_id)
                except Exception as save_error:
                    self.logger.error(f"Error auto-saving conversation: {save_error}")

    def save_conversation_to_db(
        self,
        portfolio_id: int,
        session_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Save current conversation to database.

        Args:
            portfolio_id: Portfolio ID
            session_name: Optional name for the session

        Returns:
            Session ID if successful, None otherwise
        """
        if not self.conversation_history:
            self.logger.warning("No conversation history to save")
            return None

        session_id = self.conversation_dao.save_conversation(
            portfolio_id=portfolio_id,
            conversation_data=self.conversation_history,
            session_name=session_name,
            set_as_active=True
        )

        if session_id:
            self.current_session_id = session_id
            self.logger.info(f"Saved conversation to session {session_id}")

        return session_id

    def load_conversation_from_db(self, portfolio_id: int) -> bool:
        """
        Load the active conversation for a portfolio from database.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            True if conversation was loaded, False if no active session exists
        """
        session_data = self.conversation_dao.load_active_conversation(portfolio_id)

        if session_data:
            # Validate and clean conversation history
            raw_history = session_data['conversation_data']
            validated_history = self._validate_conversation_history(raw_history)

            # If validation removed messages, update the database
            if len(validated_history) < len(raw_history):
                self.logger.info(
                    f"Updating database with validated conversation history "
                    f"({len(validated_history)} messages instead of {len(raw_history)})"
                )
                self.conversation_dao.save_conversation(
                    portfolio_id=portfolio_id,
                    conversation_data=validated_history,
                    session_name=session_data.get('session_name'),
                    set_as_active=True
                )

            self.conversation_history = validated_history
            self.current_session_id = session_data['id']
            self.logger.info(
                f"Loaded conversation session {self.current_session_id} "
                f"with {len(validated_history)} messages"
            )
            return True
        else:
            self.logger.info(f"No active conversation found for portfolio {portfolio_id}")
            return False

    def reset_conversation(self):
        """Clear conversation history to start fresh."""
        self.conversation_history = []
        self.current_session_id = None
        self.logger.info("Conversation history cleared")

    def get_conversation_history(self) -> List[Dict]:
        """Get the current conversation history."""
        return self.conversation_history.copy()

    def set_conversation_history(self, history: List[Dict]):
        """
        Set conversation history (useful for continuing previous conversations).

        Args:
            history: Conversation history to set (will be validated)
        """
        validated_history = self._validate_conversation_history(history)
        self.conversation_history = validated_history

        if len(validated_history) < len(history):
            self.logger.warning(
                f"Conversation history contained incomplete tool exchanges. "
                f"Set {len(validated_history)} messages instead of {len(history)}"
            )
        else:
            self.logger.info(f"Conversation history set with {len(validated_history)} messages")

    def get_conversation_stats(self) -> Dict:
        """
        Get statistics about the current conversation.

        Returns:
            Dictionary with message count, exchange count, and session info
        """
        message_count = len(self.conversation_history)
        exchange_count = message_count // 2

        return {
            'message_count': message_count,
            'exchange_count': exchange_count,
            'session_id': self.current_session_id,
            'has_history': message_count > 0
        }

    def query_portfolio(self, portfolio_id: int, query: str, force_refresh: bool = False) -> str:
        """
        DEPRECATED: Use chat() method instead.

        Query a portfolio using natural language.
        This method now redirects to the new chat() interface.

        Args:
            portfolio_id: The portfolio ID to query
            query: Natural language query
            force_refresh: If True, clears conversation history (equivalent to fresh chat)

        Returns:
            AI-generated response
        """
        self.logger.warning("query_portfolio() is deprecated. Use chat() instead.")
        if force_refresh:
            self.reset_conversation()
        return self.chat(query, portfolio_id=portfolio_id)

    def get_weekly_recommendations(self, portfolio_id: int) -> str:
        """
        DEPRECATED: Use chat() with a specific prompt instead.

        Generate weekly recommendations for a portfolio.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            AI-generated weekly recommendations
        """
        self.logger.warning("get_weekly_recommendations() is deprecated. Use chat() instead.")

        weekly_prompt = """
        Based on the portfolio data, technical indicators, news sentiment, and recent market activity,
        please provide specific recommendations for the upcoming week. Include:

        1. Stocks to watch closely and why
        2. Any technical signals that suggest buying or selling opportunities
        3. Risk factors to monitor
        4. Potential market events or earnings that could affect holdings
        5. Portfolio rebalancing suggestions if any
        6. Specific price levels or indicators to watch

        Be actionable and specific with your recommendations.
        """

        self.reset_conversation()
        return self.chat(weekly_prompt, portfolio_id=portfolio_id)

    def analyze_portfolio_performance(self, portfolio_id: int) -> str:
        """
        DEPRECATED: Use chat() with a specific prompt instead.

        Analyze portfolio performance comprehensively.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            AI-generated performance analysis
        """
        self.logger.warning("analyze_portfolio_performance() is deprecated. Use chat() instead.")

        analysis_prompt = """
        Provide a comprehensive analysis of this portfolio's current performance including:

        1. Overall performance assessment with specific numbers
        2. Best and worst performing positions
        3. Risk assessment and diversification analysis
        4. Technical indicator summary and what they suggest
        5. Fundamental strength assessment
        6. News sentiment impact on holdings
        7. Recent transaction activity analysis
        8. Specific recommendations for improvement

        Use all available data to provide a thorough evaluation.
        """

        self.reset_conversation()
        return self.chat(analysis_prompt, portfolio_id=portfolio_id)
