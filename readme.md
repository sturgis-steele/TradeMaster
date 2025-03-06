# TradeMaster Discord Bot

A proactive, AI-powered Discord bot for a trading community, offering wallet tracking, market analysis, trade critique, and conversational assistance.

## Features

- **AI-Powered Conversations**: Uses Groq's powerful LLMs to provide intelligent responses to any trading question
- **Proactive Engagement**: Monitors all messages in real-time and interjects naturally when relevant
- **Specialized Tools**:
  - **Wallet Tracking**: Monitor blockchain wallets and receive alerts for significant activity
  - **Market Trend Analysis**: Get insights on market trends, sentiment, and price data
  - **Trade Critique**: Receive feedback and analysis on your trading decisions
  - **Conversational AI**: Ask questions about trading concepts, terminology, and strategies
- **Context-Aware Responses**: Maintains conversation history to provide consistent and relevant answers

## Setup

### Prerequisites

- Python 3.9+
- Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))
- Groq API Key (for LLM functionality, get one from [Groq Cloud](https://console.groq.com/))
- Optional: Open Operator installation (for web browsing capabilities)
- API Keys (optional but recommended):
  - Etherscan API Key (for wallet tracking)
  - BSCScan API Key (for BSC wallet tracking)
  - CoinGecko API Key (for market data)
  - Alpha Vantage API Key (for stock data)

## Note on Dependencies

This project has been configured to work without requiring the `etherscan-python` package which may cause installation issues. Instead, the bot uses direct API calls to Etherscan services.

If you encounter any dependency issues during installation, please check the following:

1. Try installing with Poetry: `poetry install`
2. If using pip, try: `pip install -r requirements.txt`
3. For specific package issues, you can install them individually

### Installation

#### Using Poetry (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/trademaster-bot.git
   cd trademaster-bot
   ```

2. Install dependencies with Poetry:

   ```bash
   # Install Poetry if you haven't already
   # curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install

   # Activate the virtual environment
   poetry shell
   ```

3. Create a `.env` file in the `config` directory:

   ```bash
   mkdir -p config
   touch config/.env
   ```

4. Add your API keys to the `.env` file:

   ```
   # Required
   DISCORD_TOKEN=your_discord_bot_token

   # Optional but recommended
   ETHERSCAN_API_KEY=your_etherscan_api_key
   BSCSCAN_API_KEY=your_bscscan_api_key
   COINGECKO_API_KEY=your_coingecko_api_key
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   NEWSAPI_KEY=your_newsapi_key
   ```

5. Create necessary directories:
   ```bash
   mkdir -p data
   ```

#### Using Pip (Alternative)

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/trademaster-bot.git
   cd trademaster-bot
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Follow steps 3-5 from the Poetry installation instructions above.

### Running the Bot

#### With Poetry

Start the bot with:

```bash
# Make sure you're in the Poetry shell
poetry run python main.py
```

#### With Pip

Start the bot with:

```bash
python main.py
```

#### Production Deployment

For production deployment, consider:

##### Process Manager (PM2)

Using Poetry with a process manager like PM2:

```bash
pm2 start "poetry run python main.py" --name trademaster
```

##### Systemd Service

Creating a systemd service for automatic startup:

```
[Unit]
Description=TradeMaster Discord Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/trademaster
ExecStart=/path/to/poetry run python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Usage

The bot monitors conversations and responds to both direct calls and relevant discussions:

### Commands

- `/tm help` - Shows help information and example commands
- `/tm reset` - Resets your conversation history with the bot

### Direct Calls

- Reference the bot directly: "Hey TradeMaster, what's the price of BTC?"

### Wallet Tracking

- Track a wallet: "TradeMaster, track this wallet: 0x123..."
- Check balance: "What's the balance of 0x123...?"
- View transactions: "Show me recent transactions for 0x123..."

### Market Analysis

- Price check: "What's the current price of ETH?"
- Sentiment analysis: "What's the sentiment around BTC right now?"
- News: "Any recent news about DOGE?"
- Trend analysis: "What's your analysis of BTC's trend?"

### Trade Critique

- Log entry: "Bought 1 BTC at $45,000"
- Log exit: "Sold 1 BTC at $48,000"
- Complete trade: "Bought 1 BTC at $45,000, sold at $48,000"
- Performance summary: "How am I doing in my trades?"

### Trading Knowledge

- Ask definitions: "What is RSI?"
- Ask concepts: "Explain support and resistance"
- General questions: "How do I manage risk in trading?"

## Architecture

- **main.py**: Entry point and Discord client setup
- **router_new.py**: LangGraph-based AI router for message analysis and tool selection
- **llm_handler.py**: Handler for LLM API interactions with Groq
- **web_operator.py**: Browser automation for Twitter and news without APIs
- **tools/**: Specialized modules for different functionality
  - **wallet.py**: Wallet tracking functionality
  - **trends.py**: Market trend analysis
  - **critique.py**: Trade critique and analysis
  - **conversational.py**: General trading knowledge and conversation
- **data/**: Database and storage
  - **db.py**: SQLite database interface
  - **trademaster.db**: SQLite database
  - **tracked_wallets.json**: Backup of tracked wallets
  - **trade_history.json**: Backup of trade history
  - **trading_knowledge.json**: Knowledge base for trading concepts

## LLM Integration

TradeMaster uses Groq's powerful language models to provide intelligent responses to user queries:

- **Models Available**:

  - `llama3-70b-8192` (default, most capable)
  - `llama3-8b-8192` (faster, less capabilities)
  - `mixtral-8x7b-32768` (good for extended context)

- **AI Features**:

  - Natural language understanding and generation
  - Context-aware responses that maintain conversation flow
  - Intent detection to route to specialized tools when needed
  - Enhancement of tool outputs to sound more natural

- **Conversation Management**:
  - Keeps track of user conversations for contextual responses
  - `/tm reset` command clears conversation history
  - Automatically limits conversation history to maintain performance

## Web Operator Integration

TradeMaster can use [Open Operator](https://github.com/browserbase/open-operator) to browse the web and collect market data without requiring paid APIs. This feature enables:

- **Twitter Sentiment Analysis**: Browse Twitter to collect and analyze sentiment around crypto/stocks
- **News Aggregation**: Find and summarize the latest financial news from various sources

### Setting Up Web Operator

1. Clone and set up Open Operator:

   ```bash
   git clone https://github.com/browserbase/open-operator.git
   cd open-operator
   # Follow Open Operator installation instructions
   ```

2. Configure TradeMaster to use your Open Operator installation:

   ```
   # In config/.env
   WEB_OPERATOR_PATH=./open-operator  # Path to Open Operator installation
   TWITTER_USERNAME=your_twitter_username  # Optional
   TWITTER_PASSWORD=your_twitter_password  # Optional
   ```

3. Web Operator requires:
   - Chromium or Chrome browser
   - NodeJS runtime
   - Follow installation instructions in the Open Operator repository

### Fallback Mechanism

If Web Operator is not available, TradeMaster will automatically fall back to simulated data for sentiment and news, ensuring the bot remains functional even without web browsing capabilities.

## Customization

### Modifying Bot Behavior

- Adjust response frequency in `router_new.py` by modifying the probability values
- Update trading terminology and knowledge in `conversational.py`
- Add new trading concepts to the knowledge base

### Adding New Features

The modular architecture makes it easy to add new tools:

1. Create a new file in the `tools/` directory with a class that has a `process()` method
2. Add the tool to the imports and tool dictionary in `router_new.py`
3. Add detection patterns for the new functionality in the router

## License

[MIT License](LICENSE)

## Contact

For support, feature requests, or contributions, please open an issue on GitHub or contact the project maintainer.
