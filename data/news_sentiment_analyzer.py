from datetime import datetime

import yfinance as yf
from transformers import pipeline

from data.news_sentiment_dao import NewsSentimentDAO


class NewsSentimentAnalyzer:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.sentiment_dao = NewsSentimentDAO(db_user, db_password, db_host, db_name)
        self.sentiment_dao.open_connection()

        # Initialize FinBERT model
        print("Loading FinBERT model...")
        self.nlp = pipeline(
            "sentiment-analysis", model="ProsusAI/finbert", return_all_scores=True
        )
        print("FinBERT model loaded")

    def close_connection(self):
        """Closes the database connection"""
        self.sentiment_dao.close_connection()

    def analyze_sentiment(self, text):
        """
        Analyzes sentiment of text using FinBERT
        Returns score between -1 and 1, and confidence
        """
        try:
            result = self.nlp(text)[0]

            # Convert FinBERT output to score and confidence
            scores = {item["label"]: item["score"] for item in result}

            # Calculate sentiment score (-1 to 1)
            sentiment_score = scores["positive"] - scores["negative"]

            # Calculate confidence (highest probability among classes)
            confidence = max(scores.values())

            return sentiment_score, confidence

        except Exception as e:
            print(f"Error analyzing sentiment: {str(e)}")
            return 0, 0

    def fetch_and_analyze_news(self, ticker_id, symbol):
        """
        Fetches news from yFinance and analyzes sentiment
        """
        try:
            # Get news from yFinance
            ticker = yf.Ticker(symbol)
            news_items = ticker.news

            if not news_items:
                print(f"No news found for {symbol}")
                # Save a "no news" entry to indicate we checked but found nothing
                self.sentiment_dao.save_sentiment(
                    ticker_id=ticker_id,
                    headline="No recent news available",
                    publisher="Yahoo Finance",
                    publish_date=datetime.now(),
                    sentiment_score=0,
                    confidence=0,
                    article_link=f"https://finance.yahoo.com/quote/{symbol}",
                )
                return

            print(f"\nNews items for {symbol}:")
            for item in news_items:
                print(f"News item fields: {item.keys()}")
                try:
                    content_dict = item["content"]

                    # Extract text from content dictionary
                    title = content_dict.get("title", "")
                    summary = content_dict.get("summary", "")
                    description = content_dict.get("description", "")

                    # Combine available text fields
                    text_parts = []
                    if title:
                        text_parts.append(title)
                    if summary:
                        text_parts.append(summary)
                    if description:
                        text_parts.append(description)

                    if not text_parts:
                        print(f"No news text found for {symbol}")
                        continue

                    # Combine all text parts with spaces
                    text = " ".join(text_parts)

                    # Truncate text to first 500 characters for sentiment analysis
                    # This ensures we stay within FinBERT's token limit while keeping the most relevant part
                    analysis_text = text[:500]

                    # Use first 100 characters as headline for display
                    headline = text[:100] + "..." if len(text) > 100 else text

                    # Analyze content sentiment using truncated text
                    sentiment_score, confidence = self.analyze_sentiment(analysis_text)

                    # Get publish time from content or use current time
                    try:
                        publish_time = datetime.strptime(
                            content_dict.get("pubDate", ""), "%Y-%m-%dT%H:%M:%SZ"
                        )
                    except:
                        publish_time = datetime.now()

                    # Get article URL from content or use quote page
                    article_url = None
                    try:
                        if isinstance(content_dict.get("clickThroughUrl"), dict):
                            article_url = content_dict["clickThroughUrl"].get("url")
                        if not article_url and isinstance(
                            content_dict.get("canonicalUrl"), dict
                        ):
                            article_url = content_dict["canonicalUrl"].get("url")
                    except:
                        pass

                    if not article_url:
                        article_url = f"https://finance.yahoo.com/quote/{symbol}"

                    # Save to database with publish time and article URL
                    self.sentiment_dao.save_sentiment(
                        ticker_id=ticker_id,
                        headline=headline,
                        publisher=content_dict.get("provider", {}).get(
                            "displayName", "Yahoo Finance"
                        ),
                        publish_date=publish_time,
                        sentiment_score=sentiment_score,
                        confidence=confidence,
                        article_link=article_url,
                    )
                    print(f"Processed news item: {headline}")
                except Exception as e:
                    print(f"Error processing news item for {symbol}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error processing news for {symbol}: {str(e)}")

    def get_sentiment_summary(self, ticker_id, symbol):
        """
        Gets a summary of sentiment analysis for a ticker
        """
        try:
            # Get latest sentiment data
            sentiment_data = self.sentiment_dao.get_latest_sentiment(ticker_id)

            if not sentiment_data:
                return {
                    "symbol": symbol,
                    "status": "No sentiment data available",
                    "articles": [],
                }

            # Check if we only have a "no news" entry
            if (
                len(sentiment_data) == 1
                and sentiment_data[0]["headline"] == "No recent news available"
            ):
                return {
                    "symbol": symbol,
                    "status": "No recent news",
                    "average_sentiment": 0,
                    "article_count": 0,
                    "articles": [],
                }

            # Calculate average sentiment
            total_sentiment = 0
            weighted_total = 0
            total_weight = 0

            articles = []
            for item in sentiment_data:
                weight = item["confidence"]
                weighted_total += item["sentiment_score"] * weight
                total_weight += weight

                articles.append(
                    {
                        "headline": item["headline"],
                        "publisher": item["publisher"],
                        "date": item["publish_date"].strftime("%Y-%m-%d %H:%M:%S"),
                        "sentiment": item["sentiment_score"],
                        "confidence": item["confidence"],
                        "link": item["article_link"],
                    }
                )

            avg_sentiment = weighted_total / total_weight if total_weight > 0 else 0

            # Determine sentiment status
            if avg_sentiment >= 0.5:
                status = "Very Positive"
            elif avg_sentiment >= 0.1:
                status = "Positive"
            elif avg_sentiment > -0.1:
                status = "Neutral"
            elif avg_sentiment > -0.5:
                status = "Negative"
            else:
                status = "Very Negative"

            return {
                "symbol": symbol,
                "status": status,
                "average_sentiment": avg_sentiment,
                "article_count": len(articles),
                "articles": articles,
            }

        except Exception as e:
            print(f"Error getting sentiment summary: {str(e)}")
            return None
