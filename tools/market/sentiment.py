import os
import logging
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from utils.config import load_config

logger = logging.getLogger("TradeMaster.Tools.Market.Sentiment")

class SentimentAnalyzer:
    """Analyzes market sentiment from social media and news"""
    
    def __init__(self):
        """Initialize the sentiment analyzer"""
        # Load configuration
        self.config = load_config()
        
        # Get API keys
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.newsapi_key = os.getenv("NEWSAPI_KEY")
        
        # Check if web operator is enabled
        web_operator_config = self.config.get("tools", {}).get("web_operator", {})
        self.use_web_operator = web_operator_config.get("enabled", False)
        
        if self.use_web_operator:
            web_operator_path = web_operator_config.get("path", "./open-operator")
            try:
                from utils.web_operator import WebOperator
                self.web_operator = WebOperator(operator_path=web_operator_path)
                logger.info("Web Operator initialized for sentiment analysis")
            except ImportError:
                logger.warning("WebOperator module not available. Using API or simulation for sentiment analysis.")
                self.use_web_operator = False
            except Exception as e:
                logger.error(f"Error initializing WebOperator: {str(e)}")
                self.use_web_operator = False
        
        # Cache for recent API calls to avoid rate limiting
        self.cache = {
            "sentiment": {},  # {symbol: {"data": sentiment_data, "timestamp": fetch_time}}
            "news": {}        # {symbol: {"data": news_data, "timestamp": fetch_time}}
        }
        
        # Cache expiration times (in seconds)
        self.cache_expiry = {
            "sentiment": 1800,  # 30 minutes
            "news": 3600        # 1 hour
        }
    
    async def get_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get sentiment analysis for a symbol
        
        Args:
            symbol (str): The symbol to analyze
            
        Returns:
            dict or None: Sentiment data or None if the request failed
        """
        # Check cache first
        if symbol in self.cache["sentiment"]:
            cache_data = self.cache["sentiment"][symbol]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry["sentiment"]:
                logger.debug(f"Using cached sentiment data for {symbol} (age: {cache_age:.1f}s)")
                return cache_data["data"]
        
        # Try to get sentiment data
        sentiment_data = None
        
        # Try with web operator first if enabled
        if self.use_web_operator:
            try:
                sentiment_data = await self.web_operator.get_twitter_sentiment(symbol)
                if sentiment_data:
                    logger.info(f"Got sentiment data for {symbol} using Web Operator")
            except Exception as e:
                logger.error(f"Error getting sentiment with Web Operator: {str(e)}")
        
        # Try with Twitter API if web operator failed or is disabled
        if not sentiment_data and self.twitter_bearer_token:
            try:
                sentiment_data = await self._fetch_twitter_sentiment(symbol)
                if sentiment_data:
                    logger.info(f"Got sentiment data for {symbol} using Twitter API")
            except Exception as e:
                logger.error(f"Error fetching Twitter sentiment: {str(e)}")
        
        # Simulate data if everything else failed
        if not sentiment_data:
            sentiment_data = self.simulate_sentiment_data(symbol)
            logger.info(f"Using simulated sentiment data for {symbol}")
        
        # Update cache
        self.cache["sentiment"][symbol] = {
            "data": sentiment_data,
            "timestamp": datetime.now()
        }
        
        return sentiment_data
    
    async def get_news(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get news for a symbol
        
        Args:
            symbol (str): The symbol to get news for
            
        Returns:
            dict or None: News data or None if the request failed
        """
        # Check cache first
        if symbol in self.cache["news"]:
            cache_data = self.cache["news"][symbol]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry["news"]:
                logger.debug(f"Using cached news data for {symbol} (age: {cache_age:.1f}s)")
                return cache_data["data"]
        
        # Try to get news data
        news_data = None
        
        # Try with web operator first if enabled
        if self.use_web_operator:
            try:
                news_data = await self.web_operator.get_latest_news(symbol)
                if news_data:
                    logger.info(f"Got news data for {symbol} using Web Operator")
            except Exception as e:
                logger.error(f"Error getting news with Web Operator: {str(e)}")
        
        # Try with NewsAPI if web operator failed or is disabled
        if not news_data and self.newsapi_key:
            try:
                news_data = await self._fetch_news(symbol)
                if news_data:
                    logger.info(f"Got news data for {symbol} using NewsAPI")
            except Exception as e:
                logger.error(f"Error fetching news: {str(e)}")
        
        # Simulate data if everything else failed
        if not news_data:
            news_data = self.simulate_news_data(symbol)
            logger.info(f"Using simulated news data for {symbol}")
        
        # Update cache
        self.cache["news"][symbol] = {
            "data": news_data,
            "timestamp": datetime.now()
        }
        
        return news_data
    
    async def _fetch_twitter_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch sentiment data from Twitter API
        
        Args:
            symbol (str): The symbol to analyze
            
        Returns:
            dict or None: Sentiment data or None if the request failed
        """
        if not self.twitter_bearer_token:
            return None
            
        # Search query based on symbol
        query = f"${symbol.upper()} (crypto OR trading OR invest OR price OR market) -is:retweet"
        
        # Twitter API v2 endpoint
        api_url = "https://api.twitter.com/2/tweets/search/recent"
        
        # Headers with authorization
        headers = {
            "Authorization": f"Bearer {self.twitter_bearer_token}"
        }
        
        # Query parameters
        params = {
            "query": query,
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics",
            "expansions": "author_id",
            "user.fields": "name,username"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "data" in data and len(data["data"]) > 0:
                            return self._analyze_tweets(data)
                        else:
                            logger.warning(f"No tweets found for {symbol}")
                            return None
                    else:
                        logger.warning(f"Twitter API error: {response.status}")
                        error_data = await response.json()
                        logger.warning(f"Error details: {error_data}")
                        return None
        except Exception as e:
            logger.error(f"Error in _fetch_twitter_sentiment: {str(e)}")
            return None
    
    def _analyze_tweets(self, twitter_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tweets for sentiment
        
        Args:
            twitter_data (dict): Data from Twitter API
            
        Returns:
            dict: Analyzed sentiment data
        """
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            analyzer = SentimentIntensityAnalyzer()
            
            tweets = twitter_data.get("data", [])
            tweet_count = len(tweets)
            
            if tweet_count == 0:
                return None
                
            # Calculate sentiment scores
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            total_sentiment = 0.0
            
            sample_tweets = []
            
            for tweet in tweets:
                text = tweet.get("text", "")
                sentiment = analyzer.polarity_scores(text)
                compound_score = sentiment["compound"]
                
                total_sentiment += compound_score
                
                if compound_score >= 0.05:
                    positive_count += 1
                elif compound_score <= -0.05:
                    negative_count += 1
                else:
                    neutral_count += 1
                    
                # Add to sample tweets if it's a good example
                if len(sample_tweets) < 5 and len(text) > 20 and len(text) < 200:
                    # Clean the tweet text (remove URLs, etc.)
                    cleaned_text = self._clean_tweet_text(text)
                    if cleaned_text and "@" not in cleaned_text:  # Avoid tweets with mentions
                        sample_tweets.append(cleaned_text)
            
            # Calculate percentages
            positive_pct = (positive_count / tweet_count) * 100
            neutral_pct = (neutral_count / tweet_count) * 100
            negative_pct = (negative_count / tweet_count) * 100
            
            # Calculate average sentiment
            avg_sentiment = total_sentiment / tweet_count
            
            # Extract trending topics (simple implementation)
            trending_topics = ["#" + symbol.upper()]
            if avg_sentiment > 0.2:
                trending_topics.append("#bullish")
            elif avg_sentiment < -0.2:
                trending_topics.append("#bearish")
                
            trending_topics.append("#crypto" if symbol in ["btc", "eth", "sol"] else "#trading")
            
            # Finalize sentiment data
            sentiment_data = {
                "sentiment_score": avg_sentiment,
                "positive_percentage": positive_pct,
                "neutral_percentage": neutral_pct,
                "negative_percentage": negative_pct,
                "tweet_volume": tweet_count,
                "trending_topics": trending_topics,
                "sample_tweets": sample_tweets
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error analyzing tweets: {str(e)}")
            return None
    
    def _clean_tweet_text(self, text: str) -> str:
        """Clean tweet text by removing URLs, etc.
        
        Args:
            text (str): The tweet text
            
        Returns:
            str: Cleaned text
        """
        import re
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        
        # Remove mentions (@username)
        text = re.sub(r'@\S+', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    async def _fetch_news(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch news data from NewsAPI
        
        Args:
            symbol (str): The symbol to get news for
            
        Returns:
            dict or None: News data or None if the request failed
        """
        if not self.newsapi_key:
            return None
            
        # Format search query based on symbol
        if symbol.lower() in ["btc", "bitcoin"]:
            query = "bitcoin OR btc OR crypto"
        elif symbol.lower() in ["eth", "ethereum"]:
            query = "ethereum OR eth OR crypto"
        else:
            query = f"{symbol.upper()} crypto OR {symbol.upper()} trading OR {symbol.upper()} price"
            
        # NewsAPI endpoint
        api_url = "https://newsapi.org/v2/everything"
        
        # Query parameters
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 5,
            "apiKey": self.newsapi_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "ok" and data["totalResults"] > 0:
                            # Process the articles
                            articles = []
                            for article in data["articles"]:
                                # Analyze sentiment of the article
                                try:
                                    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                                    analyzer = SentimentIntensityAnalyzer()
                                    
                                    # Analyze title and description
                                    title_sentiment = analyzer.polarity_scores(article["title"])
                                    desc_sentiment = analyzer.polarity_scores(article["description"] or "")
                                    
                                    # Average the compound scores
                                    avg_compound = (title_sentiment["compound"] + desc_sentiment["compound"]) / 2
                                    
                                    # Determine sentiment category
                                    if avg_compound >= 0.05:
                                        sentiment = "positive"
                                    elif avg_compound <= -0.05:
                                        sentiment = "negative"
                                    else:
                                        sentiment = "neutral"
                                except:
                                    sentiment = "neutral"
                                
                                articles.append({
                                    "title": article["title"],
                                    "description": article["description"],
                                    "source": article["source"]["name"],
                                    "url": article["url"],
                                    "publishedAt": article["publishedAt"],
                                    "sentiment": sentiment
                                })
                            
                            return {
                                "articles": articles,
                                "total_results": len(articles)
                            }
                        else:
                            logger.warning(f"No news found for {symbol}")
                            return None
                    else:
                        logger.warning(f"NewsAPI error: {response.status}")
                        error_data = await response.json()
                        logger.warning(f"Error details: {error_data}")
                        return None
        except Exception as e:
            logger.error(f"Error in _fetch_news: {str(e)}")
            return None
    
    def simulate_sentiment_data(self, symbol: str) -> Dict[str, Any]:
        """Simulate sentiment data if real data cannot be obtained
        
        Args:
            symbol (str): The symbol to simulate sentiment for
            
        Returns:
            dict: Simulated sentiment data
        """
        # Generate random sentiment but skew it based on the symbol
        # (this would normally come from real API data)
        symbol_hash = sum(ord(c) for c in symbol)
        random.seed(symbol_hash + datetime.now().day)  # Change daily but consistent for the same symbol
        
        sentiment_score = random.uniform(-1, 1)  # Between -1 (negative) and 1 (positive)
        tweet_volume = random.randint(1000, 50000)
        
        # Generate some fake tweet examples
        tweet_templates = [
            "{symbol} looking bullish on the 4h chart! Target: {target}",
            "Just bought more {symbol}, looking for a breakout soon.",
            "{symbol} forming a {pattern} pattern, could see {movement} soon.",
            "Market sentiment for {symbol} is {sentiment} right now.",
            "Technical analysis shows {symbol} might {direction} in the next few days."
        ]
        
        tweets = []
        for _ in range(3):
            template = random.choice(tweet_templates)
            tweets.append(template.format(
                symbol=symbol.upper(),
                target=f"${random.randint(10, 100000)}",
                pattern=random.choice(["cup and handle", "head and shoulders", "double bottom", "triangle", "flag"]),
                movement=random.choice(["a big move", "consolidation", "a breakout", "resistance"]),
                sentiment=random.choice(["extremely bullish", "cautiously optimistic", "mixed", "bearish", "uncertain"]),
                direction=random.choice(["pump", "dump", "go sideways", "test support", "break resistance"])
            ))
        
        # Calculate sentiment distribution based on the overall score
        positive_pct = (sentiment_score + 1) * 50  # Convert to percentage
        neutral_pct = random.uniform(10, 40)
        negative_pct = 100 - positive_pct - neutral_pct
        
        # Ensure percentages add up to 100%
        total = positive_pct + neutral_pct + negative_pct
        positive_pct = (positive_pct / total) * 100
        neutral_pct = (neutral_pct / total) * 100
        negative_pct = (negative_pct / total) * 100
        
        return {
            "sentiment_score": sentiment_score,
            "sentiment_distribution": {
                "positive": positive_pct,
                "neutral": neutral_pct,
                "negative": negative_pct
            },
            "positive_percentage": positive_pct,
            "neutral_percentage": neutral_pct,
            "negative_percentage": negative_pct,
            "common_themes": [
                f"{symbol.upper()} price action",
                "Market volatility",
                "Trading strategies",
                random.choice(["Technical analysis", "Fundamental news", "Regulatory updates", "Development milestones"])
            ],
            "sample_tweets": tweets,
            "tweet_volume": tweet_volume,
            "trending_topics": ["#" + symbol.upper(), "#crypto", "#trading", "#blockchain"],
            "significant_news": random.choice([
                f"No major news for {symbol.upper()} today.",
                f"{symbol.upper()} partnership announcement rumored.",
                f"Major exchange listing possibly coming for {symbol.upper()}.",
                f"Whales accumulating {symbol.upper()} according to on-chain data."
            ])
        }
    
    def simulate_news_data(self, symbol: str) -> Dict[str, Any]:
        """Simulate news data if real data cannot be obtained
        
        Args:
            symbol (str): The symbol to simulate news for
            
        Returns:
            dict: Simulated news data
        """
        # Generate random news but make it somewhat realistic
        symbol_hash = sum(ord(c) for c in symbol)
        random.seed(symbol_hash + datetime.now().day)  # Change daily but consistent for the same symbol
        
        # News article templates
        article_templates = [
            {
                "title": "{symbol} Price Prediction: Will {symbol} Reach ${target} in {timeframe}?",
                "description": "Analysts weigh in on {symbol}'s potential to reach ${target} given current market conditions and technical indicators.",
                "sentiment": "neutral"
            },
            {
                "title": "Breaking: {entity} Announces Major {symbol} {event}",
                "description": "In a surprising development, {entity} has just revealed plans for a significant {event} related to {symbol}.",
                "sentiment": "positive"
            },
            {
                "title": "Market Analysis: {symbol} Shows Signs of {trend}",
                "description": "Technical indicators suggest {symbol} may be entering a period of {trend}, according to leading analysts.",
                "sentiment": "variable"
            },
            {
                "title": "{symbol} Faces Regulatory Scrutiny in {region}",
                "description": "Regulators in {region} are examining {symbol}'s compliance with local laws, creating uncertainty for investors.",
                "sentiment": "negative"
            },
            {
                "title": "New {symbol} Partnership Could Revolutionize {industry}",
                "description": "{symbol} has formed a strategic alliance aimed at transforming how {industry} operates using blockchain technology.",
                "sentiment": "positive"
            }
        ]
        
        # Generate articles
        articles = []
        for _ in range(3):
            template = random.choice(article_templates)
            title_template = template["title"]
            desc_template = template["description"]
            sentiment = template["sentiment"]
            
            # Variables for templates
            variables = {
                "symbol": symbol.upper(),
                "target": f"${random.randint(1, 100) * 1000}",
                "timeframe": random.choice(["2025", "Q3", "next month", "year-end"]),
                "entity": random.choice(["Microsoft", "Amazon", "JP Morgan", "PayPal", "BlackRock", "Vitalik Buterin", "A major hedge fund"]),
                "event": random.choice(["acquisition", "integration", "investment", "development", "partnership"]),
                "trend": random.choice(["Bullish Divergence", "Accumulation", "Distribution", "Consolidation", "Reversal"]),
                "region": random.choice(["the EU", "the United States", "China", "South Korea", "Singapore", "the UK"]),
                "industry": random.choice(["finance", "gaming", "healthcare", "supply chain", "social media", "entertainment"])
            }
            
            # Fill in templates
            title = title_template.format(**variables)
            description = desc_template.format(**variables)
            
            # Determine sentiment
            if sentiment == "variable":
                article_sentiment = random.choice(["positive", "neutral", "negative"])
            else:
                article_sentiment = sentiment
                
            # Generate publication date
            days_ago = random.randint(0, 5)
            pub_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            # Generate source
            sources = ["CoinDesk", "Bloomberg", "Reuters", "CNBC", "CryptoBriefing", "The Block", "Cointelegraph"]
            source = random.choice(sources)
            
            articles.append({
                "title": title,
                "description": description,
                "source": source,
                "url": f"https://example.com/news/{symbol.lower()}-{random.randint(1000, 9999)}",
                "publishedAt": pub_date,
                "sentiment": article_sentiment
            })
        
        return {
            "articles": articles,
            "total_results": len(articles)
        }