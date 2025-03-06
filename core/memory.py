import os
import logging
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from data.db import Database
from utils.config import load_config

logger = logging.getLogger("TradeMaster.Core.Memory")

class UserMemory:
    """Persistent memory storage for user interactions and data
    
    This class manages all persistent user data, including profiles, preferences,
    tracked wallets, conversation history, and important facts. It provides methods
    for storing and retrieving this information to maintain context across sessions
    and enable personalized interactions.
    """
    
    def __init__(self, db_path=None):
        """Initialize the user memory manager
        
        Args:
            db_path (str, optional): Path to the SQLite database file
        """
        # Load configuration settings
        self.config = load_config()
        self.memory_config = self.config.get("memory", {})
        
        # Check if memory system is enabled in configuration
        if not self.memory_config.get("enabled", True):
            logger.warning("Memory system is disabled in configuration.")
            self.enabled = False
            return
            
        self.enabled = True
        
        # Initialize database connection
        if db_path:
            self.db = Database(db_path)
        else:
            self.db = Database()  # Use default path
            
        # Store a reference to the connection for convenience
        self.conn = self.db.conn
        logger.info("User memory system initialized")
        logger.info(f"UserMemory initialized with database at {self.db.db_path}")
    
    def close(self):
        """Close the database connection
        
        This method should be called when shutting down the bot to ensure
        proper database cleanup.
        """
        if self.enabled and hasattr(self, 'db'):
            self.db.close()
            logger.info("Database connection closed")
    
    def get_user_profile(self, user_id, username=None):
        """Get a user's profile, creating it if it doesn't exist
        
        This method retrieves a user's profile from the database. If the profile
        doesn't exist and a username is provided, it creates a new profile.
        
        Args:
            user_id (str): The user's Discord ID
            username (str, optional): The user's username (for new profiles)
            
        Returns:
            dict: The user profile data or None if not found/created
        """
        if not self.enabled or not self.conn:
            return None
            
        try:
            cursor = self.conn.cursor()
            
            # Try to get existing profile
            cursor.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?",
                (user_id,)
            )
            
            row = cursor.fetchone()
            
            if row:
                # Update last_seen and interactions_count for existing user
                cursor.execute(
                    "UPDATE user_profiles SET last_seen = ?, interactions_count = interactions_count + 1 WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                self.conn.commit()
                
                return dict(row)
            elif username:
                # Create new profile for first-time user
                now = datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO user_profiles (user_id, username, first_seen, last_seen, interactions_count) VALUES (?, ?, ?, ?, 1)",
                    (user_id, username, now, now)
                )
                self.conn.commit()
                
                return {
                    "user_id": user_id,
                    "username": username,
                    "first_seen": now,
                    "last_seen": now,
                    "interactions_count": 1,
                    "preferences": None
                }
            else:
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error in get_user_profile: {str(e)}")
            return None
    
    def update_user_preferences(self, user_id, preferences):
        """Update a user's preferences
        
        This method stores user preferences such as notification settings,
        preferred cryptocurrencies, or trading interests.
        
        Args:
            user_id (str): The user's Discord ID
            preferences (dict): Preference data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            # Convert preferences to JSON string for storage
            preferences_json = json.dumps(preferences)
            
            cursor.execute(
                "UPDATE user_profiles SET preferences = ? WHERE user_id = ?",
                (preferences_json, user_id)
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error in update_user_preferences: {str(e)}")
            return False
    
    def get_user_wallets(self, user_id):
        """Get all wallets tracked by a user
        
        This method retrieves all blockchain wallets that a user has asked the bot to track.
        These wallets can be used for monitoring transactions and balance changes.
        
        Args:
            user_id (str): The user's Discord ID
            
        Returns:
            list: List of wallet data dictionaries with address, network, and nickname
        """
        if not self.enabled or not self.conn:
            return []
            
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "SELECT * FROM user_wallets WHERE user_id = ?",
                (user_id,)
            )
            
            wallets = []
            for row in cursor.fetchall():
                wallets.append(dict(row))
                
            return wallets
        except sqlite3.Error as e:
            logger.error(f"Error in get_user_wallets: {str(e)}")
            return []
    
    def add_user_wallet(self, user_id, wallet_address, network, nickname=None):
        """Add a wallet to a user's tracked wallets
        
        This method adds or updates a blockchain wallet address for tracking.
        Users can track multiple wallets across different networks and assign
        nicknames for easier reference.
        
        Args:
            user_id (str): The user's Discord ID
            wallet_address (str): The wallet address to track
            network (str): The blockchain network (e.g., "ethereum", "bsc")
            nickname (str, optional): A user-defined nickname for the wallet
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            # Check if wallet already exists for this user
            cursor.execute(
                "SELECT id FROM user_wallets WHERE user_id = ? AND wallet_address = ?",
                (user_id, wallet_address)
            )
            
            if cursor.fetchone():
                # Update existing wallet
                if nickname:
                    cursor.execute(
                        "UPDATE user_wallets SET network = ?, nickname = ? WHERE user_id = ? AND wallet_address = ?",
                        (network, nickname, user_id, wallet_address)
                    )
                else:
                    cursor.execute(
                        "UPDATE user_wallets SET network = ? WHERE user_id = ? AND wallet_address = ?",
                        (network, user_id, wallet_address)
                    )
            else:
                # Add new wallet
                cursor.execute(
                    "INSERT INTO user_wallets (user_id, wallet_address, network, nickname, tracked_since) VALUES (?, ?, ?, ?, ?)",
                    (user_id, wallet_address, network, nickname, datetime.now().isoformat())
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error in add_user_wallet: {str(e)}")
            return False
    
    def add_memory(self, user_id, memory_type, topic, content, metadata=None):
        """Add or update a memory for a user
        
        This method stores important information about a user that should be remembered
        across conversations. This can include facts, preferences, or wallet information.
        If a memory with the same type and topic already exists, it will be updated.
        
        Args:
            user_id (str): The user's Discord ID
            memory_type (str): Type of memory (e.g., "fact", "preference", "wallet_info")
            topic (str): The topic of the memory (e.g., "risk_tolerance", "favorite_coins")
            content (str): The memory content to store
            metadata (dict, optional): Additional metadata about this memory
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            # Check if memory already exists
            cursor.execute(
                "SELECT id FROM conversation_memory WHERE user_id = ? AND memory_type = ? AND topic = ?",
                (user_id, memory_type, topic)
            )
            
            row = cursor.fetchone()
            
            metadata_json = json.dumps(metadata) if metadata else None
            now = datetime.now().isoformat()
            
            if row:
                # Update existing memory
                cursor.execute(
                    "UPDATE conversation_memory SET content = ?, metadata = ?, updated_at = ? WHERE id = ?",
                    (content, metadata_json, now, row['id'])
                )
            else:
                # Add new memory
                cursor.execute(
                    "INSERT INTO conversation_memory (user_id, memory_type, topic, content, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, memory_type, topic, content, metadata_json, now, now)
                )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error in add_memory: {str(e)}")
            return False
    
    def get_memories(self, user_id, memory_type=None, topic=None):
        """Get memories for a user
        
        This method retrieves stored memories for a user, optionally filtered by type or topic.
        It's used to access important facts, preferences, or other information about the user
        that has been stored across conversations.
        
        Args:
            user_id (str): The user's Discord ID
            memory_type (str, optional): Filter by memory type (e.g., "fact", "preference")
            topic (str, optional): Filter by topic
            
        Returns:
            list: List of memory dictionaries with content and metadata
        """
        if not self.enabled or not self.conn:
            return []
            
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM conversation_memory WHERE user_id = ?"
            params = [user_id]
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
                
            if topic:
                query += " AND topic = ?"
                params.append(topic)
                
            query += " ORDER BY updated_at DESC"
            
            cursor.execute(query, params)
            
            memories = []
            for row in cursor.fetchall():
                memory = dict(row)
                
                # Parse metadata JSON if present
                if memory['metadata']:
                    try:
                        memory['metadata'] = json.loads(memory['metadata'])
                    except json.JSONDecodeError:
                        memory['metadata'] = {}
                        
                memories.append(memory)
                
            return memories
        except sqlite3.Error as e:
            logger.error(f"Error in get_memories: {str(e)}")
            return []
    
    def delete_memories_by_topic(self, user_id, topic):
        """Delete memories related to a specific topic
        
        This method allows users to remove specific memories or information
        that they no longer want the bot to remember. It uses partial matching
        to find topics that contain the specified string.
        
        Args:
            user_id (str): The user's Discord ID
            topic (str): Topic to match (can be partial)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            # Use LIKE for partial topic matching
            cursor.execute(
                "DELETE FROM conversation_memory WHERE user_id = ? AND topic LIKE ?",
                (user_id, f"%{topic}%")
            )
            
            self.conn.commit()
            return cursor.rowcount > 0  # Return True if any rows were deleted
        except sqlite3.Error as e:
            logger.error(f"Error in delete_memories_by_topic: {str(e)}")
            return False
    
    def delete_all_memories(self, user_id):
        """Delete all memories and data for a user
        
        This method provides a "forget me" functionality, removing all stored data
        about a user except for their basic profile. This respects user privacy
        and data rights while maintaining the ability to recognize the user.
        
        Args:
            user_id (str): The user's Discord ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            # Delete all user data
            cursor.execute("DELETE FROM conversation_memory WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM user_wallets WHERE user_id = ?", (user_id,))
            
            # Reset profile but don't delete it
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_profiles SET preferences = NULL, interactions_count = 0, last_seen = ? WHERE user_id = ?",
                (now, user_id)
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error in delete_all_memories: {str(e)}")
            return False
    
    def log_conversation(self, user_id, channel_id, message_content, bot_response):
        """Log a conversation exchange
        
        This method records each interaction between a user and the bot.
        These logs help maintain conversation context and can be analyzed
        to improve the bot's responses over time.
        
        Args:
            user_id (str): The user's Discord ID
            channel_id (str): The channel ID
            message_content (str): The user's message
            bot_response (str): The bot's response
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled or not self.conn:
            return False
            
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "INSERT INTO conversation_history (user_id, channel_id, message_content, bot_response, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, channel_id, message_content, bot_response, datetime.now().isoformat())
            )
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error in log_conversation: {str(e)}")
            return False
    
    def get_conversation_history(self, user_id, limit=10):
        """Get recent conversation history for a user
        
        This method retrieves the most recent exchanges between a user and the bot.
        It's useful for maintaining context in ongoing conversations and for
        analyzing interaction patterns.
        
        Args:
            user_id (str): The user's Discord ID
            limit (int): Maximum number of exchanges to return
            
        Returns:
            list: List of conversation exchanges in chronological order
        """
        if not self.enabled or not self.conn:
            return []
            
        try:
            cursor = self.conn.cursor()
            
            cursor.execute(
                "SELECT * FROM conversation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            
            history = []
            for row in cursor.fetchall():
                history.append(dict(row))
                
            # Return in chronological order (oldest first)
            return list(reversed(history))
        except sqlite3.Error as e:
            logger.error(f"Error in get_conversation_history: {str(e)}")
            return []
    
    def get_memory_summary(self, user_id):
        """Get a summary of key user memories for context
        
        This method creates a formatted summary of important information about a user,
        including their profile, preferences, important facts, and tracked wallets.
        This summary is used by the LLM to provide personalized responses.
        
        Args:
            user_id (str): The user's Discord ID
            
        Returns:
            str: A formatted summary of user memories
        """
        if not self.enabled or not self.conn:
            return ""
            
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return ""
                
            # Get key memories
            facts = self.get_memories(user_id, memory_type="fact")
            preferences = self.get_memories(user_id, memory_type="preference")
            wallet_info = self.get_memories(user_id, memory_type="wallet_info")
            wallets = self.get_user_wallets(user_id)
            
            # Construct summary
            summary = f"User: {profile['username']} (interactions: {profile['interactions_count']})\n\n"
            
            if facts:
                summary += "Important facts:\n"
                for fact in facts[:5]:  # Limit to 5 most recent facts
                    summary += f"- {fact['topic']}: {fact['content']}\n"
                summary += "\n"
            
            if preferences:
                summary += "Preferences:\n"
                for pref in preferences[:5]:  # Limit to 5 most recent preferences
                    summary += f"- {pref['topic']}: {pref['content']}\n"
                summary += "\n"
            
            if wallet_info:
                summary += "Wallet information:\n"
                for info in wallet_info[:5]:  # Limit to 5 most recent wallet info
                    summary += f"- {info['topic']}: {info['content']}\n"
                summary += "\n"
            
            if wallets:
                summary += "Tracked wallets:\n"
                for wallet in wallets:
                    nickname = f" ({wallet['nickname']})" if wallet['nickname'] else ""
                    summary += f"- {wallet['wallet_address']} on {wallet['network']}{nickname}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error in get_memory_summary: {str(e)}")
            return ""