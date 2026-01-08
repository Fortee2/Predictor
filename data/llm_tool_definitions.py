"""
Tool definitions for LLM integration using AWS Bedrock Converse API.
This module defines the tool specifications that the LLM can use.
"""


def get_tool_config():
    """
    Build the complete tool configuration for Bedrock Converse API.
    Returns a dictionary with tool specifications.
    """
    return {
        "tools": [
            # Portfolio Query Tools
            {
                "toolSpec": {
                    "name": "get_portfolio_list",
                    "description": "Get a list of all portfolios with their IDs, names, descriptions, and status.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_portfolio_details",
                    "description": "Get detailed information about a specific portfolio including name, description, cash balance, and number of positions.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The unique ID of the portfolio"
                                }
                            },
                            "required": ["portfolio_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_current_positions",
                    "description": "Get current positions in a portfolio with shares, average price, current price, and current value.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                }
                            },
                            "required": ["portfolio_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_cash_balance",
                    "description": "Get the current cash balance of a portfolio.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                }
                            },
                            "required": ["portfolio_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_transaction_history_by_date",
                    "description": "Get transaction history for a portfolio including buys, sells, and dividends for a date range.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                },
                                "start_date": {
                                    "type": "string",
                                    "format": "date",
                                    "description": "The date to start retrieving transactions for in YYYY-MM-DD format. If not provided defaults to today minus 365 days."
                                },
                                "end_date": {
                                    "type": "string",
                                    "format": "date",
                                    "description": "The date to end retrieving transactions for in YYYY-MM-DD format. If not provided defaults to today."
                                }
                            },
                            "required": ["portfolio_id"]
                        }
                    }
                }
            },
            # Technical Analysis Tools
            {
                "toolSpec": {
                    "name": "calculate_rsi",
                    "description": "Calculate the Relative Strength Index (RSI) for a stock ticker. Returns RSI value and status (Overbought >70, Oversold <30, Neutral).",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                }
                            },
                            "required": ["ticker_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "calculate_macd",
                    "description": "Calculate MACD (Moving Average Convergence Divergence) indicator for a stock. Returns MACD line, signal line, histogram, and buy/sell signal.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                }
                            },
                            "required": ["ticker_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_comprehensive_analysis",
                    "description": "Get comprehensive technical and fundamental analysis for a ticker including RSI, MACD, moving averages, Bollinger Bands, stochastic oscillator, news sentiment, and fundamental metrics.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                },
                                "symbol": {
                                    "type": "string",
                                    "description": "The ticker symbol (e.g., AAPL)"
                                }
                            },
                            "required": ["ticker_id", "symbol"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_ticker_data",
                    "description": "Get current ticker data including last price, volume, and other basic information.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                }
                            },
                            "required": ["ticker_id"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_ticker_id_by_symbol",
                    "description": "Get the ticker ID for a given stock symbol.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "symbol": {
                                    "type": "string",
                                    "description": "The stock symbol (e.g., AAPL, MSFT)"
                                }
                            },
                            "required": ["symbol"]
                        }
                    }
                }
            },
            # News & Fundamental Tools
            {
                "toolSpec": {
                    "name": "get_news_sentiment",
                    "description": "Get news sentiment analysis for a stock ticker using FinBERT.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                },
                                "symbol": {
                                    "type": "string",
                                    "description": "The ticker symbol"
                                }
                            },
                            "required": ["ticker_id", "symbol"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_fundamental_data",
                    "description": "Get fundamental data for a stock including P/E ratio, market cap, dividend yield, EPS growth, and revenue growth.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "ticker_id": {
                                    "type": "integer",
                                    "description": "The ticker ID"
                                }
                            },
                            "required": ["ticker_id"]
                        }
                    }
                }
            },
            # Write Operation Tools
            {
                "toolSpec": {
                    "name": "log_transaction",
                    "description": "Log a buy or sell transaction for a stock in a portfolio.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                },
                                "ticker_symbol": {
                                    "type": "string",
                                    "description": "The stock symbol (e.g., AAPL)"
                                },
                                "transaction_type": {
                                    "type": "string",
                                    "description": "Type of transaction: 'buy' or 'sell'"
                                },
                                "shares": {
                                    "type": "number",
                                    "description": "Number of shares"
                                },
                                "price": {
                                    "type": "number",
                                    "description": "Price per share"
                                },
                                "transaction_date": {
                                    "type": "string",
                                    "description": "Transaction date in YYYY-MM-DD format (optional, defaults to today)"
                                }
                            },
                            "required": ["portfolio_id", "ticker_symbol", "transaction_type", "shares", "price"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "add_cash",
                    "description": "Add cash to a portfolio (deposit).",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                },
                                "amount": {
                                    "type": "number",
                                    "description": "Amount of cash to add"
                                }
                            },
                            "required": ["portfolio_id", "amount"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "withdraw_cash",
                    "description": "Withdraw cash from a portfolio.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                },
                                "amount": {
                                    "type": "number",
                                    "description": "Amount of cash to withdraw"
                                }
                            },
                            "required": ["portfolio_id", "amount"]
                        }
                    }
                }
            },
            # AI Recommendation Tools
            {
                "toolSpec": {
                    "name": "save_recommendation",
                    "description": "Save an AI trading recommendation to the database for tracking. Use this when you want to make a formal recommendation that should be tracked and linked to future trades. The recommendation will be marked as PENDING and can be followed up later.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID this recommendation is for"
                                },
                                "ticker_symbol": {
                                    "type": "string",
                                    "description": "The stock ticker symbol (e.g., AAPL, TSLA)"
                                },
                                "recommendation_type": {
                                    "type": "string",
                                    "description": "Type of recommendation",
                                    "enum": ["BUY", "SELL", "HOLD", "REDUCE", "INCREASE"]
                                },
                                "recommended_quantity": {
                                    "type": "number",
                                    "description": "Suggested number of shares (optional)"
                                },
                                "recommended_price": {
                                    "type": "number",
                                    "description": "Suggested target price (optional)"
                                },
                                "confidence_score": {
                                    "type": "number",
                                    "description": "Your confidence in this recommendation from 0-100 (e.g., 85 means 85% confident)"
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "Detailed explanation of why you're making this recommendation, including technical analysis, fundamental factors, and market conditions"
                                },
                                "technical_indicators": {
                                    "type": "object",
                                    "description": "Key technical indicator values at time of recommendation (e.g., {'RSI': 28.5, 'MACD': 1.25, 'MA_20': 175.30})"
                                },
                                "sentiment_score": {
                                    "type": "number",
                                    "description": "News sentiment score if analyzed (typically -1 to 1)"
                                },
                                "expires_days": {
                                    "type": "integer",
                                    "description": "Number of days until this recommendation expires (default 7 days)"
                                }
                            },
                            "required": ["portfolio_id", "ticker_symbol", "recommendation_type", "reasoning"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_active_recommendations",
                    "description": "Get all active (pending) recommendations for a portfolio that haven't been followed or expired yet.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "portfolio_id": {
                                    "type": "integer",
                                    "description": "The portfolio ID"
                                }
                            },
                            "required": ["portfolio_id"]
                        }
                    }
                }
            },
            # Watch list Tools
            {
                "toolSpec": {
                    "name": "get_watchlists",
                    "description": "Get all watchlists.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_watchlist_tickers",
                    "description": "Get all tickers in a specific watchlist.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "watchlist_id": {
                                    "type": "integer",
                                    "description": "The watchlist ID"
                                }
                            },
                            "required": ["watchlist_id"]
                        }
                    }
                }
            }
        ]
    }
