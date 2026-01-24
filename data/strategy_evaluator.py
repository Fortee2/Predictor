"""
Strategy Evaluator - Core signal generation engine.

This module evaluates trading strategies against ticker data and generates
trading signals with confidence scores based on anchor and confirmation indicators.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# from .ai_recommendations_dao import AIRecommendationsDAO  # TODO: Add this module if needed
from .bollinger_bands import BollingerBandAnalyzer
from .config import Config
from .fundamental_data_dao import FundamentalDataDAO
from .macd import MACD
from .moving_averages import moving_averages
from .news_sentiment_analyzer import NewsSentimentAnalyzer
from .options_data import OptionsData
from .portfolio_dao import PortfolioDAO
from .rsi_calculations import rsi_calculations
from .shared_analysis_metrics import SharedAnalysisMetrics
from .stochastic_oscillator import StochasticOscillator
from .ticker_dao import TickerDao
from .trading_signal_dao import TradingSignalDAO
from .trading_strategy_dao import TradingStrategyDAO
from .trend_analyzer import TrendAnalyzer
from .utility import DatabaseConnectionPool

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """
    Core engine for evaluating trading strategies and generating signals.

    Uses SharedAnalysisMetrics to get indicator values and evaluates
    strategy conditions to generate BUY/SELL signals with confidence scores.
    """

    def __init__(self, pool: DatabaseConnectionPool, config: Optional[Config] = None):
        """
        Initialize the Strategy Evaluator.

        Args:
            pool: Database connection pool
            config: Optional configuration object
        """
        self.pool = pool
        self.config = config if config else Config()

        # Initialize all indicator analyzers
        self.ticker_dao = TickerDao(pool)
        self.portfolio_dao = PortfolioDAO(pool)
        self.rsi_calc = rsi_calculations(pool)
        self.moving_avg = moving_averages(pool)
        self.macd_analyzer = MACD(pool)
        self.bb_analyzer = BollingerBandAnalyzer(self.ticker_dao)
        self.stochastic_analyzer = StochasticOscillator(pool)
        self.trend_analyzer = TrendAnalyzer(pool)
        self.fundamental_dao = FundamentalDataDAO(pool)
        self.news_analyzer = NewsSentimentAnalyzer(pool)
        self.options_analyzer = OptionsData(pool)

        # Create shared metrics analyzer
        self.metrics = SharedAnalysisMetrics(
            self.rsi_calc,
            self.moving_avg,
            self.bb_analyzer,
            self.macd_analyzer,
            self.fundamental_dao,
            self.news_analyzer,
            self.options_analyzer,
            self.trend_analyzer,
            self.stochastic_analyzer,
        )

        # Initialize DAOs
        self.signal_dao = TradingSignalDAO(pool)
        self.strategy_dao = TradingStrategyDAO(pool)
        # self.ai_rec_dao = AIRecommendationsDAO(pool)  # TODO: Add this module if needed
        self.ai_rec_dao = None  # Placeholder until AIRecommendationsDAO is implemented

    def evaluate_strategy(
        self,
        strategy: Dict,
        ticker_id: int,
        symbol: str,
        portfolio_id: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Evaluate a strategy against a ticker and generate signal if conditions met.

        Args:
            strategy: Strategy configuration dict
            ticker_id: Ticker ID to evaluate
            symbol: Ticker symbol
            portfolio_id: Optional portfolio ID

        Returns:
            Signal dict if conditions met, None otherwise
        """
        try:
            logger.info(
                f"Evaluating strategy '{strategy['name']}' for {symbol} (ticker_id={ticker_id})"
            )

            # Get comprehensive analysis for the ticker
            analysis = self.metrics.get_comprehensive_analysis(
                ticker_id=ticker_id,
                symbol=symbol,
                include_options=True,
                include_stochastic=True,
                ma_period=strategy.get("anchor_config", {}).get("period", 20),
            )

            # Evaluate anchor indicator
            anchor_signal = self.evaluate_anchor_indicator(strategy, analysis)

            if not anchor_signal or anchor_signal["signal_type"] == "HOLD":
                logger.debug(f"Anchor indicator did not trigger signal for {symbol}")
                return None

            # Evaluate confirmation indicators
            confirmations = self.evaluate_confirmations(strategy, analysis)

            # Calculate final confidence score
            confidence_score = self.calculate_confidence_score(
                anchor_signal, confirmations, strategy
            )

            # Check minimum confidence threshold
            min_confidence = strategy.get("min_confidence_score", 50.0)
            if confidence_score < min_confidence:
                logger.debug(
                    f"Signal confidence {confidence_score:.1f}% below minimum {min_confidence}% for {symbol}"
                )
                return None

            # Determine signal strength
            if confidence_score >= 80:
                signal_strength = "STRONG"
            elif confidence_score >= 60:
                signal_strength = "MODERATE"
            else:
                signal_strength = "WEAK"

            # Get current price
            current_price = self._get_current_price(ticker_id)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return None

            # Build indicator snapshot
            indicator_snapshot = self._build_indicator_snapshot(analysis, anchor_signal, confirmations)

            # Calculate expiration date
            expires_date = self._calculate_expiration_date(strategy)

            # Create signal dict
            signal = {
                "strategy_id": strategy["id"],
                "ticker_id": ticker_id,
                "symbol": symbol,
                "signal_type": anchor_signal["signal_type"],
                "signal_strength": signal_strength,
                "confidence_score": confidence_score,
                "indicator_snapshot": indicator_snapshot,
                "price_at_signal": current_price,
                "portfolio_id": portfolio_id,
                "signal_date": datetime.now(),
                "expires_date": expires_date,
                "reasoning": anchor_signal["reasoning"],
                "strategy_name": strategy["name"],
            }

            logger.info(
                f"Generated {signal['signal_type']} signal for {symbol} "
                f"with {confidence_score:.1f}% confidence ({signal_strength})"
            )

            return signal

        except Exception as e:
            logger.error(f"Error evaluating strategy for {symbol}: {e}", exc_info=True)
            return None

    def evaluate_anchor_indicator(self, strategy: Dict, analysis: Dict) -> Optional[Dict]:
        """
        Evaluate the anchor (primary) indicator and determine if signal triggered.

        Args:
            strategy: Strategy configuration
            analysis: Comprehensive analysis results

        Returns:
            Dict with signal_type, base_confidence, reasoning, or None
        """
        anchor_indicator = strategy["anchor_indicator"]
        anchor_config = strategy.get("anchor_config", {})
        buy_conditions = strategy.get("buy_conditions", {})
        sell_conditions = strategy.get("sell_conditions", {})

        try:
            # Get indicator data from analysis
            indicator_data = analysis.get(anchor_indicator)
            if not indicator_data or not indicator_data.get("success"):
                logger.warning(
                    f"Anchor indicator '{anchor_indicator}' not available or failed"
                )
                return None

            # Check buy conditions
            if self._check_conditions(buy_conditions, indicator_data, analysis):
                return {
                    "signal_type": "BUY",
                    "base_confidence": 70.0,  # Base confidence for anchor
                    "reasoning": f"Anchor indicator {anchor_indicator} met BUY conditions",
                    "indicator": anchor_indicator,
                    "values": indicator_data,
                }

            # Check sell conditions
            if self._check_conditions(sell_conditions, indicator_data, analysis):
                return {
                    "signal_type": "SELL",
                    "base_confidence": 70.0,
                    "reasoning": f"Anchor indicator {anchor_indicator} met SELL conditions",
                    "indicator": anchor_indicator,
                    "values": indicator_data,
                }

            return {"signal_type": "HOLD", "reasoning": "No conditions met"}

        except Exception as e:
            logger.error(f"Error evaluating anchor indicator: {e}", exc_info=True)
            return None

    def evaluate_confirmations(self, strategy: Dict, analysis: Dict) -> Dict:
        """
        Evaluate all confirmation indicators.

        Args:
            strategy: Strategy configuration
            analysis: Comprehensive analysis results

        Returns:
            Dict with confirmation results
        """
        confirmation_configs = strategy.get("confirmation_indicators", [])
        if not confirmation_configs:
            return {
                "all_confirmed": True,
                "confirmed_count": 0,
                "total_count": 0,
                "required_met": True,
                "details": [],
            }

        confirmed = []
        required_met = True
        total_count = len(confirmation_configs)

        for conf in confirmation_configs:
            indicator = conf["indicator"]
            required = conf.get("required", False)
            conditions = conf.get("conditions", {})
            weight = conf.get("weight", 10)

            # Get indicator data
            indicator_key = indicator
            if indicator == "moving_average":
                indicator_key = "moving_average"
            elif indicator == "bollinger_bands":
                indicator_key = "bollinger_bands"

            indicator_data = analysis.get(indicator_key)
            if not indicator_data or not indicator_data.get("success"):
                if required:
                    required_met = False
                confirmed.append(
                    {
                        "indicator": indicator,
                        "met": False,
                        "required": required,
                        "reason": "Indicator data not available",
                        "weight": weight,
                    }
                )
                continue

            # Check conditions
            conditions_met = self._check_conditions(conditions, indicator_data, analysis)

            if not conditions_met and required:
                required_met = False

            confirmed.append(
                {
                    "indicator": indicator,
                    "met": conditions_met,
                    "required": required,
                    "reason": "Conditions met" if conditions_met else "Conditions not met",
                    "weight": weight,
                }
            )

        confirmed_count = sum(1 for c in confirmed if c["met"])

        return {
            "all_confirmed": confirmed_count == total_count,
            "confirmed_count": confirmed_count,
            "total_count": total_count,
            "required_met": required_met,
            "details": confirmed,
        }

    def _check_conditions(
        self, conditions: Dict, indicator_data: Dict, analysis: Dict
    ) -> bool:
        """
        Check if all conditions in a condition dict are met.

        Args:
            conditions: Conditions dict from strategy
            indicator_data: Data for the specific indicator
            analysis: Full analysis for cross-indicator checks

        Returns:
            True if all conditions met, False otherwise
        """
        if not conditions:
            return True

        for field, condition in conditions.items():
            if not self._check_single_condition(field, condition, indicator_data, analysis):
                return False

        return True

    def _check_single_condition(
        self, field: str, condition: Dict, indicator_data: Dict, analysis: Dict
    ) -> bool:
        """
        Check a single condition.

        Args:
            field: Field name to check
            condition: Condition specification
            indicator_data: Indicator data
            analysis: Full analysis

        Returns:
            True if condition met
        """
        operator = condition.get("operator")
        value = condition.get("value")
        equals = condition.get("equals")
        not_equals = condition.get("not_equals")
        reference = condition.get("reference")

        # Get the actual value from indicator data
        actual_value = indicator_data.get(field)

        # Handle nested fields (e.g., trend.direction)
        if actual_value is None and "." in field:
            parts = field.split(".")
            actual_value = indicator_data
            for part in parts:
                if isinstance(actual_value, dict):
                    actual_value = actual_value.get(part)
                else:
                    actual_value = None
                    break

        if actual_value is None:
            return False

        # Equality checks
        if equals is not None:
            return actual_value == equals

        if not_equals is not None:
            return actual_value != not_equals

        # Numeric operator checks
        if operator and value is not None:
            try:
                if operator == "<=":
                    return float(actual_value) <= float(value)
                elif operator == "<":
                    return float(actual_value) < float(value)
                elif operator == ">=":
                    return float(actual_value) >= float(value)
                elif operator == ">":
                    return float(actual_value) > float(value)
                elif operator == "==":
                    return float(actual_value) == float(value)
                elif operator == "!=":
                    return float(actual_value) != float(value)
            except (ValueError, TypeError):
                return False

        # Reference checks (compare to another indicator value)
        if reference:
            ref_value = indicator_data.get(reference)
            if ref_value is not None:
                try:
                    if operator == ">":
                        return float(actual_value) > float(ref_value)
                    elif operator == "<":
                        return float(actual_value) < float(ref_value)
                except (ValueError, TypeError):
                    return False

        return True

    def calculate_confidence_score(
        self, anchor_signal: Dict, confirmations: Dict, strategy: Dict
    ) -> float:
        """
        Calculate overall confidence score for the signal.

        Args:
            anchor_signal: Anchor indicator result
            confirmations: Confirmation results
            strategy: Strategy configuration

        Returns:
            Confidence score (0-100)
        """
        # Start with anchor base confidence
        confidence = anchor_signal.get("base_confidence", 70.0)

        # Check if all required confirmations met
        if not confirmations.get("required_met", True):
            # Significantly reduce confidence if required confirmations not met
            confidence -= 25.0

        # Add points for each confirmation met (weighted)
        for detail in confirmations.get("details", []):
            if detail["met"]:
                weight = detail.get("weight", 10)
                confidence += weight * 0.5  # Scale weight contribution
            elif detail["required"]:
                # Already handled above, but emphasize
                pass
            else:
                # Optional confirmation not met - small penalty
                confidence -= 2.0

        # Cap between 0 and 100
        confidence = max(0.0, min(100.0, confidence))

        return confidence

    def _get_current_price(self, ticker_id: int) -> Optional[float]:
        """Get current price for a ticker."""
        try:
            ticker_data = self.ticker_dao.get_ticker_data(ticker_id)
            if ticker_data and ticker_data.get("last_price"):
                return float(ticker_data["last_price"])
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
        return None

    def _build_indicator_snapshot(
        self, analysis: Dict, anchor_signal: Dict, confirmations: Dict
    ) -> Dict:
        """Build snapshot of all indicator values at signal time."""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "anchor": {
                "indicator": anchor_signal.get("indicator"),
                "signal_type": anchor_signal.get("signal_type"),
                "values": anchor_signal.get("values", {}),
            },
            "confirmations": confirmations.get("details", []),
            "all_indicators": {},
        }

        # Include all available indicator data
        for key, value in analysis.items():
            if isinstance(value, dict) and value.get("success"):
                # Store only the essential data, not error messages
                snapshot["all_indicators"][key] = {
                    k: v for k, v in value.items() if k != "error"
                }

        return snapshot

    def _calculate_expiration_date(self, strategy: Dict) -> Optional[datetime]:
        """Calculate signal expiration date based on strategy config."""
        expiration_days = self.config.config.get("trading_strategies", {}).get(
            "signal_expiration_days", 7
        )
        return datetime.now() + timedelta(days=expiration_days)

    def save_signal(self, signal: Dict) -> Optional[int]:
        """
        Save a generated signal to the database.

        Args:
            signal: Signal dict from evaluate_strategy()

        Returns:
            Signal ID if saved successfully, None otherwise
        """
        try:
            signal_id = self.signal_dao.save_signal(
                strategy_id=signal["strategy_id"],
                ticker_id=signal["ticker_id"],
                signal_type=signal["signal_type"],
                signal_strength=signal["signal_strength"],
                confidence_score=signal["confidence_score"],
                indicator_snapshot=signal["indicator_snapshot"],
                price_at_signal=signal["price_at_signal"],
                portfolio_id=signal.get("portfolio_id"),
                signal_date=signal.get("signal_date"),
                expires_date=signal.get("expires_date"),
            )

            if signal_id:
                logger.info(f"Saved signal {signal_id} for {signal['symbol']}")

                # Optionally create AI recommendation
                if self._should_create_ai_recommendation(signal):
                    self._create_ai_recommendation(signal, signal_id)

            return signal_id

        except Exception as e:
            logger.error(f"Error saving signal: {e}", exc_info=True)
            return None

    def _should_create_ai_recommendation(self, signal: Dict) -> bool:
        """Check if signal should be converted to AI recommendation."""
        if not self.config.config.get("trading_strategies", {}).get(
            "auto_create_ai_recommendation", True
        ):
            return False

        min_confidence = self.config.config.get("trading_strategies", {}).get(
            "ai_recommendation_min_confidence", 75.0
        )

        return signal["confidence_score"] >= min_confidence

    def _create_ai_recommendation(self, signal: Dict, signal_id: int) -> Optional[int]:
        """Create AI recommendation from signal."""
        try:
            # Build reasoning text
            reasoning = f"Trading Strategy '{signal['strategy_name']}' generated {signal['signal_type']} signal.\n\n"
            reasoning += f"{signal.get('reasoning', '')}\n\n"
            reasoning += f"Confidence Score: {signal['confidence_score']:.1f}%\n"
            reasoning += f"Signal Strength: {signal['signal_strength']}"

            # Create recommendation (if AI recommendations module is available)
            if self.ai_rec_dao:
                rec_id = self.ai_rec_dao.save_recommendation(
                    portfolio_id=signal.get("portfolio_id"),
                    ticker_symbol=signal["symbol"],
                    recommendation_type=signal["signal_type"],
                    recommended_price=signal["price_at_signal"],
                    confidence_score=signal["confidence_score"],
                    reasoning=reasoning,
                    technical_indicators=signal["indicator_snapshot"],
                    sentiment_score=signal["indicator_snapshot"]
                    .get("all_indicators", {})
                    .get("news_sentiment", {})
                    .get("average_sentiment"),
                    recommendation_date=signal.get("signal_date"),
                    expires_date=signal.get("expires_date"),
                )

                if rec_id:
                    # Link signal to recommendation
                    self.signal_dao.link_signal_to_recommendation(signal_id, rec_id)
                logger.info(
                    f"Created AI recommendation {rec_id} from signal {signal_id}"
                )

            return rec_id

        except Exception as e:
            logger.error(f"Error creating AI recommendation: {e}", exc_info=True)
            return None

    def batch_evaluate_portfolio(
        self, portfolio_id: int, strategy_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Evaluate all active strategies for all tickers in a portfolio.

        Args:
            portfolio_id: Portfolio ID
            strategy_ids: Optional list of specific strategy IDs to evaluate

        Returns:
            List of generated signals
        """
        signals = []

        try:
            # Get tickers in portfolio
            tickers = self.portfolio_dao.get_tickers_in_portfolio(portfolio_id)
            if not tickers:
                logger.warning(f"No tickers found in portfolio {portfolio_id}")
                return signals

            # Get strategies to evaluate
            if strategy_ids:
                strategies = [
                    self.strategy_dao.get_strategy(sid) for sid in strategy_ids
                ]
                strategies = [s for s in strategies if s]  # Filter None
            else:
                strategies = self.strategy_dao.get_active_strategies(
                    portfolio_id=portfolio_id
                )

            if not strategies:
                logger.warning(f"No active strategies found for portfolio {portfolio_id}")
                return signals

            logger.info(
                f"Evaluating {len(strategies)} strategies for {len(tickers)} tickers"
            )

            # Evaluate each strategy against each ticker
            for strategy in strategies:
                for ticker_symbol, _ in tickers:
                    try:
                        ticker_id = self.ticker_dao.get_ticker_id(ticker_symbol)
                        if not ticker_id:
                            continue

                        # Check for duplicate signals
                        if self.signal_dao.check_duplicate_signal(
                            strategy["id"], ticker_id, datetime.now()
                        ):
                            logger.debug(
                                f"Skipping duplicate signal for {ticker_symbol}"
                            )
                            continue

                        # Evaluate strategy
                        signal = self.evaluate_strategy(
                            strategy, ticker_id, ticker_symbol, portfolio_id
                        )

                        if signal:
                            # Save signal
                            signal_id = self.save_signal(signal)
                            if signal_id:
                                signal["id"] = signal_id
                                signals.append(signal)

                    except Exception as e:
                        logger.error(
                            f"Error evaluating {ticker_symbol}: {e}", exc_info=True
                        )
                        continue

            logger.info(f"Generated {len(signals)} signals for portfolio {portfolio_id}")

        except Exception as e:
            logger.error(f"Error in batch evaluation: {e}", exc_info=True)

        return signals

    def batch_evaluate_watchlist(
        self, watch_list_id: int, strategy_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Evaluate all active strategies for all tickers in a watchlist.

        Args:
            watch_list_id: Watchlist ID
            strategy_ids: Optional list of specific strategy IDs

        Returns:
            List of generated signals
        """
        signals = []

        try:
            # Import here to avoid circular dependency
            from .watch_list_dao import WatchListDao

            watchlist_dao = WatchListDao(self.pool)

            # Get tickers in watchlist
            tickers = watchlist_dao.get_watch_list_tickers(watch_list_id)
            if not tickers:
                logger.warning(f"No tickers found in watchlist {watch_list_id}")
                return signals

            # Get strategies
            if strategy_ids:
                strategies = [
                    self.strategy_dao.get_strategy(sid) for sid in strategy_ids
                ]
                strategies = [s for s in strategies if s]
            else:
                strategies = self.strategy_dao.get_active_strategies(
                    watch_list_id=watch_list_id
                )

            if not strategies:
                logger.warning(f"No active strategies found for watchlist {watch_list_id}")
                return signals

            logger.info(
                f"Evaluating {len(strategies)} strategies for {len(tickers)} watchlist tickers"
            )

            # Evaluate each strategy against each ticker
            for strategy in strategies:
                for ticker_data in tickers:
                    try:
                        ticker_id = ticker_data["ticker_id"]
                        ticker_symbol = ticker_data["ticker_symbol"]

                        # Check for duplicates
                        if self.signal_dao.check_duplicate_signal(
                            strategy["id"], ticker_id, datetime.now()
                        ):
                            continue

                        # Evaluate
                        signal = self.evaluate_strategy(
                            strategy, ticker_id, ticker_symbol, portfolio_id=None
                        )

                        if signal:
                            signal_id = self.save_signal(signal)
                            if signal_id:
                                signal["id"] = signal_id
                                signals.append(signal)

                    except Exception as e:
                        logger.error(
                            f"Error evaluating ticker {ticker_data.get('ticker_symbol')}: {e}",
                            exc_info=True,
                        )
                        continue

            logger.info(f"Generated {len(signals)} signals for watchlist {watch_list_id}")

        except Exception as e:
            logger.error(f"Error in watchlist batch evaluation: {e}", exc_info=True)

        return signals

    def batch_evaluate_all_strategies(self) -> List[Dict]:
        """
        Evaluate all active global strategies across all portfolios.

        This method is useful for automated signal generation after data updates.
        It evaluates:
        - Global strategies (portfolio_id=NULL, watch_list_id=NULL)
        - Portfolio-specific strategies for all portfolios
        - Watchlist-specific strategies for all watchlists

        Returns:
            List of all generated signals
        """
        all_signals = []

        try:
            logger.info("Starting batch evaluation for all active strategies")

            # Get all active strategies
            all_strategies = self.strategy_dao.get_all_strategies(include_inactive=False)

            if not all_strategies:
                logger.warning("No active strategies found")
                return all_signals

            logger.info(f"Found {len(all_strategies)} active strategies")

            # Group strategies by scope
            global_strategies = []
            portfolio_strategies = {}
            watchlist_strategies = {}

            for strategy in all_strategies:
                if strategy.get("portfolio_id"):
                    # Portfolio-specific strategy
                    pid = strategy["portfolio_id"]
                    if pid not in portfolio_strategies:
                        portfolio_strategies[pid] = []
                    portfolio_strategies[pid].append(strategy["id"])
                elif strategy.get("watch_list_id"):
                    # Watchlist-specific strategy
                    wid = strategy["watch_list_id"]
                    if wid not in watchlist_strategies:
                        watchlist_strategies[wid] = []
                    watchlist_strategies[wid].append(strategy["id"])
                else:
                    # Global strategy - applies to all portfolios
                    global_strategies.append(strategy)

            # Evaluate global strategies for all portfolios
            if global_strategies:
                logger.info(f"Evaluating {len(global_strategies)} global strategies")
                portfolios = self.portfolio_dao.get_portfolio_list()

                for portfolio in portfolios:
                    if portfolio.get("status") != "Active":
                        continue

                    portfolio_id = portfolio["id"]
                    logger.info(f"Evaluating global strategies for portfolio {portfolio_id}")

                    signals = self.batch_evaluate_portfolio(
                        portfolio_id,
                        strategy_ids=[s["id"] for s in global_strategies]
                    )
                    all_signals.extend(signals)

            # Evaluate portfolio-specific strategies
            for portfolio_id, strategy_ids in portfolio_strategies.items():
                logger.info(
                    f"Evaluating {len(strategy_ids)} portfolio-specific "
                    f"strategies for portfolio {portfolio_id}"
                )
                signals = self.batch_evaluate_portfolio(portfolio_id, strategy_ids)
                all_signals.extend(signals)

            # Evaluate watchlist-specific strategies
            for watchlist_id, strategy_ids in watchlist_strategies.items():
                logger.info(
                    f"Evaluating {len(strategy_ids)} watchlist-specific "
                    f"strategies for watchlist {watchlist_id}"
                )
                signals = self.batch_evaluate_watchlist(watchlist_id, strategy_ids)
                all_signals.extend(signals)

            logger.info(
                f"Batch evaluation complete. Generated {len(all_signals)} total signals"
            )

        except Exception as e:
            logger.error(f"Error in batch_evaluate_all_strategies: {e}", exc_info=True)

        return all_signals
