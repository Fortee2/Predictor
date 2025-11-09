"""
LLM Integration Module for Portfolio Analysis

This module provides LLM-powered analysis of portfolio data using llama-index and AWS Bedrock.
It creates vector indices of portfolio data and enables natural language queries.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Default Bedrock configuration
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_LLM_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
import boto3

from data.portfolio_dao import PortfolioDAO
from data.ticker_dao import TickerDao
from data.portfolio_transactions_dao import PortfolioTransactionsDAO
from data.rsi_calculations import rsi_calculations
from data.moving_averages import moving_averages
from data.bollinger_bands import BollingerBandAnalyzer
from data.macd import MACD
from data.stochastic_oscillator import StochasticOscillator
from data.options_data import OptionsData
from data.news_sentiment_dao import NewsSentimentDAO
from data.fundamental_data_dao import FundamentalDataDAO


class LLMPortfolioAnalyzer:
    """Main class for LLM-powered portfolio analysis."""
    
    def __init__(self, db_user: str, db_password: str, db_host: str, db_name: str,
                 aws_region: str = DEFAULT_AWS_REGION,
                 model_name: str = DEFAULT_LLM_MODEL,
                 embed_model: str = DEFAULT_EMBED_MODEL):
        """
        Initialize the LLM Portfolio Analyzer.
        
        Args:
            db_user: Database username
            db_password: Database password  
            db_host: Database host
            db_name: Database name
            aws_region: AWS region for Bedrock
            model_name: Name of the Bedrock model to use
            embed_model: Name of the Bedrock embedding model to use
        """
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_name = db_name
        self.aws_region = aws_region
        self.model_name = model_name
        self.embed_model_name = embed_model
        
        # Initialize DAOs
        self.portfolio_dao = PortfolioDAO(db_user, db_password, db_host, db_name)
        self.ticker_dao = TickerDao(db_user, db_password, db_host, db_name)
        self.transactions_dao = PortfolioTransactionsDAO(db_user, db_password, db_host, db_name)
        self.news_dao = NewsSentimentDAO(db_user, db_password, db_host, db_name)
        self.fundamental_dao = FundamentalDataDAO(db_user, db_password, db_host, db_name)
        
        # Initialize technical analysis tools
        self.rsi_calc = rsi_calculations(db_user, db_password, db_host, db_name)
        self.ma_calc = moving_averages(db_user, db_password, db_host, db_name)
        self.bb_calc = BollingerBandAnalyzer(self.ticker_dao)
        self.macd_calc = MACD(db_user, db_password, db_host, db_name)
        self.stoch_calc = StochasticOscillator(db_user, db_password, db_host, db_name)
        self.options_calc = OptionsData(db_user, db_password, db_host, db_name)
        
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
            bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.aws_region
            )
            
            # Initialize Bedrock Converse LLM
            self.llm = BedrockConverse(
                model=self.model_name,
                client=bedrock_client,
                temperature=0.1,  # Lower temperature for more consistent financial analysis
                max_tokens=4096
            )
            
            # Initialize Bedrock embedding model
            self.embed_model = BedrockEmbedding(
                model_name=self.embed_model_name,
                client=bedrock_client
            )
            
            # Configure llama-index settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            Settings.node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
            
            self.logger.info(f"LLM setup completed with Bedrock model: {self.model_name}")
            self.logger.info(f"Embedding model: {self.embed_model_name}")
            
        except Exception as e:
            self.logger.error(f"Error setting up Bedrock LLM: {e}")
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
        """
        Connect to the database.
        Note: Individual components will open connections as needed to avoid pool exhaustion.
        """
        # Open connections for frequently used DAOs only
        self.portfolio_dao.open_connection()
        self.ticker_dao.open_connection()
        self.transactions_dao.open_connection()
        # Other components will open connections on-demand

    def disconnect_from_database(self):
        """Disconnect from the database."""
        # Close any open connections
        try:
            self.portfolio_dao.close_connection()
        except:
            pass
        try:
            self.ticker_dao.close_connection()
        except:
            pass
        try:
            self.transactions_dao.close_connection()
        except:
            pass
        try:
            self.news_dao.close_connection()
        except:
            pass
        try:
            self.fundamental_dao.close_connection()
        except:
            pass
        try:
            self.rsi_calc.close_connection()
        except:
            pass
        try:
            self.ma_calc.close_connection()
        except:
            pass
        try:
            self.macd_calc.close_connection()
        except:
            pass
        try:
            self.stoch_calc.close_connection()
        except:
            pass
        try:
            self.options_calc.close_connection()
        except:
            pass

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

            # Options analysis document
            options_text = self._create_options_analysis_text(portfolio_id)
            if options_text:
                documents.append(Document(
                    text=options_text,
                    metadata={
                        "document_type": "options_analysis",
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
            
            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            active_tickers = [position['symbol'] for position in positions.values()]
            
            text = f"""
            Portfolio Overview: {portfolio_info['name']}
            Description: {portfolio_info.get('description', 'No description available')}
            Creation Date: {portfolio_info.get('date_added', 'Unknown')}
            Current Cash Balance: ${cash_balance:.2f}
            Number of Active Holdings: {len(active_tickers)}
            Active Holdings: {', '.join(active_tickers) if active_tickers else 'No active positions'}
            Status: {'Active' if portfolio_info.get('active', True) else 'Inactive'}
            
            This portfolio contains {len(active_tickers)} active stock positions with a cash balance of ${cash_balance:.2f}.
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
                ticker = position['symbol']
                ticker_analysis = []
                
                # Get current price first for context
                current_price = 0
                try:
                    ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                    current_price = ticker_data.get('last_price', 0) if ticker_data else 0
                    if current_price > 0:
                        ticker_analysis.append(f"Current Price: ${current_price:.2f}")
                except:
                    pass
                
                # 1. RSI Analysis
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
                        ticker_analysis.append(f"RSI (14): {latest_rsi:.1f} - {rsi_signal}")
                except Exception as e:
                    self.logger.debug(f"RSI calculation failed for {ticker}: {e}")
                
                # 2. Moving Averages Analysis
                try:
                    ma_data = self.ticker_dao.retrieve_last_moving_avg(ticker_id, '50SMA')
                    if not ma_data.empty and current_price > 0:
                        sma_50 = float(ma_data.iloc[0]['value'])
                        ma_position = "above" if current_price > sma_50 else "below"
                        ma_signal = "Bullish" if current_price > sma_50 else "Bearish"
                        ticker_analysis.append(f"50-Day SMA: ${sma_50:.2f} (Price {ma_position} - {ma_signal})")
                    
                    ma_data_200 = self.ticker_dao.retrieve_last_moving_avg(ticker_id, '200SMA')
                    if not ma_data_200.empty and current_price > 0:
                        sma_200 = float(ma_data_200.iloc[0]['value'])
                        ma_position = "above" if current_price > sma_200 else "below"
                        ma_signal = "Bullish" if current_price > sma_200 else "Bearish"
                        ticker_analysis.append(f"200-Day SMA: ${sma_200:.2f} (Price {ma_position} - {ma_signal})")
                except Exception as e:
                    self.logger.debug(f"Moving average calculation failed for {ticker}: {e}")
                
                # 3. Bollinger Bands Analysis
                try:
                    bb_data = self.bb_calc.calculate_bollinger_bands(ticker_id)
                    if bb_data is not None and not bb_data.empty and current_price > 0:
                        latest_bb = bb_data.iloc[-1]
                        upper_band = float(latest_bb['upper_band'])
                        lower_band = float(latest_bb['lower_band'])
                        middle_band = float(latest_bb['middle_band'])
                        
                        # Determine position relative to bands
                        if current_price > upper_band:
                            bb_signal = "Above upper band (Overbought)"
                        elif current_price < lower_band:
                            bb_signal = "Below lower band (Oversold)"
                        elif current_price > middle_band:
                            bb_signal = "Above middle band (Bullish)"
                        else:
                            bb_signal = "Below middle band (Bearish)"
                        
                        ticker_analysis.append(f"Bollinger Bands: Upper ${upper_band:.2f}, Middle ${middle_band:.2f}, Lower ${lower_band:.2f}")
                        ticker_analysis.append(f"  Position: {bb_signal}")
                except Exception as e:
                    self.logger.debug(f"Bollinger Bands calculation failed for {ticker}: {e}")
                
                # 4. MACD Analysis
                try:
                    macd_data = self.macd_calc.load_macd_from_db(ticker_id)
                    if macd_data is not None and not macd_data.empty:
                        latest_macd = macd_data.iloc[-1]
                        macd_value = float(latest_macd['macd'])
                        signal_line = float(latest_macd['signal_line'])
                        histogram = float(latest_macd['histogram'])
                        
                        # Determine MACD signal
                        if macd_value > signal_line and histogram > 0:
                            macd_signal = "Bullish (MACD above signal)"
                        elif macd_value < signal_line and histogram < 0:
                            macd_signal = "Bearish (MACD below signal)"
                        else:
                            macd_signal = "Neutral"
                        
                        ticker_analysis.append(f"MACD: {macd_value:.2f}, Signal: {signal_line:.2f}, Histogram: {histogram:.2f}")
                        ticker_analysis.append(f"  Signal: {macd_signal}")
                except Exception as e:
                    self.logger.debug(f"MACD calculation failed for {ticker}: {e}")
                
                # 5. Stochastic Oscillator Analysis
                try:
                    stoch_signals = self.stoch_calc.get_stochastic_signals(ticker_id)
                    if stoch_signals and stoch_signals.get('success'):
                        stoch_k = stoch_signals['stoch_k']
                        stoch_d = stoch_signals['stoch_d']
                        signal = stoch_signals['signal']
                        signal_strength = stoch_signals['signal_strength']
                        crossover = stoch_signals.get('crossover_signal')
                        
                        ticker_analysis.append(f"Stochastic Oscillator: %K={stoch_k:.1f}, %D={stoch_d:.1f}")
                        ticker_analysis.append(f"  Signal: {signal} ({signal_strength})")
                        if crossover:
                            ticker_analysis.append(f"  Crossover: {crossover}")
                except Exception as e:
                    self.logger.debug(f"Stochastic calculation failed for {ticker}: {e}")
                
                # Add ticker analysis to main report if we have any indicators
                if ticker_analysis:
                    analysis_parts.append(f"\n{ticker}:")
                    for analysis in ticker_analysis:
                        analysis_parts.append(f"  - {analysis}")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating technical analysis text: {e}")
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
                ticker = position['symbol']
                try:
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
        """
        Create news sentiment analysis text for securities with active positions only.
        
        Args:
            portfolio_id: The portfolio ID to analyze
            
        Returns:
            str: Formatted text containing sentiment scores and recent headlines 
                 for each security with active positions, or empty string if no positions exist
        """
        try:
            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            if not positions:
                return ""
                
            analysis_parts = ["News Sentiment Analysis (Last 7 Days):\n"]
            
            # Iterate through active positions only
            for ticker_id, position in positions.items():
                ticker = position['symbol']
                try:
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

    def _create_options_analysis_text(self, portfolio_id: int) -> str:
        """
        Create options analysis summary text for securities with active positions.
        
        Includes: Implied Volatility, Put/Call Ratio, Open Interest, Options Volume
        
        Args:
            portfolio_id: The portfolio ID to analyze
            
        Returns:
            str: Formatted text containing options market data for each security
                 with active positions, or empty string if no positions exist
        """
        try:
            # Get only tickers with active positions
            positions = self.transactions_dao.get_current_positions(portfolio_id)
            if not positions:
                return ""
                
            analysis_parts = ["Options Market Analysis:\n"]
            
            # Iterate through active positions only
            for ticker_id, position in positions.items():
                ticker = position['symbol']
                ticker_options = []
                
                try:
                    # Get options summary for this ticker
                    options_summary = self.options_calc.get_options_summary(ticker)
                    
                    if options_summary and options_summary.get('underlying_price'):
                        # Basic options market data
                        ticker_options.append(f"Underlying Price: ${options_summary['underlying_price']:.2f}")
                        ticker_options.append(f"Available Expirations: {options_summary.get('num_expirations', 0)}")
                        
                        # Calls data
                        if options_summary.get('calls_volume') is not None:
                            calls_volume = options_summary['calls_volume']
                            calls_oi = options_summary.get('calls_open_interest', 0)
                            ticker_options.append(f"Calls Volume: {calls_volume:,.0f}, Open Interest: {calls_oi:,.0f}")
                            
                            # Implied volatility for calls
                            if options_summary.get('calls_iv_range'):
                                iv_range = options_summary['calls_iv_range']
                                avg_iv = (iv_range['min'] + iv_range['max']) / 2
                                avg_iv_pct = avg_iv * 100
                                min_iv_pct = iv_range['min'] * 100
                                max_iv_pct = iv_range['max'] * 100
                                ticker_options.append(f"Calls Implied Volatility: {avg_iv_pct:.1f}% (Range: {min_iv_pct:.1f}% - {max_iv_pct:.1f}%)")
                        
                        # Puts data
                        if options_summary.get('puts_volume') is not None:
                            puts_volume = options_summary['puts_volume']
                            puts_oi = options_summary.get('puts_open_interest', 0)
                            ticker_options.append(f"Puts Volume: {puts_volume:,.0f}, Open Interest: {puts_oi:,.0f}")
                            
                            # Implied volatility for puts
                            if options_summary.get('puts_iv_range'):
                                iv_range = options_summary['puts_iv_range']
                                avg_iv = (iv_range['min'] + iv_range['max']) / 2
                                avg_iv_pct = avg_iv * 100
                                min_iv_pct = iv_range['min'] * 100
                                max_iv_pct = iv_range['max'] * 100
                                ticker_options.append(f"Puts Implied Volatility: {avg_iv_pct:.1f}% (Range: {min_iv_pct:.1f}% - {max_iv_pct:.1f}%)")
                        
                        # Calculate Put/Call Ratio if both volumes exist
                        if (options_summary.get('calls_volume') and options_summary.get('puts_volume') and 
                            options_summary['calls_volume'] > 0):
                            put_call_ratio = options_summary['puts_volume'] / options_summary['calls_volume']
                            
                            # Interpret Put/Call Ratio
                            if put_call_ratio > 1.0:
                                pc_signal = "Bearish sentiment (More puts than calls)"
                            elif put_call_ratio < 0.7:
                                pc_signal = "Bullish sentiment (More calls than puts)"
                            else:
                                pc_signal = "Neutral sentiment"
                            
                            ticker_options.append(f"Put/Call Ratio: {put_call_ratio:.2f} - {pc_signal}")
                        
                        # Nearest expiration info
                        if options_summary.get('nearest_expiration'):
                            ticker_options.append(f"Nearest Expiration: {options_summary['nearest_expiration']}")
                    
                except Exception as e:
                    self.logger.debug(f"Options analysis failed for {ticker}: {e}")
                    # If options data not available, note it
                    ticker_options.append("Options data not available or stock does not have active options market")
                
                # Add ticker options analysis to main report if we have any data
                if ticker_options:
                    analysis_parts.append(f"\n{ticker}:")
                    for option_info in ticker_options:
                        analysis_parts.append(f"  - {option_info}")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error creating options analysis text: {e}")
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
        # Clear cached index to force rebuild with fresh data
        if portfolio_id in self.vector_indices:
            del self.vector_indices[portfolio_id]
            self.logger.info(f"Cleared cached index for portfolio {portfolio_id}")
        
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
            self.logger.info(f"Cleared cached index for portfolio {portfolio_id}")
        
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
