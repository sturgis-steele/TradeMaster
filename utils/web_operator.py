import logging
import aiohttp
import asyncio
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger("TradeMaster.Utils.WebOperator")

class WebOperator:
    """Handles web scraping and API operations"""
    
    def __init__(self):
        """Initialize the web operator"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        logger.info("WebOperator initialized")
    
    async def scrape_twitter(self, query: str, count: int = 20) -> Optional[List[Dict[str, Any]]]:
        """Scrape Twitter for tweets about a topic
        
        Args:
            query (str): The search query
            count (int): Number of tweets to scrape
            
        Returns:
            list or None: List of tweet data or None if error
        """
        # Note: This is a simplified implementation that would need to be
        # replaced with a proper Twitter scraping solution in production
        
        # Nitter is an alternative Twitter frontend that's easier to scrape
        url = f"https://nitter.net/search?f=tweets&q={query}&since=0"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Parse HTML
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Extract tweets
                        tweet_elements = soup.select(".timeline-item")[:count]
                        
                        tweets = []
                        for element in tweet_elements:
                            # Extract tweet text
                            content_element = element.select_one(".tweet-content")
                            if not content_element:
                                continue
                                
                            text = content_element.get_text().strip()
                            
                            # Extract stats
                            stats = {}
                            stats_element = element.select_one(".tweet-stats")
                            if stats_element:
                                # Extract likes
                                likes_element = stats_element.select_one(".icon-heart")
                                if likes_element and likes_element.parent:
                                    likes_text = likes_element.parent.get_text().strip()
                                    stats["like_count"] = self._parse_count(likes_text)
                                
                                # Extract retweets
                                retweets_element = stats_element.select_one(".icon-retweet")
                                if retweets_element and retweets_element.parent:
                                    retweets_text = retweets_element.parent.get_text().strip()
                                    stats["retweet_count"] = self._parse_count(retweets_text)
                            
                            tweets.append({
                                "text": text,
                                "public_metrics": stats
                            })
                        
                        return tweets
                    else:
                        logger.warning(f"Error scraping Twitter: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error scraping Twitter: {str(e)}")
            return None
    
    def _parse_count(self, text: str) -> int:
        """Parse count from text (e.g., "1.5K" -> 1500)
        
        Args:
            text (str): The count text
            
        Returns:
            int: The parsed count
        """
        text = text.strip().lower()
        
        if not text or text == "0":
            return 0
        
        # Remove commas
        text = text.replace(",", "")
        
        # Handle K, M, B suffixes
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        elif "m" in text:
            return int(float(text.replace("m", "")) * 1000000)
        elif "b" in text:
            return int(float(text.replace("b", "")) * 1000000000)
        else:
            try:
                return int(float(text))
            except ValueError:
                return 0
    
    async def fetch_news(self, query: str, count: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Fetch news articles about a topic
        
        Args:
            query (str): The search query
            count (int): Number of articles to fetch
            
        Returns:
            list or None: List of article data or None if error
        """
        # Google News search URL
        url = f"https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Parse HTML
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # Extract articles
                        article_elements = soup.select("article")[:count]
                        
                        articles = []
                        for element in article_elements:
                            # Extract title
                            title_element = element.select_one("h3 a")
                            if not title_element:
                                continue
                                
                            title = title_element.get_text().strip()
                            
                            # Extract source and time
                            source_element = element.select_one("time")
                            source = source_element.parent.get_text().strip() if source_element else ""
                            
                            # Extract description (not always available)
                            description = ""
                            
                            articles.append({
                                "title": title,
                                "source": source,
                                "description": description
                            })
                        
                        return articles
                    else:
                        logger.warning(f"Error fetching news: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return None