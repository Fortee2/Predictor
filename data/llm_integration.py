"""
LLM Integration Module for Portfolio Analysis

This module provides LLM-powered analysis of portfolio data using llama-index and AWS Bedrock.
It creates vector indices of portfolio data and enables natural language queries.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

import boto3
import chromadb

from .bollinger_bands import BollingerBandAnalyzer
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .trend_analyzer import TrendAnalyzer
from .utility import DatabaseConnectionPool

# Default Bedrock configuration
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_LLM_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.vector_stores.chroma import ChromaVectorStore

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
        embed_model: str = DEFAULT_EMBED_MODEL,
    ):
        """
        Initialize the LLM Portfolio Analyzer.

        Args:
            pool: Database connection pool
            model_name: Name of the Bedrock model to use
            embed_model: Name of the Bedrock embedding model to use
        """
        self.db_pool = pool
        self.aws_region = aws_region
        self.model_name = model_name
        self.embed_model_name = embed_model

        # Initialize DAOs
        self.portfolio_dao = PortfolioDAO(pool=self.db_pool)
        self.ticker_dao = TickerDao(pool=self.db_pool)
        self.transactions_dao = PortfolioTransactionsDAO(pool=self.db_pool)
        self.watchlist_dao = WatchListDAO(pool=self.db_pool)
        self.news_analyzer = NewsSentimentAnalyzer(pool=self.db_pool)
        self.fundamental_dao = FundamentalDataDAO(pool=self.db_pool)

        # Initialize technical analysis tools
        self.rsi_calc = rsi_calculations(pool=self.db_pool)
        self.ma_calc = moving_averages(pool=self.db_pool)
        self.bb_calc = BollingerBandAnalyzer(self.ticker_dao)
        self.macd_calc = MACD(pool=self.db_pool)
        self.stoch_calc = StochasticOscillator(pool=self.db_pool)
        self.options_calc = OptionsData(pool=self.db_pool)
        self.trend_analyzer = TrendAnalyzer(pool=self.db_pool)

        # LLM and embedding configuration
        self.llm = None
        self.embed_model = None
        self.vector_indices = {}  # Store indices for different portfolios
        self.chroma_client = None

        # Logger
        self.logger = logging.getLogger(__name__)

        self._setup_llm()
        self._setup_vector_store()

    def _setup_llm(self):
        """Set up the LLM and embedding models using AWS Bedrock."""
        try:
            # Initialize AWS Bedrock client
            bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=self.aws_region)

            # Initialize Bedrock Converse LLM
            self.llm = BedrockConverse(
                model=self.model_name,
                client=bedrock_client,
                temperature=0.1,  # Lower temperature for more consistent financial analysis
                max_tokens=4096,
            )

            # Initialize Bedrock embedding model
            self.embed_model = BedrockEmbedding(model_name=self.embed_model_name, client=bedrock_client)

            # Configure llama-index settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)

            self.logger.info("LLM setup completed with Bedrock model: %s", self.model_name)
            self.logger.info("Embedding model: %s", self.embed_model_name)

        except Exception as e:
            self.logger.error("Error setting up Bedrock LLM: %s", e)
            raise

    def _setup_vector_store(self):
        """Set up ChromaDB vector store."""
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            self.logger.info("ChromaDB vector store initialized")

        except Exception as e:
            self.logger.error("Error setting up vector store: %s", e)
            raise

    def create_portfolio_documents(self, portfolio_id: int) -> List[Document]:
        """
        Create LlamaIndex documents from portfolio data.

        Args:
            portfolio_id: The portfolio ID to create documents for

        Returns:
            List of LlamaIndex Document objects
        """
        documents = []

        try:
            # Portfolio overview document
            portfolio_info = self.portfolio_dao.read_portfolio(portfolio_id)
            if portfolio_info:
                overview_text = self._create_portfolio_overview_text(portfolio_info, portfolio_id)
                documents.append(
                    Document(
                        text=overview_text,
                        metadata={
                            "document_type": "portfolio_overview",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            # Holdings and positions document
            holdings_text = self._create_holdings_text(portfolio_id)
            if holdings_text:
                documents.append(
                    Document(
                        text=holdings_text,
                        metadata={
                            "document_type": "holdings",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            # Technical analysis document
            technical_text = self._create_technical_analysis_text(portfolio_id)
            if technical_text:
                documents.append(
                    Document(
                        text=technical_text,
                        metadata={
                            "document_type": "technical_analysis",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            # Fundamental analysis document
            fundamental_text = self._create_fundamental_analysis_text(portfolio_id)
            if fundamental_text:
                documents.append(
                    Document(
                        text=fundamental_text,
                        metadata={
                            "document_type": "fundamental_analysis",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            # Recent transactions document
            transactions_text = self._create_transactions_text(portfolio_id)
            if transactions_text:
                documents.append(
                    Document(
                        text=transactions_text,
                        metadata={
                            "document_type": "recent_transactions",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            # Watchlist analysis document
            watchlist_text = self._create_watchlist_analysis_text()
            if watchlist_text:
                documents.append(
                    Document(
                        text=watchlist_text,
                        metadata={
                            "document_type": "watchlist_analysis",
                            "portfolio_id": portfolio_id,
                            "last_updated": datetime.now().isoformat(),
                        },
                    )
                )

            self.logger.info("Created %s documents for portfolio %s", len(documents), portfolio_id)
            return documents

        except Exception as e:
            self.logger.error("Error creating portfolio documents: %s", e)
            return []

    def _create_portfolio_overview_text(self, portfolio_info: Dict, portfolio_id: int) -> str:
        """Create portfolio overview text."""
        try:
            cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)

            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            active_tickers = [position["symbol"] for position in positions.values()]

            text = f"""
            Portfolio Overview: {portfolio_info["name"]}
            Description: {portfolio_info.get("description", "No description available")}
            Creation Date: {portfolio_info.get("date_added", "Unknown")}
            Current Cash Balance: ${cash_balance:.2f}
            Number of Active Holdings: {len(active_tickers)}
            Active Holdings: {", ".join(active_tickers) if active_tickers else "No active positions"}
            Status: {"Active" if portfolio_info.get("active", True) else "Inactive"}
            
            This portfolio contains {len(active_tickers)} active stock positions with a cash balance of ${cash_balance:.2f}.
            """
            return text.strip()

        except Exception as e:
            self.logger.error("Error creating portfolio overview text: %s", e)
            return ""

    def _create_holdings_text(self, portfolio_id: int) -> str:
        """Create holdings and positions text."""
        try:
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if not tickers:
                return ""

            holdings_info = []
            total_portfolio_value = 0

            # Get current positions using the existing method
            positions = self.transactions_dao.get_current_positions(portfolio_id)

            for ticker_id, position in positions.items():
                ticker_symbol = position["symbol"]
                shares = position["shares"]
                avg_price = position["avg_price"]

                # Get current price from ticker data
                ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                if ticker_data and ticker_data.get("last_price", 0) > 0:
                    current_price = ticker_data["last_price"]
                    current_value = shares * current_price
                    total_portfolio_value += current_value

                    unrealized_gain_loss = (current_price - avg_price) * shares
                    gain_loss_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                    holdings_info.append(
                        {
                            "ticker": ticker_symbol,
                            "shares": shares,
                            "avg_cost": avg_price,
                            "current_price": current_price,
                            "current_value": current_value,
                            "unrealized_gain_loss": unrealized_gain_loss,
                            "gain_loss_pct": gain_loss_pct,
                        }
                    )

            # Create text summary
            text_parts = ["Current Portfolio Holdings:\n"]

            for holding in holdings_info:
                gain_loss_indicator = (
                    "📈"
                    if holding["unrealized_gain_loss"] > 0
                    else "📉"
                    if holding["unrealized_gain_loss"] < 0
                    else "➡️"
                )
                text_parts.append(
                    f"""
                {holding["ticker"]}: 
                - Shares Owned: {holding["shares"]:.2f}
                - Average Cost Basis: ${holding["avg_cost"]:.2f}
                - Current Price: ${holding["current_price"]:.2f}  
                - Current Value: ${holding["current_value"]:.2f}
                - Unrealized Gain/Loss: ${holding["unrealized_gain_loss"]:.2f} ({holding["gain_loss_pct"]:.1f}%) {gain_loss_indicator}
                """
                )

            text_parts.append(f"\nTotal Portfolio Value: ${total_portfolio_value:.2f}")

            return "\n".join(text_parts)

        except Exception as e:
            self.logger.error("Error creating holdings text: %s", e)
            return ""

    def _create_technical_analysis_text(self, portfolio_id: int) -> str:
        """
        Create comprehensive technical analysis summary text for securities with active positions.

        Includes: RSI, Moving Averages (SMA/EMA), Bollinger Bands, MACD, Stochastic Oscillator

        Args:
            portfolio_id: The portfolio ID to analyze

        Returns:
            str: Formatted text containing all available technical indicators
                 for each security with active positions, or empty string if no positions exist
        """
        try:
            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            if not positions:
                return ""

            analysis_parts = ["Technical Analysis Summary (All Indicators):\n"]

            # Iterate through active positions only
            for ticker_id, position in positions.items():
                ticker = position["symbol"]
                ticker_analysis = []

                # Get current price first for context
                current_price = 0
                try:
                    ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                    current_price = ticker_data.get("last_price", 0) if ticker_data else 0
                    if current_price > 0:
                        ticker_analysis.append(f"Current Price: ${current_price:.2f}")
                except:
                    pass

                metrics = SharedAnalysisMetrics(
                    self.rsi_calc,
                    self.ma_calc,
                    self.bb_calc,
                    self.macd_calc,
                    self.fundamental_dao,
                    self.news_analyzer,
                    self.options_calc,
                    self.trend_analyzer,
                    stochastic_analyzer=self.stoch_calc,
                )

                analysis = metrics.get_comprehensive_analysis(
                    ticker_id=ticker_id,
                    symbol=ticker,
                    position_data=position,
                )

                # Format and display the analysis
                formatted_output = metrics.format_analysis_output(analysis, shares_info=position["shares"])

                # Add ticker analysis to main report if we have any indicators
                analysis_parts.append(f"\n{ticker}:")
                analysis_parts.append(f"  - {formatted_output}")

            tech_analysis = "\n".join(analysis_parts)
            print(tech_analysis)
            return tech_analysis

        except Exception as e:
            self.logger.error("Error creating technical analysis text: %s", e)
            return ""

    def _create_fundamental_analysis_text(self, portfolio_id: int) -> str:
        """
        Create fundamental analysis summary text for securities with active positions only.

        Args:
            portfolio_id: The portfolio ID to analyze

        Returns:
            str: Formatted text containing fundamental metrics (P/E ratio, market cap,
                 dividend yield, growth metrics) for each security with active positions,
                 or empty string if no positions exist
        """
        try:
            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            if not positions:
                return ""

            analysis_parts = ["Fundamental Analysis Summary:\n"]

            # Iterate through active positions only
            for ticker_id, position in positions.items():
                ticker = position["symbol"]
                try:
                    fund_data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                    if fund_data:
                        ticker_info = []

                        # Valuation metrics
                        if fund_data.get("pe_ratio"):
                            ticker_info.append(f"P/E Ratio: {fund_data['pe_ratio']:.2f}")
                        if fund_data.get("market_cap") is not None:
                            try:
                                market_cap_b = float(fund_data["market_cap"]) / 1e9
                                ticker_info.append(f"Market Cap: ${market_cap_b:.1f}B")
                            except (TypeError, ValueError):
                                pass
                        if fund_data.get("dividend_yield"):
                            ticker_info.append(f"Dividend Yield: {fund_data['dividend_yield']:.2f}%")

                        # Growth metrics
                        if fund_data.get("eps_growth"):
                            ticker_info.append(f"EPS Growth: {fund_data['eps_growth']:.1f}%")
                        if fund_data.get("revenue_growth"):
                            ticker_info.append(f"Revenue Growth: {fund_data['revenue_growth']:.1f}%")

                        if ticker_info:
                            analysis_parts.append(f"\n{ticker}:")
                            for info in ticker_info:
                                analysis_parts.append(f"  - {info}")

                except Exception:
                    continue

            return "\n".join(analysis_parts)

        except Exception as e:
            self.logger.error("Error creating fundamental analysis text: %s", e)
            return ""

    def _create_transactions_text(self, portfolio_id: int) -> str:
        """Create recent transactions summary text."""
        try:
            # Get transactions from last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            all_transactions = []

            # Use the transaction history method that exists
            all_transactions = self.transactions_dao.get_transaction_history(portfolio_id)

            # Filter to last 30 days and add ticker symbols
            filtered_transactions = []
            for trans in all_transactions:
                if "transaction_date" in trans and trans["transaction_date"]:
                    trans_date = trans["transaction_date"]
                    if isinstance(trans_date, str):
                        trans_date = datetime.strptime(trans_date, "%Y-%m-%d").date()
                    elif hasattr(trans_date, "date"):
                        trans_date = trans_date.date()

                    if trans_date >= start_date.date():
                        filtered_transactions.append(trans)

            all_transactions = filtered_transactions

            if not all_transactions:
                return "No recent transactions in the last 30 days."

            # Sort by date, most recent first
            all_transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)

            text_parts = ["Recent Transactions (Last 30 Days):\n"]

            for trans in all_transactions[:10]:  # Limit to 10 most recent
                date = trans.get("transaction_date", "Unknown")
                trans_type = trans.get("transaction_type", "unknown").title()
                ticker = trans.get("ticker", "Unknown")

                if trans_type in ["Buy", "Sell"]:
                    shares = trans.get("shares", 0)
                    price = trans.get("price", 0)
                    total = shares * price
                    text_parts.append(
                        f"  • {date}: {trans_type} {shares} shares of {ticker} @ ${price:.2f} (Total: ${total:.2f})"
                    )
                elif trans_type == "Dividend":
                    amount = trans.get("amount", 0)
                    text_parts.append(f"  • {date}: Dividend from {ticker}: ${amount:.2f}")

            return "\n".join(text_parts)

        except Exception as e:
            self.logger.error("Error creating transactions text: %s", e)
            return ""

    def _create_watchlist_analysis_text(self) -> str:
        """
        Create comprehensive watchlist analysis text with technical indicators.

        This provides analysis of securities on watchlists as potential candidates
        for adding to the portfolio.

        Returns:
            str: Formatted text containing technical and fundamental analysis
                 for each watchlist security, or empty string if no watchlists exist
        """
        try:
            # Get all watchlists
            watchlists = self.watchlist_dao.get_watch_list()
            if not watchlists:
                return ""

            analysis_parts = ["Watchlist Securities Analysis (Potential Portfolio Additions):\n"]
            analysis_parts.append("=" * 80)

            # Track which tickers we've already analyzed to avoid duplicates
            analyzed_tickers = set()

            for watchlist in watchlists:
                watchlist_id = watchlist["id"]
                watchlist_name = watchlist["name"]
                watchlist_desc = watchlist.get("description", "")

                # Get tickers in this watchlist
                tickers_in_watchlist = self.watchlist_dao.get_tickers_in_watch_list(watchlist_id)

                if not tickers_in_watchlist:
                    continue

                analysis_parts.append(f"\n📋 Watchlist: {watchlist_name}")
                if watchlist_desc:
                    analysis_parts.append(f"Description: {watchlist_desc}")
                analysis_parts.append("-" * 80)

                # Analyze each ticker in the watchlist
                for ticker_info in tickers_in_watchlist:
                    ticker_id = ticker_info["ticker_id"]
                    ticker_symbol = ticker_info["symbol"]
                    ticker_name = ticker_info.get("name", ticker_symbol)
                    notes = ticker_info.get("notes", "")

                    # Skip if we've already analyzed this ticker
                    if ticker_symbol in analyzed_tickers:
                        continue

                    analyzed_tickers.add(ticker_symbol)

                    analysis_parts.append(f"\n{ticker_symbol} ({ticker_name}):")
                    if notes:
                        analysis_parts.append(f"  Notes: {notes}")

                    # Initialize shared metrics analyzer
                    metrics = SharedAnalysisMetrics(
                        self.rsi_calc,
                        self.ma_calc,
                        self.bb_calc,
                        self.macd_calc,
                        self.fundamental_dao,
                        self.news_analyzer,
                        self.options_calc,
                        self.trend_analyzer,
                        stochastic_analyzer=self.stoch_calc,
                    )

                    # Get comprehensive analysis
                    analysis = metrics.get_comprehensive_analysis(
                        ticker_id=ticker_id,
                        symbol=ticker_symbol,
                        include_options=True,
                        include_stochastic=True,
                    )

                    # Extract key metrics for summary
                    ticker_summary = []

                    # Current price
                    try:
                        ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                        if ticker_data and ticker_data.get("last_price"):
                            current_price = ticker_data["last_price"]
                            ticker_summary.append(f"  Current Price: ${current_price:.2f}")
                    except:
                        pass

                    # RSI
                    if analysis.get("rsi", {}).get("success"):
                        rsi = analysis["rsi"]
                        ticker_summary.append(f"  RSI: {rsi['value']:.2f} ({rsi['status']})")

                    # Moving Average trend
                    if analysis.get("moving_average", {}).get("success"):
                        ma = analysis["moving_average"]
                        if ma.get("trend", {}).get("direction"):
                            trend_dir = ma["trend"]["direction"]
                            trend_str = ma["trend"]["strength"]
                            ticker_summary.append(f"  Trend: {trend_dir} ({trend_str})")

                    # MACD signal
                    if analysis.get("macd", {}).get("success"):
                        macd = analysis["macd"]
                        ticker_summary.append(f"  MACD Signal: {macd['current_signal']} ({macd['signal_strength']})")

                    # Fundamental metrics
                    if analysis.get("fundamental", {}).get("success"):
                        fund = analysis["fundamental"]["data"]
                        fund_items = []
                        if fund.get("pe_ratio"):
                            fund_items.append(f"P/E: {fund['pe_ratio']:.2f}")
                        if fund.get("market_cap") is not None:
                            try:
                                market_cap_b = float(fund["market_cap"]) / 1e9
                                fund_items.append(f"Market Cap: ${market_cap_b:.1f}B")
                            except (TypeError, ValueError):
                                pass
                        if fund.get("dividend_yield"):
                            fund_items.append(f"Div Yield: {fund['dividend_yield']:.2f}%")
                        if fund_items:
                            ticker_summary.append(f"  Fundamentals: {', '.join(fund_items)}")

                    # News sentiment
                    if analysis.get("news_sentiment", {}).get("success"):
                        news = analysis["news_sentiment"]
                        ticker_summary.append(
                            f"  News Sentiment: {news['status']} (Avg: {news['average_sentiment']:.2f})"
                        )

                    # Stochastic
                    if analysis.get("stochastic", {}).get("success"):
                        stoch = analysis["stochastic"]
                        ticker_summary.append(f"  Stochastic: {stoch['signal']} ({stoch['signal_strength']})")

                    # Options sentiment
                    if analysis.get("options", {}).get("success") and "put_call_ratio" in analysis["options"]:
                        options = analysis["options"]
                        ticker_summary.append(
                            f"  Options P/C Ratio: {options['put_call_ratio']:.2f} ({options['volume_sentiment']})"
                        )

                    # Add summary to analysis
                    if ticker_summary:
                        analysis_parts.extend(ticker_summary)
                    else:
                        analysis_parts.append("  Analysis data not available")

                    analysis_parts.append("")  # Empty line for spacing

            if len(analyzed_tickers) == 0:
                return ""

            analysis_parts.append("=" * 80)
            analysis_parts.append(f"\nTotal watchlist securities analyzed: {len(analyzed_tickers)}")
            analysis_parts.append("\nThese securities are being monitored as potential additions to the portfolio.")
            analysis_parts.append(
                "Consider their technical signals, fundamental metrics, and overall market conditions when making investment decisions."
            )

            return "\n".join(analysis_parts)

        except Exception as e:
            self.logger.error("Error creating watchlist analysis text: %s", e)
            return ""

    def build_portfolio_index(self, portfolio_id: int) -> VectorStoreIndex:
        """
        Build or update the vector index for a portfolio.

        Args:
            portfolio_id: The portfolio ID to build index for

        Returns:
            VectorStoreIndex for the portfolio
        """
        try:
            # Create collection name
            collection_name = f"portfolio_{portfolio_id}"

            # Get or create ChromaDB collection
            try:
                collection = self.chroma_client.get_collection(collection_name)
                # Delete existing collection to refresh data
                self.chroma_client.delete_collection(collection_name)
            except:
                pass  # Collection doesn't exist, which is fine

            collection = self.chroma_client.create_collection(collection_name)

            # Create vector store
            vector_store = ChromaVectorStore(chroma_collection=collection)

            # Create documents
            documents = self.create_portfolio_documents(portfolio_id)

            if not documents:
                self.logger.warning("No documents created for portfolio %s", portfolio_id)
                return None

            # Build index
            index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)

            # Cache the index
            self.vector_indices[portfolio_id] = index

            self.logger.info("Built vector index for portfolio %s with %s documents", portfolio_id, len(documents))
            return index

        except Exception as e:
            self.logger.error("Error building portfolio index: %s", e)
            return None

    def query_portfolio(self, portfolio_id: int, query: str) -> str:
        """
        Query a portfolio using natural language.

        Args:
            portfolio_id: The portfolio ID to query
            query: Natural language query

        Returns:
            AI-generated response
        """
        try:
            # Get or build index
            if portfolio_id not in self.vector_indices:
                index = self.build_portfolio_index(portfolio_id)
            else:
                index = self.vector_indices[portfolio_id]

            if not index:
                return "Sorry, I couldn't analyze your portfolio data at the moment."

            # Create query engine
            query_engine = index.as_query_engine(similarity_top_k=5, response_mode="tree_summarize")

            # Add context to the query
            enhanced_query = f"""
            You are a professional financial advisor analyzing a portfolio. 
            Please provide detailed, actionable insights based on the portfolio data.
            Consider technical indicators, fundamental metrics, sentiment analysis, and recent transactions.
            Be specific with numbers, dates, and recommendations.
            
            User Question: {query}
            """

            # Execute query
            response = query_engine.query(enhanced_query)

            return str(response)

        except Exception as e:
            self.logger.error("Error querying portfolio: %s", e)
            return f"Sorry, I encountered an error while analyzing your portfolio: {str(e)}"

    def get_weekly_recommendations(self, portfolio_id: int) -> str:
        """
        Generate weekly recommendations for a portfolio.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            AI-generated weekly recommendations
        """
        # Clear cached index to force rebuild with fresh data
        if portfolio_id in self.vector_indices:
            del self.vector_indices[portfolio_id]
            self.logger.info("Cleared cached index for portfolio %s", portfolio_id)

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

        return self.query_portfolio(portfolio_id, weekly_prompt)

    def analyze_portfolio_performance(self, portfolio_id: int) -> str:
        """
        Analyze portfolio performance comprehensively.

        Args:
            portfolio_id: The portfolio ID

        Returns:
            AI-generated performance analysis
        """
        # Clear cached index to force rebuild with fresh data
        if portfolio_id in self.vector_indices:
            del self.vector_indices[portfolio_id]
            self.logger.info("Cleared cached index for portfolio %s", portfolio_id)

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

        return self.query_portfolio(portfolio_id, analysis_prompt)
