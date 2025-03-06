import re
import os
import logging
import aiohttp
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

from utils.config import load_config

# Load environment variables
load_dotenv("config/.env")

logger = logging.getLogger("TradeMaster.Tools.Wallet.Tracker")

# Try to import etherscan package, but handle if not available
try:
    from etherscan import Etherscan
    HAS_ETHERSCAN = True
except ImportError:
    logger.warning("Etherscan package not available. Using API directly instead.")
    HAS_ETHERSCAN = False

class WalletTracker:
    """Tool for tracking and analyzing blockchain wallets"""
    
    def __init__(self):
        """Initialize the wallet tracking tool"""
        # Load configuration
        self.config = load_config()
        self.wallet_config = self.config.get("tools", {}).get("wallet_tracking", {})
        
        # Check if wallet tracking is enabled
        if not self.wallet_config.get("enabled", True):
            logger.warning("Wallet tracking tool is disabled in configuration.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Get API keys
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        self.bscscan_api_key = os.getenv("BSCSCAN_API_KEY")
        
        # Dictionary to store tracked wallets with their metadata
        # Format: {wallet_address: {"user_id": discord_user_id, "network": "eth", "last_tx": timestamp}}
        self.tracked_wallets = self._load_tracked_wallets()
        
        # Initialize user memory
        self.memory_handler = None
        try:
            from core.memory import UserMemory
            self.memory_handler = UserMemory()
            logger.info("Memory system loaded for wallet tracking")
        except ImportError:
            logger.warning("UserMemory module not available for wallet tracking.")
        except Exception as e:
            logger.error(f"Error initializing UserMemory for wallet tracking: {str(e)}")
        
        logger.info("WalletTracker initialized")
    
    def _load_tracked_wallets(self):
        """Load tracked wallets from a JSON file"""
        try:
            with open("data/tracked_wallets.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No tracked wallets file found or invalid format. Creating new database.")
            return {}
            
    def _save_tracked_wallets(self):
        """Save tracked wallets to a JSON file"""
        try:
            # Ensure the data directory exists
            os.makedirs("data", exist_ok=True)
            
            with open("data/tracked_wallets.json", "w") as f:
                json.dump(self.tracked_wallets, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracked wallets: {str(e)}")
    
    async def process(self, text, message):
        """Process a wallet-related request
        
        Args:
            text (str): The message text
            message (discord.Message): The Discord message object
            
        Returns:
            str: Response to the request
        """
        if not self.enabled:
            return "Wallet tracking is currently disabled."
            
        # Extract information from message
        user_id = str(message.author.id)
        username = message.author.name
        
        return await self.process_text(text, user_id, username)
    
    async def process_text(self, text, user_id, username):
        """Process a wallet-related request from text
        
        Args:
            text (str): The message text
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            
        Returns:
            str: Response to the request
        """
        if not self.enabled:
            return "Wallet tracking is currently disabled."
        
        # Extract wallet address if present in the message
        wallet_address = self._extract_wallet_address(text)
        
        # Check if this is a tracking request
        is_tracking_request = any(phrase in text.lower() for phrase in [
            "track", "monitor", "watch", "follow"
        ])
        
        # Handle tracking request with provided address
        if is_tracking_request and wallet_address:
            return await self._handle_track_request(wallet_address, user_id, username)
            
        # Handle tracking request without address (guide user)
        if is_tracking_request:
            return "I'd be happy to track a wallet for you! Please provide the wallet address you'd like to track. It should start with '0x' for Ethereum/BSC wallets."
        
        # Check if this is a balance inquiry
        if any(word in text.lower() for word in ["balance", "how much", "holdings"]) and wallet_address:
            return await self._get_wallet_balance(wallet_address)
            
        # Check if this is a transaction history request
        if any(word in text.lower() for word in ["transactions", "history", "activity"]) and wallet_address:
            return await self._get_recent_transactions(wallet_address)
            
        # If user just shared a wallet with no specific command, provide a summary
        if wallet_address:
            return await self._get_wallet_summary(wallet_address)
            
        # Generic response if no specific action determined
        return "I can track wallets, check balances, and monitor transactions. Just share an Ethereum or BSC wallet address (starts with 0x) and tell me what you'd like to know about it!"
    
    def _extract_wallet_address(self, text):
        """Extract a wallet address from text
        
        Args:
            text (str): The message text
            
        Returns:
            str or None: The extracted wallet address or None if not found
        """
        # Simple regex for ETH/BSC wallet addresses
        eth_address_pattern = r'0x[a-fA-F0-9]{40}'
        match = re.search(eth_address_pattern, text)
        
        if match:
            return match.group(0)
        return None
        
    async def _handle_track_request(self, wallet_address, user_id, username, channel_id=None):
        """Handle a request to track a wallet
        
        Args:
            wallet_address (str): The wallet address to track
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            channel_id (str, optional): The Discord channel ID for notifications
            
        Returns:
            str: Response to the tracking request
        """
        # Add the wallet to tracked wallets if not already tracked
        if wallet_address in self.tracked_wallets:
            return f"I'm already tracking that wallet. I'll notify you when significant activity happens!"
        
        # Determine the blockchain network (default to Ethereum)
        network = "eth"
        
        # Store wallet tracking information
        self.tracked_wallets[wallet_address] = {
            "user_id": user_id,
            "channel_id": channel_id,
            "network": network,
            "tracked_since": datetime.now().isoformat(),
            "last_tx": None
        }
        
        # Save the updated tracking list
        self._save_tracked_wallets()
        
        # Save to user memory if available
        if self.memory_handler:
            # Add wallet to user's tracked wallets
            self.memory_handler.add_user_wallet(user_id, wallet_address, network)
            
            # Store this as a memory
            nickname = f"{network.upper()} Wallet"  # Default nickname
            self.memory_handler.add_memory(
                user_id, 
                "wallet_info", 
                f"tracked_{wallet_address[:8]}",
                f"User is tracking wallet {wallet_address} on {network.upper()} network.",
                {"network": network, "address": wallet_address, "nickname": nickname}
            )
        
        # Fetch initial balance to verify the wallet exists and is trackable
        try:
            balance = await self._fetch_wallet_balance(wallet_address, network)
            if balance is not None:
                # Save balance information to memory
                if self.memory_handler:
                    self.memory_handler.add_memory(
                        user_id,
                        "wallet_info",
                        f"balance_{wallet_address[:8]}",
                        f"Wallet {wallet_address} has balance of {balance} {network.upper() if network == 'eth' else 'BNB'}.",
                        {"address": wallet_address, "balance": balance, "network": network}
                    )
                    
                return f"I'm now tracking wallet {wallet_address[:6]}...{wallet_address[-4:]} on {network.upper()}. Current balance: {balance} {network.upper() if network == 'eth' else 'BNB'}. I'll alert you when significant activity happens!"
            else:
                # Remove the wallet if we couldn't get its balance
                del self.tracked_wallets[wallet_address]
                self._save_tracked_wallets()
                return f"I couldn't verify that wallet. Please check the address and try again."
        except Exception as e:
            logger.error(f"Error verifying wallet {wallet_address}: {str(e)}")
            # Remove the wallet if verification failed
            del self.tracked_wallets[wallet_address]
            self._save_tracked_wallets()
            return f"There was an error verifying that wallet. Please check the address and try again."
    
    async def _get_wallet_balance(self, wallet_address):
        """Get the balance of a wallet
        
        Args:
            wallet_address (str): The wallet address
            
        Returns:
            str: Response with wallet balance
        """
        # Determine network based on tracked wallets, default to Ethereum
        network = "eth"
        if wallet_address in self.tracked_wallets:
            network = self.tracked_wallets[wallet_address].get("network", "eth")
        
        try:
            balance_data = await self.blockchain_api.get_wallet_balance(wallet_address, network)
            
            if balance_data:
                eth_balance = balance_data.get("eth_balance", 0)
                token_balances = balance_data.get("token_balances", [])
                
                # Format response
                response = f"Balance for {wallet_address[:6]}...{wallet_address[-4:]}:\n"
                response += f"• {eth_balance} {'ETH' if network == 'eth' else 'BNB'}\n"
                
                # Add token balances if available
                if token_balances:
                    # Show top 5 tokens by value
                    for token in token_balances[:5]:
                        response += f"• {token['balance']} {token['symbol']}\n"
                    
                    if len(token_balances) > 5:
                        response += f"• ...and {len(token_balances) - 5} more tokens\n"
                
                return response
            else:
                return f"I couldn't retrieve the balance for this wallet. It might be new or have no transactions."
                
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return f"I encountered an error while checking this wallet's balance. Please try again later."
    
    async def _get_recent_transactions(self, wallet_address):
        """Get recent transactions for a wallet
        
        Args:
            wallet_address (str): The wallet address
            
        Returns:
            str: Response with recent transaction information
        """
        # Determine network based on tracked wallets, default to Ethereum
        network = "eth"
        if wallet_address in self.tracked_wallets:
            network = self.tracked_wallets[wallet_address].get("network", "eth")
        
        try:
            transactions = await self.blockchain_api.get_recent_transactions(wallet_address, network)
            
            if not transactions:
                return f"I couldn't find any recent transactions for this wallet."
            
            # Format response
            response = f"Recent transactions for {wallet_address[:6]}...{wallet_address[-4:]}:\n\n"
            
            for i, tx in enumerate(transactions[:3]):  # Show up to 3 transactions
                tx_type = "Sent" if tx["from"].lower() == wallet_address.lower() else "Received"
                value = tx["value"]
                timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))
                date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                response += f"{i+1}. {tx_type} {value} {'ETH' if network == 'eth' else 'BNB'} "
                response += f"on {date_str}\n"
                response += f"   Tx: {tx['hash'][:8]}...{tx['hash'][-6:]}\n"
            
            return response
                
        except Exception as e:
            logger.error(f"Error getting recent transactions: {str(e)}")
            return f"I encountered an error while checking this wallet's transactions. Please try again later."
    
    async def _get_wallet_summary(self, wallet_address):
        """Get a summary of a wallet's activity
        
        Args:
            wallet_address (str): The wallet address
            
        Returns:
            str: Response with wallet summary
        """
        balance = await self._get_wallet_balance(wallet_address)
        
        return f"Wallet summary: {balance}\n\nIf you want me to track this wallet, reply with 'TradeMaster, track this wallet'. Use 'transactions {wallet_address}' to see recent activity."
    
    async def _fetch_wallet_balance(self, wallet_address, network="eth"):
        """Fetch the balance of a wallet from the blockchain API
        
        Args:
            wallet_address (str): The wallet address
            network (str): The blockchain network ("eth" or "bsc")
            
        Returns:
            float or None: The wallet balance in ETH/BNB or None if the request failed
        """
        # Get the API key for the appropriate network
        api_key = self.etherscan_api_key if network == "eth" else self.bscscan_api_key
        
        if not api_key:
            logger.warning(f"No API key for {network} network")
            return None
        
        # API endpoint based on network
        if network == "eth":
            api_url = f"https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={api_key}"
        else:
            api_url = f"https://api.bscscan.com/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data["status"] == "1":
                            # Convert wei to ETH/BNB
                            balance_in_wei = int(data["result"])
                            balance = balance_in_wei / 10**18
                            return balance
                    
                    logger.warning(f"Failed to get balance for {wallet_address} on {network}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching balance for {wallet_address} on {network}: {str(e)}")
            return None