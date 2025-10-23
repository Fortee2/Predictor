"""
LLM Integration Module for Portfolio Analysis

This module provides LLM-powered analysis of portfolio data using llama-index and Ollama.
It creates vector indices of portfolio data and enables natural language queries.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from data.portfolio_dao import PortfolioDAO
from data.ticker_dao import TickerDao
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.rsi_calculations import rsi_calculations
from data.moving_averages import MovingAverages
from data.bollinger_bands import BollingerBands
from data.news_sentiment_dao import NewsSentimentDAO
from data.fundamental_data_dao import FundamentalDataDAO


class LLMPortfolioAnalyzer:
    """Main class for LLM-powered portfolio analysis."""
    
    def __init__(self, db_user: str, db_password: str, db_host: str, db_name: str,
                 ollama_host: str = "http://localhost:11434",
                 model_name: str = "llama3.2:3b"):
        """
        Initialize the LLM Portfolio Analyzer.
        
        Args:
            db_user: Database username
            db_password: Database password  
            db_host: Database host
            db_name: Database name
            ollama_host: Ollama server URL
            model_name: Name of the Ollama model to use
        """
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.ollama_host = ollama_host
        self.model_name = model_name
        
        # Initialize DAOs
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.news_dao = NewsSentimentDAO(db_user, db_password, db_host, db_name)
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        
        # Initialize technical analysis tools
        self.rsi_calc = rsi_calculations(db_user, db_password, db_host, db_name)
        self.ma_calc = MovingAverages(db_user, db_password, db_host, db_name)
        self.bb_calc = BollingerBands(db_user, db_password, db_host, db_name)
        
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
        """Set up the LLM and embedding models."""
        try:
            # Initialize Ollama LLM
            self.llm = Ollama(
                model=self.model_name,
                base_url=self.ollama_host,
                temperature=0.1,  # Lower temperature for more consistent financial analysis
                request_timeout=120.0
            )
            
            # Initialize Ollama embedding model
            self.embed_model = OllamaEmbedding(
                model_name="nomic-embed-text",  # Good embedding model for text
                base_url=self.ollama_host,
                request_timeout=60.0
            )
            
            # Configure llama-index settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
            
            self.logger.info(f"LLM setup completed with model: {self.model_name}")
            
        except Exception as e:
            self.logger.error(f"Error setting up LLM: {e}")
            raise

    def _setup_vector_store(self):
        """Set up ChromaDB vector store."""
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            self.logger.info("ChromaDB vector store initialized")
            
        except Exception as e:
            self.logger.error(f"Error setting up vector store: {e}")
            raise

    def connect_to_database(self):
        """Connect to the database."""
        self.portfolio_dao.open_connection()
        self.ticker_dao.open_connection()
        self.transactions_dao.open_connection()
        self.news_dao.open_connection()
        self.fundamental_dao.open_connection()
        self.rsi_calc.open_connection()
        self.ma_calc.open_connection()
        self.bb_calc.open_connection()

    def disconnect_from_database(self):
        """Disconnect from the database."""
        self.portfolio_dao.close_connection()
        self.ticker_dao.close_connection()
        self.transactions_dao.close_connection()
        self.news_dao.close_connection()
        self.fundamental_dao.close_connection()
        self.rsi_calc.close_connection()
        self.ma_calc.close_connection()
        self.bb_calc.close_connection()

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
                documents.append(Document(
                    text=overview_text,
                    metadata={
                        "document_type": "portfolio_overview",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            # Holdings and positions document
            holdings_text = self._create_holdings_text(portfolio_id)
            if holdings_text:
                documents.append(Document(
                    text=holdings_text,
                    metadata={
                        "document_type": "holdings",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            # Technical analysis document
            technical_text = self._create_technical_analysis_text(portfolio_id)
            if technical_text:
                documents.append(Document(
                    text=technical_text,
                    metadata={
                        "document_type": "technical_analysis",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            # Fundamental analysis document
            fundamental_text = self._create_fundamental_analysis_text(portfolio_id)
            if fundamental_text:
                documents.append(Document(
                    text=fundamental_text,
                    metadata={
                        "document_type": "fundamental_analysis",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            # News sentiment document
            sentiment_text = self._create_sentiment_analysis_text(portfolio_id)
            if sentiment_text:
                documents.append(Document(
                    text=sentiment_text,
                    metadata={
                        "document_type": "sentiment_analysis",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            # Recent transactions document
            transactions_text = self._create_transactions_text(portfolio_id)
            if transactions_text:
                documents.append(Document(
                    text=transactions_text,
                    metadata={
                        "document_type": "recent_transactions",
                        "portfolio_id": portfolio_id,
                        "last_updated": datetime.now().isoformat()
                    }
                ))

            self.logger.info(f"Created {len(documents)} documents for portfolio {portfolio_id}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Error creating portfolio documents: {e}")
            return []

    def _create_portfolio_overview_text(self, portfolio_info: Dict, portfolio_id: int) -> str:
        """Create portfolio overview text."""
        try:
            cash_balance = self.portfolio_dao.get_cash_balance(portfolio_id)
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            
            text = f"""
            Portfolio Overview: {portfolio_info['name']}
            Description: {portfolio_info.get('description', 'No description available')}
            Creation Date: {portfolio_info.get('date_added', 'Unknown')}
            Current Cash Balance: ${cash_balance:.2f}
            Number of Holdings: {len(tickers)}
            Holdings: {', '.join(tickers)}
            Status: {'Active' if portfolio_info.get('active', True) else 'Inactive'}
            
            This portfolio contains {len(tickers)} different stock positions with a cash balance of ${cash_balance:.2f}.
            """
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Error creating portfolio overview text: {e}")
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
                ticker_symbol = position['symbol']
                shares = position['shares']
                avg_price = position['avg_price']
                
                # Get current price from ticker data
                ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                if ticker_data and ticker_data.get('last_price', 0) > 0:
                    current_price = ticker_data['last_price']
                    current_value = shares * current_price
                    total_portfolio_value += current_value
                    
                    unrealized_gain_loss = (current_price - avg_price) * shares
                    gain_loss_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                    
                    holdings_info.append({
                        'ticker': ticker_symbol,
                        'shares': shares,
                        'avg_cost': avg_price,
                        'current_price': current_price,
                        'current_value': current_value,
                        'unrealized_gain_loss': unrealized_gain_loss,
                        'gain_loss_pct': gain_loss_pct
                    })

            # Create text summary
            text_parts = ["Current Portfolio Holdings:\n"]
            
            for holding in holdings_info:
                gain_loss_indicator = "📈" if holding['unrealized_gain_loss'] > 0 else "📉" if holding['unrealized_gain_loss'] < 0 else "➡️"
                text_parts.append(f"""
                {holding['ticker']}: 
                - Shares Owned: {holding['shares']:.2f}
                - Average Cost Basis: ${holding['avg_cost']:.2f}
                - Current Price: ${holding['current_price']:.2f}  
                - Current Value: ${holding['current_value']:.2f}
                - Unrealized Gain/Loss: ${holding['unrealized_gain_loss']:.2f} ({holding['gain_loss_pct']:.1f}%) {gain_loss_indicator}
                """)
            
            text_parts.append(f"\nTotal Portfolio Value: ${total_portfolio_value:.2f}")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating holdings text: {e}")
            return ""

    def _create_technical_analysis_text(self, portfolio_id: int) -> str:
        """Create technical analysis summary text."""
        try:
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if not tickers:
                return ""
                
            analysis_parts = ["Technical Analysis Summary:\n"]
            
            for ticker in tickers:
                ticker_analysis = []
                
                # Get ticker ID first
                ticker_id = self.ticker_dao.get_ticker_id(ticker)
                if not ticker_id:
                    continue
                    
                # RSI Analysis
                try:
                    rsi_data = self.ticker_dao.retrieve_last_rsi(ticker_id)
                    if not rsi_data.empty:
                        latest_rsi = float(rsi_data.iloc[0]['rsi'])
                        if latest_rsi > 70:
                            rsi_signal = "Overbought (Consider selling)"
                        elif latest_rsi < 30:
                            rsi_signal = "Oversold (Consider buying)"
                        else:
                            rsi_signal = "Neutral"
                        ticker_analysis.append(f"RSI: {latest_rsi:.1f} - {rsi_signal}")
                except:
                    pass
                
                # Get current price for technical analysis
                try:
                    ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                    current_price = ticker_data.get('last_price', 0) if ticker_data else 0
                    
                    if current_price > 0:
                        ticker_analysis.append(f"Current Price: ${current_price:.2f}")
                except:
                    pass
                
                if ticker_analysis:
                    analysis_parts.append(f"\n{ticker}:")
                    for analysis in ticker_analysis:
                        analysis_parts.append(f"  - {analysis}")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating technical analysis text: {e}")
            return ""

    def _create_fundamental_analysis_text(self, portfolio_id: int) -> str:
        """Create fundamental analysis summary text."""
        try:
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if not tickers:
                return ""
                
            analysis_parts = ["Fundamental Analysis Summary:\n"]
            
            for ticker in tickers:
                try:
                    # Get ticker ID first
                    ticker_id = self.ticker_dao.get_ticker_id(ticker)
                    if ticker_id:
                        fund_data = self.fundamental_dao.get_latest_fundamental_data(ticker_id)
                        if fund_data:
                            ticker_info = []
                            
                            # Valuation metrics
                            if fund_data.get('pe_ratio'):
                                ticker_info.append(f"P/E Ratio: {fund_data['pe_ratio']:.2f}")
                            if fund_data.get('market_cap'):
                                market_cap_b = fund_data['market_cap'] / 1e9
                                ticker_info.append(f"Market Cap: ${market_cap_b:.1f}B")
                            if fund_data.get('dividend_yield'):
                                ticker_info.append(f"Dividend Yield: {fund_data['dividend_yield']:.2f}%")
                            
                            # Growth metrics
                            if fund_data.get('eps_growth'):
                                ticker_info.append(f"EPS Growth: {fund_data['eps_growth']:.1f}%")
                            if fund_data.get('revenue_growth'):
                                ticker_info.append(f"Revenue Growth: {fund_data['revenue_growth']:.1f}%")
                                
                            if ticker_info:
                                analysis_parts.append(f"\n{ticker}:")
                                for info in ticker_info:
                                    analysis_parts.append(f"  - {info}")
                                
                except Exception:
                    continue
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating fundamental analysis text: {e}")
            return ""

    def _create_sentiment_analysis_text(self, portfolio_id: int) -> str:
        """Create news sentiment analysis text."""
        try:
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if not tickers:
                return ""
                
            analysis_parts = ["News Sentiment Analysis (Last 7 Days):\n"]
            
            for ticker in tickers:
                try:
                    # Get ticker ID first
                    ticker_id = self.ticker_dao.get_ticker_id(ticker)
                    if ticker_id:
                        # Get recent sentiment data
                        sentiment_data = self.news_dao.get_latest_sentiment(ticker_id, limit=5)
                        if sentiment_data:
                            avg_sentiment = sum(s.get('sentiment_score', 0) for s in sentiment_data) / len(sentiment_data)
                            
                            if avg_sentiment > 0.1:
                                sentiment_label = "Positive"
                                sentiment_emoji = "📈"
                            elif avg_sentiment < -0.1:
                                sentiment_label = "Negative" 
                                sentiment_emoji = "📉"
                            else:
                                sentiment_label = "Neutral"
                                sentiment_emoji = "➡️"
                                
                            analysis_parts.append(f"\n{ticker}: {sentiment_label} {sentiment_emoji}")
                            analysis_parts.append(f"  - Average Sentiment Score: {avg_sentiment:.3f}")
                            analysis_parts.append(f"  - Based on {len(sentiment_data)} recent articles")
                            
                            # Recent headlines
                            recent_headlines = sentiment_data[:3]  # Top 3 recent
                            if recent_headlines:
                                analysis_parts.append("  - Recent Headlines:")
                                for headline_data in recent_headlines:
                                    headline = headline_data.get('headline', '')[:100]
                                    analysis_parts.append(f"    • {headline}...")
                                    
                except Exception:
                    continue
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating sentiment analysis text: {e}")
            return ""

    def _create_transactions_text(self, portfolio_id: int) -> str:
        """Create recent transactions summary text."""
        try:
            # Get transactions from last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            all_transactions = []
            
            # Use the transaction history method that exists
            all_transactions = self.transactions_dao.get_transaction_history(portfolio_id)
            
            # Filter to last 30 days and add ticker symbols
            filtered_transactions = []
            for trans in all_transactions:
                if 'transaction_date' in trans and trans['transaction_date']:
                    trans_date = trans['transaction_date']
                    if isinstance(trans_date, str):
                        from datetime import datetime
                        trans_date = datetime.strptime(trans_date, '%Y-%m-%d').date()
                    elif hasattr(trans_date, 'date'):
                        trans_date = trans_date.date()
                    
                    if trans_date >= start_date.date():
                        filtered_transactions.append(trans)
            
            all_transactions = filtered_transactions
            
            if not all_transactions:
                return "No recent transactions in the last 30 days."
                
            # Sort by date, most recent first
            all_transactions.sort(key=lambda x: x.get('transaction_date', ''), reverse=True)
            
            text_parts = ["Recent Transactions (Last 30 Days):\n"]
            
            for trans in all_transactions[:10]:  # Limit to 10 most recent
                date = trans.get('transaction_date', 'Unknown')
                trans_type = trans.get('transaction_type', 'unknown').title()
                ticker = trans.get('ticker', 'Unknown')
                
                if trans_type in ['Buy', 'Sell']:
                    shares = trans.get('shares', 0)
                    price = trans.get('price', 0)
                    total = shares * price
                    text_parts.append(f"  • {date}: {trans_type} {shares} shares of {ticker} @ ${price:.2f} (Total: ${total:.2f})")
                elif trans_type == 'Dividend':
                    amount = trans.get('amount', 0)
                    text_parts.append(f"  • {date}: Dividend from {ticker}: ${amount:.2f}")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating transactions text: {e}")
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
                self.logger.warning(f"No documents created for portfolio {portfolio_id}")
                return None
            
            # Build index
            index = VectorStoreIndex.from_documents(
                documents,
                vector_store=vector_store
            )
            
            # Cache the index
            self.vector_indices[portfolio_id] = index
            
            self.logger.info(f"Built vector index for portfolio {portfolio_id} with {len(documents)} documents")
            return index
            
        except Exception as e:
            self.logger.error(f"Error building portfolio index: {e}")
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
            query_engine = index.as_query_engine(
                similarity_top_k=5,
                response_mode="tree_summarize"
            )
            
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
            self.logger.error(f"Error querying portfolio: {e}")
            return f"Sorry, I encountered an error while analyzing your portfolio: {str(e)}"

    def get_weekly_recommendations(self, portfolio_id: int) -> str:
        """
        Generate weekly recommendations for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            AI-generated weekly recommendations
        """
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
