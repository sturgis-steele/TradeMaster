import os
import logging
import sqlite3
from datetime import datetime

# Configure logging
logger = logging.getLogger("TradeMaster.Database")

class Database:
    """SQLite database manager for TradeMaster bot
    
    This class manages all database operations for the TradeMaster bot, including:
    - Wallet tracking: Store and manage tracked blockchain wallets
    - Trade tracking: Record and analyze user trading activity
    - User statistics: Calculate and store trading performance metrics
    - Context logging: Maintain conversation context and user interactions
    - User profiles: Store user preferences and historical data
    
    The database uses SQLite for its simplicity, reliability, and zero-configuration nature.
    It maintains several tables to organize different aspects of the bot's functionality,
    with proper indexing for optimal query performance.
    
    Tables Overview:
    - tracked_wallets: Stores wallet addresses being monitored
    - trades: Records individual trading transactions
    - user_stats: Maintains aggregated trading statistics
    - context_logs: Stores conversation context
    - user_profiles: Manages user preferences and metadata
    - user_wallets: Links users to their wallets
    - conversation_memory: Stores long-term conversation context
    - conversation_history: Records chat interactions
    """
    
    def __init__(self, db_path="data/trademaster.db"):
        """Initialize the database connection and ensure required tables exist
        
        This constructor performs several initialization steps:
        1. Creates the database directory if it doesn't exist
        2. Establishes a connection to the SQLite database
        3. Creates all required tables if they don't exist
        4. Sets up proper row factory for dictionary-like access
        
        Args:
            db_path (str): Path to the SQLite database file. Defaults to 'data/trademaster.db'
        
        Raises:
            sqlite3.Error: If database connection or initialization fails
        """
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        
        # Initialize database
        self._connect()
        self._create_tables()
        
        logger.info(f"Database initialized at {db_path}")
    
    def _connect(self):
        """Establish connection to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Access columns by name
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            cursor = self.conn.cursor()
            
            # Table for tracked wallets
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_wallets (
                id INTEGER PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                network TEXT NOT NULL,
                tracked_since TIMESTAMP NOT NULL,
                last_checked TIMESTAMP,
                last_tx_hash TEXT,
                UNIQUE(wallet_address, network)
            )
            ''')
            
            # Table for trades
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                buy_price REAL,
                sell_price REAL,
                profit_loss REAL,
                profit_loss_pct REAL,
                timestamp TIMESTAMP NOT NULL
            )
            ''')
            
            # Table for user statistics
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                average_profit_pct REAL DEFAULT 0,
                largest_win_pct REAL DEFAULT 0,
                largest_loss_pct REAL DEFAULT 0,
                last_updated TIMESTAMP
            )
            ''')
            
            # Table for context logs
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_logs (
                id INTEGER PRIMARY KEY,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message_content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
            ''')
            
            # Table for user profiles and preferences
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                interactions_count INTEGER DEFAULT 0,
                preferences TEXT -- JSON string of user preferences
            )
            ''')
            
            # Table for user wallets
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_wallets (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                network TEXT NOT NULL,
                nickname TEXT,
                tracked_since TIMESTAMP NOT NULL,
                UNIQUE(user_id, wallet_address)
            )
            ''')
            
            # Table for conversation memory
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                topic TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,  # JSON string of metadata
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            ''')
            
            # Table for conversation history
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_content TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
            ''')
            
            self.conn.commit()
            logger.info("Database tables created/verified")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    # Wallet tracking methods
    def add_tracked_wallet(self, wallet_address, user_id, channel_id, network="eth"):
        """Add a wallet to the tracking list
        
        Args:
            wallet_address (str): The wallet address to track
            user_id (str): Discord user ID of the requester
            channel_id (str): Discord channel ID for notifications
            network (str): Blockchain network ("eth" or "bsc")
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Check if wallet is already tracked
            cursor.execute(
                "SELECT id FROM tracked_wallets WHERE wallet_address = ? AND network = ?",
                (wallet_address, network)
            )
            
            if cursor.fetchone():
                # Update existing record
                cursor.execute(
                    "UPDATE tracked_wallets SET user_id = ?, channel_id = ?, tracked_since = ? WHERE wallet_address = ? AND network = ?",
                    (user_id, channel_id, datetime.now().isoformat(), wallet_address, network)
                )
            else:
                # Insert new record
                cursor.execute(
                    "INSERT INTO tracked_wallets (wallet_address, user_id, channel_id, network, tracked_since) VALUES (?, ?, ?, ?, ?)",
                    (wallet_address, user_id, channel_id, network, datetime.now().isoformat())
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding tracked wallet: {str(e)}")
            return False
    
    def get_tracked_wallets(self, user_id=None, network=None):
        """Get tracked wallets, optionally filtered by user or network
        
        Args:
            user_id (str, optional): Filter by Discord user ID
            network (str, optional): Filter by blockchain network
            
        Returns:
            list: List of dictionaries with wallet data
        """
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM tracked_wallets"
            params = []
            
            # Add filters if provided
            if user_id or network:
                query += " WHERE"
                
                if user_id:
                    query += " user_id = ?"
                    params.append(user_id)
                    
                    if network:
                        query += " AND network = ?"
                        params.append(network)
                elif network:
                    query += " network = ?"
                    params.append(network)
            
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            wallets = []
            for row in cursor.fetchall():
                wallet = dict(row)
                wallets.append(wallet)
            
            return wallets
        except sqlite3.Error as e:
            logger.error(f"Error getting tracked wallets: {str(e)}")
            return []
    
    def update_wallet_tx(self, wallet_address, network, tx_hash):
        """Update the last transaction hash for a tracked wallet
        
        Args:
            wallet_address (str): The wallet address
            network (str): Blockchain network
            tx_hash (str): Transaction hash
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "UPDATE tracked_wallets SET last_checked = ?, last_tx_hash = ? WHERE wallet_address = ? AND network = ?",
                (datetime.now().isoformat(), tx_hash, wallet_address, network)
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating wallet transaction: {str(e)}")
            return False
    
    # Trade tracking methods
    def add_trade(self, trade_data):
        """Add a trade to the database
        
        Args:
            trade_data (dict): Trade data
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Extract trade data
            user_id = trade_data["user_id"]
            trade_type = trade_data["type"]
            symbol = trade_data["symbol"]
            amount = trade_data["amount"]
            buy_price = trade_data.get("buy_price")
            sell_price = trade_data.get("sell_price")
            profit_loss = trade_data.get("profit_loss")
            profit_loss_pct = trade_data.get("profit_loss_pct")
            timestamp = trade_data.get("timestamp", datetime.now().isoformat())
            
            # Insert trade
            cursor.execute(
                """INSERT INTO trades 
                (user_id, trade_type, symbol, amount, buy_price, sell_price, profit_loss, profit_loss_pct, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, trade_type, symbol, amount, buy_price, sell_price, profit_loss, profit_loss_pct, timestamp)
            )
            
            # If this is a complete trade, update user stats
            if trade_type == "complete" and profit_loss is not None:
                self.update_user_stats(user_id)
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding trade: {str(e)}")
            return False
    
    def get_user_trades(self, user_id, limit=10):
        """Get trades for a specific user
        
        Args:
            user_id (str): Discord user ID
            limit (int): Maximum number of trades to return
            
        Returns:
            list: List of dictionaries with trade data
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            
            # Convert to list of dictionaries
            trades = []
            for row in cursor.fetchall():
                trade = dict(row)
                trades.append(trade)
            
            return trades
        except sqlite3.Error as e:
            logger.error(f"Error getting user trades: {str(e)}")
            return []
    
    def update_user_stats(self, user_id, username=None):
        """Update user statistics based on their trade history
        
        Args:
            user_id (str): Discord user ID
            username (str, optional): Discord username
            
        Returns:
            dict: Updated user statistics
        """
        try:
            cursor = self.conn.cursor()
            
            # Get complete trades for this user
            cursor.execute(
                "SELECT * FROM trades WHERE user_id = ? AND trade_type = 'complete'",
                (user_id,)
            )
            
            trades = cursor.fetchall()
            
            if not trades:
                return {}
            
            # Calculate statistics
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t["profit_loss"] > 0)
            profit_loss_pcts = [t["profit_loss_pct"] for t in trades if t["profit_loss_pct"] is not None]
            
            avg_profit_pct = sum(profit_loss_pcts) / len(profit_loss_pcts) if profit_loss_pcts else 0
            largest_win_pct = max([t["profit_loss_pct"] for t in trades if t["profit_loss"] > 0], default=0)
            largest_loss_pct = min([t["profit_loss_pct"] for t in trades if t["profit_loss"] < 0], default=0)
            
            # Update or insert user stats
            if username:
                cursor.execute(
                    """INSERT INTO user_stats
                    (user_id, username, total_trades, winning_trades, average_profit_pct, largest_win_pct, largest_loss_pct, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    total_trades=excluded.total_trades,
                    winning_trades=excluded.winning_trades,
                    average_profit_pct=excluded.average_profit_pct,
                    largest_win_pct=excluded.largest_win_pct,
                    largest_loss_pct=excluded.largest_loss_pct,
                    last_updated=excluded.last_updated""",
                    (user_id, username, total_trades, winning_trades, avg_profit_pct, largest_win_pct, largest_loss_pct, datetime.now().isoformat())
                )
            else:
                cursor.execute(
                    """UPDATE user_stats SET
                    total_trades=?, winning_trades=?, average_profit_pct=?, largest_win_pct=?, largest_loss_pct=?, last_updated=?
                    WHERE user_id=?""",
                    (total_trades, winning_trades, avg_profit_pct, largest_win_pct, largest_loss_pct, datetime.now().isoformat(), user_id)
                )
            
            self.conn.commit()
            
            # Return the updated stats
            return {
                "user_id": user_id,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                "average_profit_pct": avg_profit_pct,
                "largest_win_pct": largest_win_pct,
                "largest_loss_pct": largest_loss_pct
            }
        except sqlite3.Error as e:
            logger.error(f"Error updating user stats: {str(e)}")
            return {}
    
    def get_user_stats(self, user_id):
        """Get statistics for a specific user
        
        Args:
            user_id (str): Discord user ID
            
        Returns:
            dict: User statistics
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "SELECT * FROM user_stats WHERE user_id = ?",
                (user_id,)
            )
            
            row = cursor.fetchone()
            
            if row:
                stats = dict(row)
                
                # Add win rate (calculated field)
                if stats["total_trades"] > 0:
                    stats["win_rate"] = (stats["winning_trades"] / stats["total_trades"]) * 100
                else:
                    stats["win_rate"] = 0
                    
                return stats
            else:
                return None
        except sqlite3.Error as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return None
    
    # Context logging methods
    def log_context(self, channel_id, user_id, message_content):
        """Log a message for context tracking
        
        Args:
            channel_id (str): Discord channel ID
            user_id (str): Discord user ID
            message_content (str): Content of the message
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "INSERT INTO context_logs (channel_id, user_id, message_content, timestamp) VALUES (?, ?, ?, ?)",
                (channel_id, user_id, message_content, datetime.now().isoformat())
            )
            
            # Cleanup old logs (keep only last 100 per channel)
            cursor.execute(
                """DELETE FROM context_logs
                WHERE id NOT IN (
                    SELECT id FROM context_logs
                    WHERE channel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                )
                AND channel_id = ?""",
                (channel_id, channel_id)
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging context: {str(e)}")
            return False
    
    def get_channel_context(self, channel_id, limit=10):
        """Get recent context messages for a channel
        
        Args:
            channel_id (str): Discord channel ID
            limit (int): Maximum number of messages to return
            
        Returns:
            list: List of dictionaries with message data
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "SELECT * FROM context_logs WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?",
                (channel_id, limit)
            )
            
            # Convert to list of dictionaries
            messages = []
            for row in cursor.fetchall():
                message = dict(row)
                messages.append(message)
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
        except sqlite3.Error as e:
            logger.error(f"Error getting channel context: {str(e)}")
            return []
