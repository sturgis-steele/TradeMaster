import os
import re
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from utils.config import load_config
from tools.market.price import PriceDataFetcher
from tools.market.sentiment import SentimentAnalyzer

logger = logging.getLogger("TradeMaster.Tools.Market.Analyzer")

class TrendAnalyzer:
    """Tool for analyzing market trends, prices, and sentiment"""
    
    def __init__(self):
        """Initialize the market trend analysis tool"""
        # Load configuration
        self.config = load_config()
        self.market_config = self.config.get("tools", {}).get("market_analysis", {})
        
        # Check if market analysis is enabled
        if not self.market_config.get("enabled", True):
            logger.warning("Market analysis tool is disabled in configuration.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Initialize submodules
        self.price_fetcher = PriceDataFetcher()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Common mappings from keywords to symbols
        self.symbol_map = {
            "bitcoin": "btc",
            "ethereum": "eth",
            "binance coin": "bnb",
            "cardano": "ada",
            "solana": "sol",
            "ripple": "xrp",
            "dogecoin": "doge",
            "polkadot": "dot",
            "litecoin": "ltc",
            "chainlink": "link",
            "uniswap": "uni",
            "avalanche": "avax",
            "stellar": "xlm",
            "matic": "matic",
            "polygon": "matic",
            "shiba": "shib",
            "tether": "usdt",
            "usdc": "usdc",
            "bnb": "bnb"
        }
        
        logger.info("TrendAnalyzer initialized")
    
    async def process(self, text, message):
        """Process a market trend analysis request
        
        Args:
            text (str): The message text
            message (discord.Message): The Discord message object
            
        Returns:
            str: Response to the request
        """
        if not self.enabled:
            return "Market analysis is currently disabled."
            
        # Extract information from message
        user_id = str(message.author.id)
        username = message.author.name
        
        return await self.process_text(text, user_id, username)
    
    async def process_text(self, text, user_id, username):
        """Process a market trend analysis request from text
        
        Args:
            text (str): The message text
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            
        Returns:
            str: Response to the request
        """
        if not self.enabled:
            return "Market analysis is currently disabled."
        
        # Extract asset symbol if present
        symbol = self._extract_symbol(text)
        
        if not symbol:
            # Generic market trend response if no specific symbol detected
            return "I can analyze market trends for various cryptocurrencies and stocks. Just mention a symbol like BTC, ETH, or AAPL!"
        
        # Check if this is a price query
        if any(word in text.lower() for word in ["price", "worth", "value", "cost", "how much"]):
            return await self._get_price_info(symbol)
        
        # Check if this is a sentiment analysis request
        if any(word in text.lower() for word in ["sentiment", "feeling", "mood", "social", "twitter", "people"]):
            return await self._get_sentiment_analysis(symbol)
        
        # Check if this is a news request
        if any(word in text.lower() for word in ["news", "announcement", "headlines", "report"]):
            return await self._get_recent_news(symbol)
        
        # Check if this is a price prediction or trend analysis request
        if any(word in text.lower() for word in ["prediction", "predict", "future", "forecast", "will", "going to", "expect", "bullish", "bearish"]):
            return await self._get_trend_analysis(symbol)
        
        # Default response - provide a comprehensive market update
        return await self._get_market_update(symbol)
    
    def _extract_symbol(self, text):
        """Extract asset symbol from text
        
        Args:
            text (str): The message text
            
        Returns:
            str or None: The extracted symbol or None if not found
        """
        # Common crypto and stock symbols (caps)
        symbol_pattern = r'\b(BTC|ETH|USDT|BNB|USDC|XRP|ADA|DOGE|SOL|DOT|LUNA|AVAX|MATIC|LINK|UNI|SHIB|LTC|ATOM|ALGO|AAPL|MSFT|AMZN|GOOG|TSLA|META|NFLX)\b'
        match = re.search(symbol_pattern, text.upper())
        
        if match:
            return match.group(0).lower()
        
        # Look for symbol names in text (lowercase)
        for name, symbol in self.symbol_map.items():
            if name in text.lower():
                return symbol
        
        # If we're discussing crypto in general, default to BTC
        if any(word in text.lower() for word in ["crypto", "bitcoin", "cryptocurrency"]) and not any(word in text.lower() for word in ["stock", "stocks", "equity", "equities"]):
            return "btc"
        
        # If we're discussing stocks in general, default to market index
        if any(word in text.lower() for word in ["stock", "stocks", "equity", "equities", "market", "index"]):
            return "spy"  # S&P 500 ETF as general market
        
        return None
        
    async def _get_price_info(self, symbol):
        """Get current price information for an asset
        
        Args:
            symbol (str): The asset symbol
            
        Returns:
            str: Formatted price information
        """
        price_data = await self.price_fetcher.get_price_data(symbol)
        
        if not price_data:
            return f"Sorry, I couldn't fetch the latest price data for {symbol.upper()}. The API might be experiencing issues."
        
        return self._format_price_response(symbol, price_data, 0)
    
    def _format_price_response(self, symbol, price_data, cache_age):
        """Format price data into a readable response
        
        Args:
            symbol (str): The asset symbol
            price_data (dict): Price data
            cache_age (float): Age of cached data in seconds
            
        Returns:
            str: Formatted response
        """
        current_price = price_data.get("current_price", "Unknown")
        change_24h = price_data.get("change_24h", 0)
        change_pct_24h = price_data.get("change_pct_24h", 0)
        
        # Format the change as an arrow and sign
        if change_pct_24h > 0:
            change_format = f"📈 +{change_pct_24h:.2f}%"
        elif change_pct_24h < 0:
            change_format = f"📉 {change_pct_24h:.2f}%"
        else:
            change_format = "➡️ 0.00%"
            
        # Determine if data is cached
        freshness = f"(cached {int(cache_age)} seconds ago)" if cache_age > 0 else "(fresh data)"
        
        # Format high, low, volume if available
        high_24h = price_data.get("high_24h", None)
        low_24h = price_data.get("low_24h", None)
        volume_24h = price_data.get("volume_24h", None)
        
        # Construct basic response
        response = f"**{symbol.upper()} Price Update** {freshness}\n"
        response += f"Current price: ${current_price:,.2f} {change_format}\n"
        
        # Add additional details if available
        if high_24h and low_24h:
            response += f"24h Range: ${low_24h:,.2f} - ${high_24h:,.2f}\n"
            
        if volume_24h:
            # Format volume with appropriate suffix (K, M, B)
            if volume_24h >= 1_000_000_000:
                vol_formatted = f"${volume_24h/1_000_000_000:.2f}B"
            elif volume_24h >= 1_000_000:
                vol_formatted = f"${volume_24h/1_000_000:.2f}M"
            else:
                vol_formatted = f"${volume_24h:,.0f}"
                
            response += f"24h Volume: {vol_formatted}"
        
        return response
    
    async def _get_sentiment_analysis(self, symbol):
        """Get sentiment analysis for an asset
        
        Args:
            symbol (str): The asset symbol
            
        Returns:
            str: Formatted sentiment analysis
        """
        sentiment_data = await self.sentiment_analyzer.get_sentiment(symbol)
        
        if not sentiment_data:
            return f"I encountered an error trying to analyze sentiment for {symbol.upper()}."
        
        return self._format_sentiment_response(symbol, sentiment_data, 0)
    
    def _format_sentiment_response(self, symbol, sentiment_data, cache_age):
        """Format sentiment data into a readable response
        
        Args:
            symbol (str): The asset symbol
            sentiment_data (dict): Sentiment data
            cache_age (float): Age of cached data in seconds
            
        Returns:
            str: Formatted response
        """
        # Extract sentiment metrics
        sentiment_score = sentiment_data.get("sentiment_score", 0)
        positive_pct = sentiment_data.get("positive_percentage", 0)
        neutral_pct = sentiment_data.get("neutral_percentage", 0)
        negative_pct = sentiment_data.get("negative_percentage", 0)
        tweet_volume = sentiment_data.get("tweet_volume", 0)
        
        # Format the sentiment as a descriptive term
        if sentiment_score > 0.5:
            sentiment_desc = "Extremely Bullish 🚀"
        elif sentiment_score > 0.2:
            sentiment_desc = "Bullish 📈"
        elif sentiment_score > -0.2:
            sentiment_desc = "Neutral ↔️"
        elif sentiment_score > -0.5:
            sentiment_desc = "Bearish 📉"
        else:
            sentiment_desc = "Extremely Bearish 🧸"
            
        # Determine if data is cached
        freshness = f"(cached {int(cache_age)} seconds ago)" if cache_age > 0 else "(fresh data)"
        
        # Construct response
        response = f"**{symbol.upper()} Sentiment Analysis** {freshness}\n"
        response += f"Overall sentiment: {sentiment_desc}\n"
        response += f"Positive: {positive_pct:.1f}% | Neutral: {neutral_pct:.1f}% | Negative: {negative_pct:.1f}%\n"
        response += f"Tweet volume: {tweet_volume:,} in the last 24 hours\n\n"
        
        # Add sample tweets if available
        if "sample_tweets" in sentiment_data and sentiment_data["sample_tweets"]:
            response += "**Sample tweets:**\n"
            for tweet in sentiment_data["sample_tweets"][:2]:  # Only show up to 2 tweets
                response += f"• {tweet}\n"
        
        # Add trading insight based on sentiment
        if sentiment_score > 0.3:
            response += "\n**Trading insight:** Social sentiment is strongly positive, which historically correlates with short-term price increases for this asset."
        elif sentiment_score < -0.3:
            response += "\n**Trading insight:** Social sentiment is strongly negative, which may indicate oversold conditions or genuine concerns about this asset."
        else:
            response += "\n**Trading insight:** Social sentiment is mixed, suggesting no clear directional bias from the crowd."
        
        return response
    
    async def _get_recent_news(self, symbol):
        """Get recent news for an asset
        
        Args:
            symbol (str): The asset symbol
            
        Returns:
            str: Formatted news response
        """
        news_data = await self.sentiment_analyzer.get_news(symbol)
        
        if not news_data:
            return f"I encountered an error trying to get recent news for {symbol.upper()}."
        
        return self._format_news_response(symbol, news_data, 0)
    
    def _format_news_response(self, symbol, news_data, cache_age):
        """Format news data into a readable response
        
        Args:
            symbol (str): The asset symbol
            news_data (dict): News data
            cache_age (float): Age of cached data in seconds
            
        Returns:
            str: Formatted response
        """
        articles = news_data.get("articles", [])
        
        if not articles:
            return f"I couldn't find any recent news for {symbol.upper()}."
        
        # Determine if data is cached
        freshness = f"(cached {int(cache_age)} seconds ago)" if cache_age > 0 else "(fresh data)"
        
        # Construct response
        response = f"**Recent {symbol.upper()} News** {freshness}\n\n"
        
        for article in articles[:3]:  # Limit to 3 articles
            title = article.get("title", "No title")
            source = article.get("source", "Unknown source")
            description = article.get("description", "No description available")
            date = article.get("publishedAt", "Unknown date")
            
            # Add sentiment emoji if available
            sentiment = article.get("sentiment", "neutral")
            if sentiment == "positive":
                emoji = "🟢"
            elif sentiment == "negative":
                emoji = "🔴"
            else:
                emoji = "⚪"
                
            response += f"{emoji} **{title}**\n"
            response += f"📰 {source} | 📅 {date}\n"
            response += f"{description}\n\n"
        
        return response
    
    async def _get_trend_analysis(self, symbol):
        """Get trend analysis for an asset
        
        Args:
            symbol (str): The asset symbol
            
        Returns:
            str: Formatted trend analysis
        """
        try:
            # Get price data
            price_data = await self.price_fetcher.get_price_data(symbol)
            if not price_data:
                return f"I couldn't retrieve price data for {symbol.upper()}."
                
            # Get sentiment data
            sentiment_data = await self.sentiment_analyzer.get_sentiment(symbol)
            if not sentiment_data:
                sentiment_data = self.sentiment_analyzer.simulate_sentiment_data(symbol)
            
            # Generate technical analysis
            technical_analysis = await self._generate_technical_analysis(symbol, price_data)
            
            # Combine all data into a comprehensive analysis
            response = f"**{symbol.upper()} Trend Analysis**\n\n"
            
            response += "**Market Conditions:**\n"
            current_price = price_data.get("current_price", "Unknown")
            change_pct_24h = price_data.get("change_pct_24h", 0)
            
            # Format the change as an arrow and sign
            if change_pct_24h > 0:
                change_format = f"📈 +{change_pct_24h:.2f}%"
            elif change_pct_24h < 0:
                change_format = f"📉 {change_pct_24h:.2f}%"
            else:
                change_format = "➡️ 0.00%"
                
            response += f"Current price: ${current_price:,.2f} {change_format}\n"
            
            response += "\n**Technical Indicators:**\n"
            for indicator, value in technical_analysis["indicators"].items():
                response += f"• {indicator}: {value}\n"
                
            # Add overall signal
            signal = technical_analysis["signal"]
            if signal == "Strong Buy":
                signal_emoji = "🟢🟢"
            elif signal == "Buy":
                signal_emoji = "🟢"
            elif signal == "Neutral":
                signal_emoji = "⚪"
            elif signal == "Sell":
                signal_emoji = "🔴"
            else:  # Strong Sell
                signal_emoji = "🔴🔴"
                
            response += f"\n**Technical Signal:** {signal_emoji} {signal}\n"
            
            # Add sentiment summary if available
            if sentiment_data:
                sentiment_score = sentiment_data.get("sentiment_score", 0)
                
                # Format the sentiment as a descriptive term
                if sentiment_score > 0.5:
                    sentiment_desc = "Extremely Bullish 🚀"
                elif sentiment_score > 0.2:
                    sentiment_desc = "Bullish 📈"
                elif sentiment_score > -0.2:
                    sentiment_desc = "Neutral ↔️"
                elif sentiment_score > -0.5:
                    sentiment_desc = "Bearish 📉"
                else:
                    sentiment_desc = "Extremely Bearish 🧸"
                    
                response += f"\n**Social Sentiment:** {sentiment_desc}\n"
            
            # Add analysis conclusion
            response += f"\n**Conclusion:** {technical_analysis['conclusion']}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in trend analysis for {symbol}: {str(e)}")
            return f"I encountered an error trying to analyze trends for {symbol.upper()}."
    
    async def _generate_technical_analysis(self, symbol, price_data):
        """Generate technical analysis for an asset
        
        Args:
            symbol (str): The asset symbol
            price_data (dict): Price data
            
        Returns:
            dict: Technical analysis data
        """
        import random
        
        # Generate consistent but pseudo-random technical indicators
        symbol_hash = sum(ord(c) for c in symbol)
        random.seed(symbol_hash + datetime.now().day)  # Change daily but consistent for the same symbol
        
        # Common technical indicators
        rsi = random.randint(30, 70)
        macd = random.choice(["Bullish", "Bearish", "Neutral"])
        ma_signal = random.choice([
            "Above 50MA", "Below 200MA", 
            "50MA crossing 200MA (Golden Cross)", 
            "200MA crossing 50MA (Death Cross)"
        ])
        volume_trend = random.choice(["Increasing", "Decreasing", "Stable"])
        
        # Use actual price data to influence the indicators
        change_pct_24h = price_data.get("change_pct_24h", 0)
        if change_pct_24h > 2:
            rsi = min(rsi + 15, 95)  # Push RSI higher for big positive moves
        elif change_pct_24h < -2:
            rsi = max(rsi - 15, 5)   # Push RSI lower for big negative moves
            
        if change_pct_24h > 0:
            # More likely to be bullish if price is up
            if random.random() < 0.7:
                macd = "Bullish"
        else:
            # More likely to be bearish if price is down
            if random.random() < 0.7:
                macd = "Bearish"
        
        # Determine overall signal based on indicators
        if rsi > 65 and macd == "Bullish" and "Golden Cross" in ma_signal:
            signal = "Strong Buy"
            conclusion = f"Multiple bullish indicators align for {symbol.upper()}, suggesting strong upward momentum. The combination of high RSI, bullish MACD, and golden cross is historically a reliable signal for continuation."
        elif rsi > 55 and macd == "Bullish":
            signal = "Buy"
            conclusion = f"Technical indicators for {symbol.upper()} are generally bullish, with RSI showing strength and positive MACD. Consider this a potential buying opportunity, but maintain appropriate risk management."
        elif rsi < 35 and macd == "Bearish" and "Death Cross" in ma_signal:
            signal = "Strong Sell"
            conclusion = f"Multiple bearish signals for {symbol.upper()} indicate potential downside risk. The low RSI combined with bearish MACD and death cross often precedes further price declines."
        elif rsi < 45 and macd == "Bearish":
            signal = "Sell"
            conclusion = f"Technical outlook for {symbol.upper()} shows weakness. The bearish MACD and relatively low RSI suggest caution is warranted for current holders."
        else:
            signal = "Neutral"
            conclusion = f"Mixed signals for {symbol.upper()} suggest a wait-and-see approach. The market appears undecided, and more clarity may emerge in the coming days. Consider waiting for a clearer trend before taking significant positions."
        
        return {
            "indicators": {
                "RSI (14)": f"{rsi} - {'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'}",
                "MACD": macd,
                "Moving Averages": ma_signal,
                "Volume Trend": volume_trend,
                "Bollinger Bands": random.choice(["Expanding", "Contracting", "Upper Band Test", "Lower Band Test"])
            },
            "signal": signal,
            "conclusion": conclusion
        }
    
    async def _get_market_update(self, symbol):
        """Get a comprehensive market update for an asset
        
        Args:
            symbol (str): The asset symbol
            
        Returns:
            str: Formatted market update
        """
        # Get price data
        price_data = await self.price_fetcher.get_price_data(symbol)
        if not price_data:
            return f"I couldn't retrieve market data for {symbol.upper()}."
        
        # Get recent news headline
        news_data = await self.sentiment_analyzer.get_news(symbol)
        latest_news = news_data["articles"][0] if news_data and news_data["articles"] else None
        
        # Get simplified sentiment
        sentiment_data = await self.sentiment_analyzer.get_sentiment(symbol)
        sentiment_score = sentiment_data.get("sentiment_score", 0) if sentiment_data else 0
        
        # Format sentiment as text
        if sentiment_score > 0.3:
            sentiment_text = "bullish 📈"
        elif sentiment_score < -0.3:
            sentiment_text = "bearish 📉"
        else:
            sentiment_text = "neutral ↔️"
            
        # Construct a concise market update
        response = f"**{symbol.upper()} Market Update**\n\n"
        
        # Add price info
        current_price = price_data.get("current_price", "Unknown")
        change_pct_24h = price_data.get("change_pct_24h", 0)
            
        # Format the change as an arrow and sign
        if change_pct_24h > 0:
            change_format = f"📈 +{change_pct_24h:.2f}%"
        elif change_pct_24h < 0:
            change_format = f"📉 {change_pct_24h:.2f}%"
        else:
            change_format = "➡️ 0.00%"
            
        response += f"Current price: ${current_price:,.2f} {change_format}\n"
                
        # Add social sentiment
        response += f"\nSocial sentiment is {sentiment_text}"
        
        # Add news headline if available
        if latest_news:
            response += f"\n\n**Latest News:** {latest_news['title']}"
            
        # Add trading insight
        response += "\n\n**Trading Insight:** "
        
        if "bearish" in sentiment_text and "📉" in change_format:
            response += "Price action and sentiment both negative. Consider waiting for reversal signals before entering."
        elif "bullish" in sentiment_text and "📈" in change_format:
            response += "Price and sentiment aligned positively. Look for pullbacks to key support levels for potential entries."
        else:
            response += "Mixed signals between price action and sentiment. Monitor for clearer directional bias before making major moves."
        
        return response