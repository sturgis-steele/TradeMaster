-- TradeMaster Database Initialization Script
-- 
-- This script initializes the SQLite database schema for the TradeMaster bot.
-- It creates all necessary tables and indexes for storing wallet tracking data,
-- trade information, user statistics, conversation context, and user preferences.
-- 
-- The schema is designed to support the following core functionalities:
-- 1. Tracking blockchain wallet activity
-- 2. Recording and analyzing trading performance
-- 3. Maintaining user context and preferences
-- 4. Supporting conversation memory for personalized interactions
--
-- Each table has appropriate indexes to optimize query performance.

-- Tracked wallets table
-- Stores information about blockchain wallets being monitored by the bot
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
);

-- Trades table
-- Records individual trading transactions made by users
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
);

-- User statistics table
-- Stores aggregated trading performance metrics for each user
CREATE TABLE IF NOT EXISTS user_stats (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    average_profit_pct REAL DEFAULT 0,
    largest_win_pct REAL DEFAULT 0,
    largest_loss_pct REAL DEFAULT 0,
    last_updated TIMESTAMP
);

-- Context logs table
-- Maintains recent conversation context for each channel
CREATE TABLE IF NOT EXISTS context_logs (
    id INTEGER PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message_content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);

-- User profiles and preferences table
-- Stores user information and preferences as a JSON string
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    interactions_count INTEGER DEFAULT 0,
    preferences TEXT  -- JSON string of user preferences
);

-- User memory table
-- Stores long-term memory items for personalized user interactions
CREATE TABLE IF NOT EXISTS user_memory (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL,  -- 'fact', 'preference', 'interaction'
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    importance INTEGER DEFAULT 1,  -- 1-5 scale of importance
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

-- Create indexes for performance
-- These indexes improve query performance for common access patterns
CREATE INDEX IF NOT EXISTS idx_tracked_wallets_user_id ON tracked_wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_tracked_wallets_wallet_address ON tracked_wallets(wallet_address);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_context_logs_user_id ON context_logs(user_id);