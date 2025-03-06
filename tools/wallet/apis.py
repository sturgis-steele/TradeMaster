import os
import logging
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger("TradeMaster.Tools.Wallet.APIs")

class BlockchainAPI:
    """Handles interactions with various blockchain APIs"""
    
    def __init__(self):
        """Initialize the blockchain API handler"""
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        self.bscscan_api_key = os.getenv("BSCSCAN_API_KEY")
        
        # API base URLs
        self.api_urls = {
            "eth": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api"
        }
        
        # Cache for recent API calls to avoid rate limiting
        self.cache = {
            "balances": {},  # {network_address: {"data": balance, "timestamp": fetch_time}}
            "transactions": {}  # {network_address: {"data": txs, "timestamp": fetch_time}}
        }
        
        # Cache expiration times (in seconds)
        self.cache_expiry = {
            "balances": 300,  # 5 minutes
            "transactions": 180  # 3 minutes
        }
        
        logger.info("BlockchainAPI initialized")
    
    async def get_wallet_balance(self, wallet_address: str, network: str = "eth") -> Optional[Dict[str, Any]]:
        """Get the balance of a wallet
        
        Args:
            wallet_address (str): The wallet address
            network (str): The blockchain network (eth or bsc)
            
        Returns:
            dict or None: Wallet balance data or None if error
        """
        # Check cache first
        cache_key = f"{network}_{wallet_address.lower()}"
        if cache_key in self.cache["balances"]:
            cache_entry = self.cache["balances"][cache_key]
            cache_age = (datetime.now() - cache_entry["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry["balances"]:
                logger.debug(f"Using cached balance for {wallet_address}")
                return cache_entry["data"]
        
        # Get the API key for the appropriate network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        
        if not api_key:
            logger.warning(f"No API key available for {network} network")
            return None
        
        # API endpoint for balance
        api_url = f"{self.api_urls[network]}?module=account&action=balance&address={wallet_address}&tag=latest&apikey={api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1":
                            # Convert wei to ether
                            eth_balance = float(data["result"]) / 10**18
                            
                            # Format to 4 decimal places if small, otherwise 2
                            if eth_balance < 0.01:
                                eth_balance = f"{eth_balance:.4f}"
                            else:
                                eth_balance = f"{eth_balance:.2f}"
                            
                            # Get token balances (simplified, would need additional API calls)
                            token_balances = await self._get_token_balances(wallet_address, network, api_key)
                            
                            result = {
                                "eth_balance": eth_balance,
                                "token_balances": token_balances
                            }
                            
                            # Cache the result
                            self.cache["balances"][cache_key] = {
                                "data": result,
                                "timestamp": datetime.now()
                            }
                            
                            return result
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                            return None
                    else:
                        logger.error(f"HTTP error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return None
    
    async def _get_token_balances(self, wallet_address: str, network: str, api_key: str) -> List[Dict[str, Any]]:
        """Get token balances for a wallet (
    
    async def get_balance(self, address: str, network: str = "eth") -> Optional[float]:
        """Get the balance of a wallet address
        
        Args:
            address (str): The wallet address
            network (str, optional): The blockchain network (eth or bsc)
            
        Returns:
            float or None: The wallet balance in ETH/BNB or None if request failed
        """
        # Check if the network is supported
        if network not in self.api_urls:
            logger.error(f"Unsupported network: {network}")
            return None
            
        # Get the API key for the network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        if not api_key:
            logger.warning(f"No API key available for {network}")
            return None
        
        # Check cache first
        cache_key = f"{network}_{address}_balance"
        from datetime import datetime
        
        if cache_key in self.cache["balances"]:
            cache_data = self.cache["balances"][cache_key]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry["balances"]:
                logger.debug(f"Using cached balance for {address} on {network} (age: {cache_age:.1f}s)")
                return cache_data["data"]
        
        # Prepare API call
        api_url = self.api_urls[network]
        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1":
                            # Convert wei to ETH/BNB
                            balance_in_wei = int(data["result"])
                            balance = balance_in_wei / 10**18
                            
                            # Cache the result
                            self.cache["balances"][cache_key] = {
                                "data": balance,
                                "timestamp": datetime.now()
                            }
                            
                            return balance
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                    else:
                        logger.warning(f"HTTP error: {response.status}")
                        
                    return None
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            return None
    
    async def get_transactions(self, address: str, network: str = "eth", count: int = 5) -> Optional[list]:
        """Get recent transactions for a wallet address
        
        Args:
            address (str): The wallet address
            network (str, optional): The blockchain network (eth or bsc)
            count (int, optional): Number of transactions to return
            
        Returns:
            list or None: List of transaction dictionaries or None if request failed
        """
        # Check if the network is supported
        if network not in self.api_urls:
            logger.error(f"Unsupported network: {network}")
            return None
            
        # Get the API key for the network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        if not api_key:
            logger.warning(f"No API key available for {network}")
            return None
        
        # Check cache first
        cache_key = f"{network}_{address}_transactions"
        from datetime import datetime
        
        if cache_key in self.cache["transactions"]:
            cache_data = self.cache["transactions"][cache_key]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_expiry["transactions"]:
                logger.debug(f"Using cached transactions for {address} on {network} (age: {cache_age:.1f}s)")
                return cache_data["data"][:count]  # Return only requested count
        
        # Prepare API call
        api_url = self.api_urls[network]
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": count,
            "sort": "desc",
            "apikey": api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1" and isinstance(data["result"], list):
                            transactions = data["result"]
                            
                            # Cache the result
                            self.cache["transactions"][cache_key] = {
                                "data": transactions,
                                "timestamp": datetime.now()
                            }
                            
                            return transactions
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                    else:
                        logger.warning(f"HTTP error: {response.status}")
                        
                    return None
        except Exception as e:
            logger.error(f"Error fetching transactions: {str(e)}")
            return None
    
    async def get_token_balance(self, address: str, token_address: str, network: str = "eth") -> Optional[Dict[str, Any]]:
        """Get token balance for a wallet address
        
        Args:
            address (str): The wallet address
            token_address (str): The token contract address
            network (str, optional): The blockchain network (eth or bsc)
            
        Returns:
            dict or None: Token balance information or None if request failed
        """
        # Check if the network is supported
        if network not in self.api_urls:
            logger.error(f"Unsupported network: {network}")
            return None
            
        # Get the API key for the network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        if not api_key:
            logger.warning(f"No API key available for {network}")
            return None
        
        # Prepare API call
        api_url = self.api_urls[network]
        params = {
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": token_address,
            "address": address,
            "tag": "latest",
            "apikey": api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1":
                            # Get token info for proper decimals
                            token_info = await self.get_token_info(token_address, network)
                            decimals = token_info.get("decimals", 18) if token_info else 18
                            symbol = token_info.get("symbol", "TOKEN") if token_info else "TOKEN"
                            
                            # Convert to proper token amount
                            balance_raw = int(data["result"])
                            balance = balance_raw / (10 ** decimals)
                            
                            return {
                                "symbol": symbol,
                                "balance": balance,
                                "decimals": decimals,
                                "raw_balance": balance_raw,
                                "token_address": token_address
                            }
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                    else:
                        logger.warning(f"HTTP error: {response.status}")
                        
                    return None
        except Exception as e:
            logger.error(f"Error fetching token balance: {str(e)}")
            return None
    
    async def get_token_info(self, token_address: str, network: str = "eth") -> Optional[Dict[str, Any]]:
        """Get information about a token
        
        Args:
            token_address (str): The token contract address
            network (str, optional): The blockchain network (eth or bsc)
            
        Returns:
            dict or None: Token information or None if request failed
        """
        # Check if the network is supported
        if network not in self.api_urls:
            logger.error(f"Unsupported network: {network}")
            return None
            
        # Get the API key for the network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        if not api_key:
            logger.warning(f"No API key available for {network}")
            return None
        
        # Prepare API call
        api_url = self.api_urls[network]
        params = {
            "module": "token",
            "action": "tokeninfo",
            "contractaddress": token_address,
            "apikey": api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1" and isinstance(data["result"], list) and len(data["result"]) > 0:
                            return data["result"][0]
                        else:
                            logger.warning(f"API error: {data.get('message', 'Unknown error')}")
                    else:
                        logger.warning(f"HTTP error: {response.status}")
                        
                    return None
        except Exception as e:
            logger.error(f"Error fetching token info: {str(e)}")
            return None