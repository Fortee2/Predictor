"""
Shared Analysis Metrics Module

This module provides common technical and fundamental analysis metrics
that can be used by both portfolio and watchlist analysis to follow
the DRY (Don't Repeat Yourself) principle.
"""

import datetime
import decimal
from typing import Any, Dict, Optional, Tuple


class SharedAnalysisMetrics:
    """
    A class that provides shared analysis metrics for both portfolio and watchlist analysis.
    This ensures consistency and reduces code duplication.
    """

    def __init__(
        self,
        rsi_calc,
        moving_avg,
        bb_analyzer,
        macd_analyzer,
        fundamental_dao,
        news_analyzer,
        options_analyzer,
        trend_analyzer,
        stochastic_analyzer=None,
    ):
        """
        Initialize the shared metrics analyzer with required components.

        Args:
            rsi_calc: RSI calculations instance
            moving_avg: Moving averages instance
            bb_analyzer: Bollinger Bands analyzer instance
            macd_analyzer: MACD analyzer instance
            fundamental_dao: Fundamental data DAO instance
            news_analyzer: News sentiment analyzer instance
            options_analyzer: Options data analyzer instance
            trend_analyzer: Trend analyzer instance
            stochastic_analyzer: Stochastic Oscillator analyzer instance (optional)
        """
        self.rsi_calc = rsi_calc
        self.moving_avg = moving_avg
        self.bb_analyzer = bb_analyzer
        self.macd_analyzer = macd_analyzer
        self.fundamental_dao = fundamental_dao
        self.news_analyzer = news_analyzer
        self.options_analyzer = options_analyzer
        self.trend_analyzer = trend_analyzer
        self.stochastic_analyzer = stochastic_analyzer

        # Initialize ticker_dao for getting price data
        self.ticker_dao = None
        if hasattr(bb_analyzer, "ticker_dao"):
            self.ticker_dao = bb_analyzer.ticker_dao

    def analyze_rsi(self, ticker_id: int) -> Dict[str, Any]:
        """
        Analyze RSI for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze

        Returns:
            Dictionary containing RSI analysis results
        """
        try:
            self.rsi_calc.calculateRSI(ticker_id)
            rsi_result = self.rsi_calc.retrievePrices(1, ticker_id)

            if not rsi_result.empty:
                latest_rsi = rsi_result.iloc[-1]
                rsi_value = latest_rsi["rsi"]
                rsi_date = rsi_result.index[-1]
                rsi_status = (
                    "Overbought"
                    if rsi_value > 70
                    else "Oversold" if rsi_value < 30 else "Neutral"
                )

                return {
                    "success": True,
                    "value": rsi_value,
                    "date": rsi_date,
                    "status": rsi_status,
                    "display_text": f"RSI ({rsi_date.strftime('%Y-%m-%d')}): {rsi_value:.2f} - {rsi_status}",
                }
            else:
                return {"success": False, "error": "No RSI data available"}
        except Exception as e:
            return {"success": False, "error": f"Unable to calculate RSI: {str(e)}"}

    def analyze_moving_average(
        self, ticker_id: int, period: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze moving average and trend for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze
            period: The moving average period (default: 20)

        Returns:
            Dictionary containing moving average analysis results
        """
        try:
            ma_data = self.moving_avg.update_moving_averages(ticker_id, period)

            if not ma_data.empty:
                latest_ma = ma_data.iloc[-1]
                date_str = str(ma_data.index[-1]).split()[0]
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                ma_value = latest_ma.iloc[0]

                result = {
                    "success": True,
                    "value": ma_value,
                    "date": dt,
                    "period": period,
                    "display_text": f"{period}-day MA ({dt.strftime('%Y-%m-%d')}): {ma_value:.2f}",
                }

                # Add trend analysis
                try:
                    ma_trend = self.trend_analyzer.analyze_ma_trend(ticker_id, period)
                    if ma_trend and isinstance(ma_trend, dict):
                        direction_emoji = (
                            "↗️"
                            if ma_trend.get("direction") == "UP"
                            else "↘️" if ma_trend.get("direction") == "DOWN" else "➡️"
                        )
                        direction = ma_trend.get("direction", "UNKNOWN")
                        strength = ma_trend.get("strength", "UNKNOWN")

                        result["trend"] = {
                            "direction": direction,
                            "strength": strength,
                            "emoji": direction_emoji,
                            "percent_change": ma_trend.get("percent_change"),
                            "display_text": f"MA Trend: {direction_emoji} {direction} ({strength})",
                        }

                        if ma_trend.get("percent_change") is not None:
                            result["trend"][
                                "rate_display"
                            ] = f"Rate of Change: {ma_trend['percent_change']:.2f}%"
                    else:
                        result["trend"] = {
                            "direction": "UNKNOWN",
                            "strength": "UNKNOWN",
                            "emoji": "➡️",
                            "display_text": "MA Trend: ➡️ UNKNOWN (UNKNOWN)",
                        }
                except Exception as e:
                    result["trend"] = {"error": f"Unable to analyze trend: {str(e)}"}

                # Add price vs MA analysis
                try:
                    price_vs_ma = self.trend_analyzer.analyze_price_vs_ma(
                        ticker_id, period
                    )
                    if price_vs_ma["position"] != "UNKNOWN":
                        position_text = (
                            "Above MA"
                            if price_vs_ma["position"] == "ABOVE_MA"
                            else (
                                "Below MA"
                                if price_vs_ma["position"] == "BELOW_MA"
                                else "At MA"
                            )
                        )
                        distance_formatted = f"{price_vs_ma['distance_percent']:.2f}"

                        result["price_position"] = {
                            "position": price_vs_ma["position"],
                            "distance_percent": price_vs_ma["distance_percent"],
                            "display_text": f"Price Position: {position_text} ({distance_formatted}% from MA)",
                        }
                    else:
                        result["price_position"] = {
                            "error": "Unable to determine price position"
                        }
                except Exception as e:
                    result["price_position"] = {
                        "error": f"Unable to analyze price position: {str(e)}"
                    }

                return result
            else:
                return {"success": False, "error": "No moving average data available"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to calculate moving average: {str(e)}",
            }

    def analyze_bollinger_bands(self, ticker_id: int) -> Dict[str, Any]:
        """
        Analyze Bollinger Bands for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze

        Returns:
            Dictionary containing Bollinger Bands analysis results
        """
        try:
            bb_data = self.bb_analyzer.generate_bollinger_band_data(ticker_id)

            if bb_data:
                bb_mean = bb_data["bollinger_bands"]["mean"]
                bb_stddev = bb_data["bollinger_bands"]["stddev"]

                return {
                    "success": True,
                    "mean": bb_mean,
                    "stddev": bb_stddev,
                    "display_text": f"Bollinger Bands - Mean: {bb_mean:.2f}, StdDev: {bb_stddev:.2f}",
                }
            else:
                return {"success": False, "error": "No Bollinger Bands data available"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to calculate Bollinger Bands: {str(e)}",
            }

    def analyze_macd(self, ticker_id: int) -> Dict[str, Any]:
        """
        Analyze MACD for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze

        Returns:
            Dictionary containing MACD analysis results
        """
        try:
            macd_data = self.macd_analyzer.calculate_macd(ticker_id)

            if (macd_data is not None) and (not macd_data.empty):
                latest_macd = macd_data.iloc[-1]
                macd_date = macd_data.index[-1]

                # Determine current MACD signal
                if latest_macd["macd"] > latest_macd["signal_line"]:
                    current_signal = "BUY"
                    signal_strength = (
                        "Strong" if latest_macd["histogram"] > 0.1 else "Weak"
                    )
                else:
                    current_signal = "SELL"
                    signal_strength = (
                        "Strong" if latest_macd["histogram"] < -0.1 else "Weak"
                    )

                # Determine trend direction based on histogram
                if latest_macd["histogram"] > 0:
                    trend_direction = (
                        "Strengthening"
                        if len(macd_data) > 1
                        and latest_macd["histogram"] > macd_data.iloc[-2]["histogram"]
                        else "Weakening"
                    )
                else:
                    trend_direction = (
                        "Strengthening"
                        if len(macd_data) > 1
                        and latest_macd["histogram"] > macd_data.iloc[-2]["histogram"]
                        else "Weakening"
                    )

                return {
                    "success": True,
                    "macd_line": latest_macd["macd"],
                    "signal_line": latest_macd["signal_line"],
                    "histogram": latest_macd["histogram"],
                    "date": macd_date,
                    "current_signal": current_signal,
                    "signal_strength": signal_strength,
                    "trend_direction": trend_direction,
                    "display_text": f"MACD ({macd_date.strftime('%Y-%m-%d')}): {current_signal} ({signal_strength})",
                }
            else:
                return {"success": False, "error": "No MACD data available"}
        except Exception as e:
            return {"success": False, "error": f"Unable to calculate MACD: {str(e)}"}

    def analyze_fundamental_data(self, ticker_id: int) -> Dict[str, Any]:
        """
        Analyze fundamental data for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze

        Returns:
            Dictionary containing fundamental analysis results
        """
        try:
            fundamental_data = self.fundamental_dao.get_latest_fundamental_data(
                ticker_id
            )

            if fundamental_data:
                result = {"success": True, "data": fundamental_data}

                display_items = []
                if fundamental_data.get("pe_ratio") is not None:
                    display_items.append(
                        f"P/E Ratio: {fundamental_data['pe_ratio']:.2f}"
                    )
                if fundamental_data.get("market_cap") is not None:
                    market_cap_str = f"{fundamental_data['market_cap']:,.2f}"
                    display_items.append(f"Market Cap: ${market_cap_str}")
                if fundamental_data.get("dividend_yield"):
                    display_items.append(
                        f"Dividend Yield: {fundamental_data['dividend_yield']:.2f}%"
                    )

                result["display_items"] = display_items
                return result
            else:
                return {"success": False, "error": "No fundamental data available"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to retrieve fundamental data: {str(e)}",
            }

    def analyze_news_sentiment(self, ticker_id: int, symbol: str) -> Dict[str, Any]:
        """
        Analyze news sentiment for a given ticker.

        Args:
            ticker_id: The ticker ID to analyze
            symbol: The ticker symbol

        Returns:
            Dictionary containing news sentiment analysis results
        """
        try:
            sentiment_data = self.news_analyzer.get_sentiment_summary(ticker_id, symbol)

            if (
                sentiment_data
                and sentiment_data["status"] != "No sentiment data available"
            ):
                return {
                    "success": True,
                    "status": sentiment_data["status"],
                    "average_sentiment": sentiment_data["average_sentiment"],
                    "article_count": sentiment_data["article_count"],
                    "display_text": f"News Sentiment: {sentiment_data['status']} (Avg: {sentiment_data['average_sentiment']:.2f}, Articles: {sentiment_data['article_count']})",
                }
            else:
                return {"success": False, "error": "No sentiment data available"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to analyze news sentiment: {str(e)}",
            }

    def analyze_stochastic(
        self, ticker_id: int, k_period: int = 14, d_period: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze Stochastic Oscillator for a given ticker - following existing analysis patterns.

        Args:
            ticker_id: The ticker ID to analyze
            k_period: K period for stochastic calculation (default: 14)
            d_period: D period for smoothing (default: 3)

        Returns:
            Dictionary containing stochastic analysis results
        """
        if self.stochastic_analyzer is None:
            return {"success": False, "error": "Stochastic analyzer not available"}

        try:
            stoch_signals = self.stochastic_analyzer.get_stochastic_signals(
                ticker_id, k_period, d_period
            )

            if stoch_signals.get("success"):
                result = {
                    "success": True,
                    "stoch_k": stoch_signals["stoch_k"],
                    "stoch_d": stoch_signals["stoch_d"],
                    "date": stoch_signals["date"],
                    "signal": stoch_signals["signal"],
                    "signal_strength": stoch_signals["signal_strength"],
                    "crossover_signal": stoch_signals["crossover_signal"],
                    "display_text": stoch_signals["display_text"],
                }

                # Add divergence analysis if available
                try:
                    divergence_analysis = self.stochastic_analyzer.analyze_divergence(
                        ticker_id, k_period, d_period
                    )
                    if divergence_analysis.get("success"):
                        result["divergence"] = {
                            "type": divergence_analysis["divergence"],
                            "price_trend": divergence_analysis["price_trend"],
                            "stoch_trend": divergence_analysis["stoch_trend"],
                            "display_text": divergence_analysis["display_text"],
                        }
                    else:
                        result["divergence"] = {
                            "error": divergence_analysis.get(
                                "error", "Unable to analyze divergence"
                            )
                        }
                except Exception as e:
                    result["divergence"] = {
                        "error": f"Unable to analyze divergence: {str(e)}"
                    }

                return result
            else:
                return {
                    "success": False,
                    "error": stoch_signals.get(
                        "error", "Unable to calculate stochastic"
                    ),
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to analyze stochastic: {str(e)}",
            }

    def analyze_portfolio_position_metrics(
        self,
        ticker_id: int,
        symbol: str,
        position_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze portfolio position metrics including average cost, current value, and last closed price.

        Args:
            ticker_id: The ticker ID to analyze
            symbol: The ticker symbol
            position_data: Optional position data containing shares, avg_price, current_price, etc.

        Returns:
            Dictionary containing portfolio position metrics
        """
        try:
            result = {"success": True, "symbol": symbol, "ticker_id": ticker_id}

            # Get last closed price from ticker data
            last_price = None
            if self.ticker_dao:
                try:
                    ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
                    if ticker_data and ticker_data.get("last_price"):
                        last_price = float(ticker_data["last_price"])
                        result["last_closed_price"] = last_price
                        result["last_update"] = ticker_data.get("last_update")
                except Exception as e:
                    result["last_closed_price_error"] = (
                        f"Unable to get last price: {str(e)}"
                    )

            # If position data is provided, calculate position metrics
            if position_data:
                shares = position_data.get("shares", 0)
                avg_price = position_data.get("avg_price", 0)
                current_price = position_data.get("current_price", last_price)

                result.update(
                    {
                        "shares": shares,
                        "average_cost": avg_price,
                        "current_price": current_price,
                    }
                )

                if shares and current_price:
                    current_value = shares * current_price
                    result["current_value"] = current_value

                    # Calculate gain/loss if we have average cost
                    if avg_price and avg_price > 0:
                        cost_basis = shares * avg_price
                        gain_loss = current_value - cost_basis
                        gain_loss_pct = (gain_loss / cost_basis) * 100

                        result.update(
                            {
                                "cost_basis": cost_basis,
                                "gain_loss": gain_loss,
                                "gain_loss_pct": gain_loss_pct,
                            }
                        )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to analyze position metrics: {str(e)}",
            }

    def analyze_options_data(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze options data for a given ticker symbol.

        Args:
            symbol: The ticker symbol

        Returns:
            Dictionary containing options analysis results
        """
        try:
            options_summary = self.options_analyzer.get_options_summary(symbol)

            if options_summary:
                result = {
                    "success": True,
                    "num_expirations": options_summary["num_expirations"],
                    "nearest_expiration": options_summary["nearest_expiration"],
                }

                if "calls_volume" in options_summary:
                    calls_volume = options_summary["calls_volume"]
                    puts_volume = options_summary["puts_volume"]

                    # Calculate put/call ratio
                    put_call_ratio = 0
                    try:
                        if calls_volume > 0:
                            put_call_ratio = puts_volume / calls_volume
                    except (ZeroDivisionError, decimal.DivisionUndefined):
                        put_call_ratio = 0

                    sentiment = (
                        "Bearish"
                        if put_call_ratio > 1
                        else "Bullish" if put_call_ratio < 1 else "Neutral"
                    )

                    # Calculate average implied volatility
                    avg_call_iv = (
                        options_summary["calls_iv_range"]["min"]
                        + options_summary["calls_iv_range"]["max"]
                    ) / 2
                    market_expectation = (
                        "High Volatility"
                        if avg_call_iv > 0.5
                        else (
                            "Moderate Volatility"
                            if avg_call_iv > 0.2
                            else "Low Volatility"
                        )
                    )

                    result.update(
                        {
                            "calls_volume": calls_volume,
                            "puts_volume": puts_volume,
                            "put_call_ratio": put_call_ratio,
                            "volume_sentiment": sentiment,
                            "calls_iv_range": options_summary["calls_iv_range"],
                            "puts_iv_range": options_summary["puts_iv_range"],
                            "market_expectation": market_expectation,
                            "display_text": f"Options: P/C Ratio {put_call_ratio:.2f} ({sentiment}), {market_expectation}",
                        }
                    )

                return result
            else:
                return {"success": False, "error": "No options data available"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Unable to analyze options data: {str(e)}",
            }

    def get_comprehensive_analysis(
        self,
        ticker_id: int,
        symbol: str,
        include_options: bool = True,
        include_stochastic: bool = True,
        ma_period: int = 20,
        position_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive analysis for a ticker including all available metrics.

        Args:
            ticker_id: The ticker ID to analyze
            symbol: The ticker symbol
            include_options: Whether to include options analysis
            include_stochastic: Whether to include stochastic analysis
            ma_period: Moving average period to use
            position_data: Optional position data for portfolio metrics

        Returns:
            Dictionary containing all analysis results
        """
        analysis = {
            "ticker_id": ticker_id,
            "symbol": symbol,
            "rsi": self.analyze_rsi(ticker_id),
            "moving_average": self.analyze_moving_average(ticker_id, ma_period),
            "bollinger_bands": self.analyze_bollinger_bands(ticker_id),
            "macd": self.analyze_macd(ticker_id),
            "fundamental": self.analyze_fundamental_data(ticker_id),
            "news_sentiment": self.analyze_news_sentiment(ticker_id, symbol),
        }

        # Add portfolio position metrics if position data is provided
        if position_data:
            analysis["portfolio_metrics"] = self.analyze_portfolio_position_metrics(
                ticker_id, symbol, position_data
            )

        if include_options:
            analysis["options"] = self.analyze_options_data(symbol)

        if include_stochastic and self.stochastic_analyzer is not None:
            analysis["stochastic"] = self.analyze_stochastic(ticker_id)

        return analysis

    def format_analysis_output(
        self, analysis: Dict[str, Any], shares_info: str = "", notes: str = None
    ) -> str:
        """
        Format analysis results for display output.

        Args:
            analysis: The analysis results dictionary
            shares_info: Additional shares information to display
            notes: Optional notes to display

        Returns:
            Formatted string for display
        """
        symbol = analysis["symbol"]
        output_lines = []

        # Header
        output_lines.append(f"║ {symbol}{shares_info:<56}║")
        output_lines.append(
            "║──────────────────────────────────────────────────────────║"
        )

        # Portfolio Position Metrics (if available)
        portfolio_metrics = analysis.get("portfolio_metrics", {})
        if portfolio_metrics.get("success"):
            output_lines.append(
                "║ Portfolio Position Metrics:                                  ║"
            )

            # Average Cost
            if "average_cost" in portfolio_metrics:
                avg_cost = portfolio_metrics["average_cost"]
                output_lines.append(
                    f"║   Average Cost: ${avg_cost:.2f}{' ' * (44 - len(f'{avg_cost:.2f}'))}║"
                )

            # Current Value
            if "current_value" in portfolio_metrics:
                current_value = portfolio_metrics["current_value"]
                output_lines.append(
                    f"║   Current Value: ${current_value:,.2f}{' ' * (43 - len(f'{current_value:,.2f}'))}║"
                )

            # Last Closed Price
            if "last_closed_price" in portfolio_metrics:
                last_price = portfolio_metrics["last_closed_price"]
                last_update = portfolio_metrics.get("last_update", "Unknown")
                if last_update and last_update != "Unknown":
                    if hasattr(last_update, "strftime"):
                        date_str = last_update.strftime("%Y-%m-%d")
                    else:
                        date_str = str(last_update)
                    output_lines.append(
                        f"║   Last Closed Price: ${last_price:.2f} ({date_str}){' ' * (25 - len(f'{last_price:.2f}') - len(date_str))}║"
                    )
                else:
                    output_lines.append(
                        f"║   Last Closed Price: ${last_price:.2f}{' ' * (38 - len(f'{last_price:.2f}'))}║"
                    )
            elif "last_closed_price_error" in portfolio_metrics:
                error_msg = portfolio_metrics["last_closed_price_error"][:40]
                output_lines.append(f"║   Last Closed Price: {error_msg:<40}║")

            # Gain/Loss information
            if (
                "gain_loss" in portfolio_metrics
                and "gain_loss_pct" in portfolio_metrics
            ):
                gain_loss = portfolio_metrics["gain_loss"]
                gain_loss_pct = portfolio_metrics["gain_loss_pct"]
                gl_color_start = "" if gain_loss >= 0 else ""
                gl_color_end = "" if gain_loss >= 0 else ""
                sign = "+" if gain_loss >= 0 else ""
                output_lines.append(
                    f"║   Gain/Loss: {gl_color_start}{sign}${gain_loss:.2f} ({sign}{gain_loss_pct:.2f}%){gl_color_end}{' ' * (25 - len(f'{gain_loss:.2f}') - len(f'{gain_loss_pct:.2f}'))}║"
                )

            output_lines.append(
                "║──────────────────────────────────────────────────────────║"
            )

        # RSI
        rsi = analysis.get("rsi", {})
        if rsi.get("success"):
            rsi_status = rsi["status"]
            padding = 45 - len(rsi_status)
            output_lines.append(f"║ {rsi['display_text']:<{60 - padding}}║")
        else:
            output_lines.append(
                f"║ RSI: {rsi.get('error', 'Unable to calculate'):<51}║"
            )

        # Moving Average
        ma = analysis.get("moving_average", {})
        if ma.get("success"):
            output_lines.append(f"║ {ma['display_text']}{' ' * 45}║")

            # MA Trend
            if "trend" in ma and "display_text" in ma["trend"]:
                trend_text = ma["trend"]["display_text"]
                padding = 60 - len(trend_text)
                output_lines.append(f"║ {trend_text}{' ' * padding}║")

                if "rate_display" in ma["trend"]:
                    rate_text = f"   {ma['trend']['rate_display']}"
                    padding = 60 - len(rate_text)
                    output_lines.append(f"║{rate_text}{' ' * padding}║")

            # Price Position
            if "price_position" in ma and "display_text" in ma["price_position"]:
                pos_text = ma["price_position"]["display_text"]
                padding = 60 - len(pos_text)
                output_lines.append(f"║ {pos_text}{' ' * padding}║")
        else:
            output_lines.append(
                f"║ Moving Average: {ma.get('error', 'Unable to calculate'):<42}║"
            )

        # Bollinger Bands
        bb = analysis.get("bollinger_bands", {})
        if bb.get("success"):
            output_lines.append(
                f"║ Bollinger Bands:                                             ║"
            )
            output_lines.append(f"║   Mean: {bb['mean']:.2f}{' ' * 49}║")
            output_lines.append(f"║   StdDev: {bb['stddev']:.2f}{' ' * 47}║")
        else:
            output_lines.append(
                f"║ Bollinger Bands: {bb.get('error', 'Unable to calculate'):<37}║"
            )

        # MACD
        macd = analysis.get("macd", {})
        if macd.get("success"):
            output_lines.append(
                f"║ MACD ({macd['date'].strftime('%Y-%m-%d')}):                                ║"
            )
            output_lines.append(f"║   MACD Line: {macd['macd_line']:.2f}{' ' * 44}║")
            output_lines.append(
                f"║   Signal Line: {macd['signal_line']:.2f}{' ' * 42}║"
            )
            output_lines.append(f"║   Histogram: {macd['histogram']:.2f}{' ' * 44}║")
            output_lines.append(
                f"║ Current MACD Signal ({macd['date'].strftime('%Y-%m-%d')}): {macd['current_signal']} ({macd['signal_strength']}){' ' * (25 - len(macd['signal_strength']))}║"
            )
            output_lines.append(
                f"║ MACD Momentum: {macd['trend_direction']}{' ' * (47 - len(macd['trend_direction']))}║"
            )
        else:
            output_lines.append(
                f"║ MACD: {macd.get('error', 'Unable to calculate'):<51}║"
            )

        # Fundamental Data
        fund = analysis.get("fundamental", {})
        if fund.get("success") and fund.get("display_items"):
            output_lines.append(
                "║ Fundamental Data:                                            ║"
            )
            for item in fund["display_items"]:
                padding = 60 - len(f"   {item}")
                output_lines.append(f"║   {item}{' ' * padding}║")
        else:
            output_lines.append(
                f"║ Fundamental Data: {fund.get('error', 'Unable to retrieve'):<37}║"
            )

        # News Sentiment
        news = analysis.get("news_sentiment", {})
        if news.get("success"):
            output_lines.append(f"║ News Sentiment: {news['status']:<47}║")
            output_lines.append(
                f"║   Average Score: {news['average_sentiment']:.2f}{' ' * 41}║"
            )
            output_lines.append(
                f"║   Articles Analyzed: {news['article_count']}{' ' * 39}║"
            )
        else:
            output_lines.append(
                f"║ News Sentiment: {news.get('error', 'No data available'):<43}║"
            )

        # Stochastic Oscillator
        stochastic = analysis.get("stochastic", {})
        if stochastic.get("success"):
            output_lines.append(f"║ {stochastic['display_text']:<60}║")

            # Crossover signal if available
            if stochastic.get("crossover_signal"):
                crossover_text = f"   Crossover: {stochastic['crossover_signal'].replace('_', ' ').title()}"
                padding = 60 - len(crossover_text)
                output_lines.append(f"║{crossover_text}{' ' * padding}║")

            # Divergence analysis if available
            if (
                "divergence" in stochastic
                and "display_text" in stochastic["divergence"]
            ):
                div_text = f"   {stochastic['divergence']['display_text']}"
                padding = 60 - len(div_text)
                output_lines.append(f"║{div_text}{' ' * padding}║")
        else:
            output_lines.append(
                f"║ Stochastic: {stochastic.get('error', 'Not available'):<45}║"
            )

        output_lines.append(
            "════════════════════════════════════════════════════════════════"
        )

        # Options Data
        options = analysis.get("options", {})
        if options.get("success"):
            output_lines.append(
                "║ Options Data:                                                  ║"
            )
            output_lines.append(
                f"║   Available Expirations: {options['num_expirations']}{' ' * 37}║"
            )
            output_lines.append(
                f"║   Nearest Expiry: {options['nearest_expiration']}{' ' * 35}║"
            )

            if "calls_volume" in options:
                calls_volume = options["calls_volume"]
                puts_volume = options["puts_volume"]
                put_call_ratio = options["put_call_ratio"]
                sentiment = options["volume_sentiment"]

                output_lines.append(
                    f"║   Total Calls Volume: {calls_volume:,}{' ' * (37 - len(str(calls_volume)))}║"
                )
                output_lines.append(
                    f"║   Total Puts Volume: {puts_volume:,}{' ' * (38 - len(str(puts_volume)))}║"
                )
                output_lines.append(
                    f"║   Put/Call Ratio: {put_call_ratio:.2f}{' ' * 42}║"
                )
                output_lines.append(
                    f"║   Volume Sentiment: {sentiment}{' ' * (42 - len(sentiment))}║"
                )

                output_lines.append(
                    "║   Implied Volatility Range:                                  ║"
                )
                output_lines.append(
                    f"║     Calls: {options['calls_iv_range']['min']:.2%} - {options['calls_iv_range']['max']:.2%}{' ' * 35}║"
                )
                output_lines.append(
                    f"║     Puts: {options['puts_iv_range']['min']:.2%} - {options['puts_iv_range']['max']:.2%}{' ' * 36}║"
                )
                output_lines.append(
                    f"║   Market Expectation: {options['market_expectation']:<42}║"
                )
        else:
            output_lines.append(
                f"║ Options Data: {options.get('error', 'Not available'):<45}║"
            )

        # Notes
        if notes:
            output_lines.append(
                "════════════════════════════════════════════════════════════════"
            )
            output_lines.append(
                f"║ Notes: {notes[:50]}{' ' * (51 - min(50, len(notes)))}║"
            )
            if len(notes) > 50:
                output_lines.append(
                    f"║   {notes[50:100]}{' ' * (57 - min(50, len(notes) - 50))}║"
                )

        output_lines.append(
            "════════════════════════════════════════════════════════════════"
        )

        return "\n".join(output_lines)
