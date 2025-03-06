import os
import logging
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("TradeMaster.Tools.Market.Price")

class PriceDataFetcher:
    """Fetches price data for cryptocurrencies and stocks"""
    
    def __init__(self):
        """Initialize the price data fetcher"""
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        
        # Cache for recent API calls to avoid rate limiting
        self.cache = {}  # {symbol: {"data": price_data, "timestamp": fetch_time}}
        
        # Cache expiration time (in seconds)
        self.cache_expiry = 300  # 5 minutes
        
        # Mapping of common symbols to CoinGecko IDs
        self.coingecko_id_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "usdt": "tether",
            "bnb": "binancecoin",
            "usdc": "usd-coin",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "sol": "solana",
            "dot": "polkadot",
            "avax": "avalanche-2",
            "matic": "matic-network",
            "shib": "shiba-inu",
            "link": "chainlink",
            "uni": "uniswap",
            "ltc": "litecoin"
        }
    
    async def get_price_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get price data for a symbol
        
        Args:
            symbol (str): The symbol to get price data for
            
        Returns:
            dict or None: Price data or None if the request failed
        """
        # Check cache first
        if symbol in self.cache:
            cache_data = self.cache[symbol]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry:
                logger.debug(f"Using cached price data for {symbol} (age: {cache_age:.1f}s)")
                return cache_data["data"]
        
        # Determine if this is crypto or stock
        is_crypto = symbol not in ["spy", "qqq", "dia", "iwm", "aapl", "msft", "amzn", "goog", "tsla", "meta", "nflx"]
        
        try:
            if is_crypto:
                price_data = await self._fetch_crypto_price(symbol)
            else:
                price_data = await self._fetch_stock_price(symbol)
                
            if price_data:
                # Update cache
                self.cache[symbol] = {
                    "data": price_data,
                    "timestamp": datetime.now()
                }
                
                return price_data
            else:
                logger.warning(f"Failed to fetch price data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    async def _fetch_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch crypto price data from CoinGecko API
        
        Args:
            symbol (str): The crypto symbol
            
        Returns:
            dict or None: Price data or None if the request failed
        """
        # Map common symbols to CoinGecko IDs
        coingecko_id = self.coingecko_id_map.get(symbol, "bitcoin")
        
        # API endpoint with API key if available
        if self.coingecko_api_key:
            api_url = f"https://pro-api.coingecko.com/api/v3/coins/{coingecko_id}?x_cg_pro_api_key={self.coingecko_api_key}"
        else:
            api_url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract relevant price data
                        price_data = {
                            "current_price": data["market_data"]["current_price"]["usd"],
                            "change_24h": data["market_data"]["price_change_24h"],
                            "change_pct_24h": data["market_data"]["price_change_percentage_24h"],
                            "high_24h": data["market_data"]["high_24h"]["usd"],
                            "low_24h": data["market_data"]["low_24h"]["usd"],
                            "volume_24h": data["market_data"]["total_volume"]["usd"],
                            "market_cap": data["market_data"]["market_cap"]["usd"]
                        }
                        
                        return price_data
                    else:
                        logger.warning(f"Failed to get crypto price for {symbol} from CoinGecko. Status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error in _fetch_crypto_price for {symbol}: {str(e)}")
            return None
    
    async def _fetch_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch stock price data from Alpha Vantage API
        
        Args:
            symbol (str): The stock symbol
            
        Returns:
            dict or None: Price data or None if the request failed
        """
        if not self.alpha_vantage_api_key:
            # Create simulated data for testing
            return self._simulate_stock_data(symbol)
        
        api_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.alpha_vantage_api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "Global Quote" in data and data["Global Quote"]:
                            quote = data["Global Quote"]
                            
                            # Extract relevant price data
                            current_price = float(quote.get("05. price", 0))
                            change = float(quote.get("09. change", 0))
                            change_percent = float(quote.get("10. change percent", "0").replace("%", ""))
                            volume = int(quote.get("06. volume", 0))
                            
                            price_data = {
                                "current_price": current_price,
                                "change_24h": change,
                                "change_pct_24h": change_percent,
                                "volume_24h": volume
                            }
                            
                            return price_data
                        else:
                            logger.warning(f"Invalid data format from Alpha Vantage for {symbol}")
                            return None
                    else:
                        logger.warning(f"Failed to get stock price for {symbol} from Alpha Vantage. Status: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error in _fetch_stock_price for {symbol}: {str(e)}")
            return None
    
    def _simulate_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Create simulated stock data when API key is not available
        
        Args:
            symbol (str): The stock symbol
            
        Returns:
            dict: Simulated price data
        """
        import random
        from datetime import datetime
        
        # Generate consistent but pseudo-random data based on symbol and date
        symbol_hash = sum(ord(c) for c in symbol)
        today = datetime.now().date().toordinal()
        random.seed(symbol_hash + today)
        
        # Base price depends on symbol
        if symbol in ["aapl", "msft", "amzn", "goog"]:
            base_price = random.uniform(150, 3000)
        elif symbol in ["tsla", "meta", "nflx"]:
            base_price = random.uniform(150, 800)
        else:
            base_price = random.uniform(100, 500)
            
        # Price change
        change_pct = random.uniform(-3, 3)
        change = base_price * (change_pct / 100)
        
        # Volume based on symbol popularity
        if symbol in ["aapl", "tsla", "spy"]:
            volume = random.randint(10000000, 50000000)
        else:
            volume = random.randint(2000000, 15000000)
            
        return {
            "current_price": base_price,
            "change_24h": change,
            "change_pct_24h": change_pct,
            "volume_24h": volume
        }