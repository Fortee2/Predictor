import yfinance as yf
from transformers import pipeline
from datetime import datetime
from data.news_sentiment_dao import NewsSentimentDAO

class NewsSentimentAnalyzer:
    def __init__(self, db_user, db_password, db_host, db_name):
        self.sentiment_dao = NewsSentimentDAO(db_user, db_password, db_host, db_name)
        self.sentiment_dao.open_connection()
        
        # Initialize FinBERT model
        print("Loading FinBERT model...")
        self.nlp = pipeline("sentiment-analysis", 
                          model="ProsusAI/finbert",
                          return_all_scores=True)
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
            scores = {item['label']: item['score'] for item in result}
            
            # Calculate sentiment score (-1 to 1)
            sentiment_score = (scores['positive'] - scores['negative'])
            
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
                return
            
            for item in news_items:
                # Analyze headline sentiment
                sentiment_score, confidence = self.analyze_sentiment(item['title'])
                
                # Save to database
                self.sentiment_dao.save_sentiment(
                    ticker_id=ticker_id,
                    headline=item['title'],
                    publisher=item.get('publisher', 'Unknown'),
                    publish_date=datetime.fromtimestamp(item['providerPublishTime']),
                    sentiment_score=sentiment_score,
                    confidence=confidence,
                    article_link=item['link']
                )
                
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
                    'symbol': symbol,
                    'status': 'No sentiment data available',
                    'articles': []
                }
            
            # Calculate average sentiment
            total_sentiment = 0
            weighted_total = 0
            total_weight = 0
            
            articles = []
            for item in sentiment_data:
                weight = item['confidence']
                weighted_total += item['sentiment_score'] * weight
                total_weight += weight
                
                articles.append({
                    'headline': item['headline'],
                    'publisher': item['publisher'],
                    'date': item['publish_date'].strftime('%Y-%m-%d %H:%M:%S'),
                    'sentiment': item['sentiment_score'],
                    'confidence': item['confidence'],
                    'link': item['article_link']
                })
            
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
                'symbol': symbol,
                'status': status,
                'average_sentiment': avg_sentiment,
                'article_count': len(articles),
                'articles': articles
            }
            
        except Exception as e:
            print(f"Error getting sentiment summary: {str(e)}")
            return None
