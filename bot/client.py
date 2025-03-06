# TradeMaster Discord Bot - Client Implementation
# This file creates the main bot client that connects to Discord and processes messages.
# It initializes the Discord connection, sets up permissions (intents), and creates the router
# that analyzes messages and determines which tools to use for responses.
#
# File Interactions:
# - main.py: Creates an instance of TradeMasterClient and starts it
# - commands.py: Registered through setup_commands() method
# - events.py: Registered through setup_events() method
# - core/router_new.py: Instantiated as self.router for message processing
# - discord.ext.commands: Extends the commands.Bot class
# - utils/logging.py: Uses logger configuration

# Import necessary libraries
import discord          # The main Discord API library
import asyncio          # For asynchronous operations (allows the bot to do multiple things at once)
import logging          # For logging information, warnings, and errors
from discord.ext import commands  # Discord's command framework for easier command handling
from core.router_new import Router     # Our LangGraph-based message router that determines how to respond

# Set up logging to track what the bot is doing
logger = logging.getLogger("TradeMaster.Client")

# Set up Discord permissions (called "intents")
# Intents tell Discord what types of data our bot wants to receive
intents = discord.Intents.default()  # Start with default permissions
intents.messages = True              # We want to see messages in channels
intents.message_content = True       # We need to read what the messages say
intents.guilds = True                # We need information about the Discord servers (guilds)

class TradeMasterClient(commands.Bot):
    """
    The main bot client that handles Discord connections and message processing.
    Extends Discord's Bot class to add our custom functionality.
    """
    def __init__(self):
        # Initialize the Discord bot with our prefix and permissions
        # We still keep a minimal command prefix for essential system commands
        # but most interaction will be through natural language processing
        super().__init__(command_prefix="/tm ", intents=intents)
        
        # Create our message router that will analyze messages and determine responses
        # The router is the "brain" that decides how to respond to different messages
        # and which tools to use based on natural language understanding
        self.router = Router()
        
        # Set up a cooldown system to prevent the bot from responding too frequently
        # This dictionary tracks when the bot last responded in each channel
        self.cooldowns = {}  # Format: {channel_id: last_response_time}
        
        # Import and set up minimal commands and event handlers
        # We import these here to avoid circular imports
        from bot.commands import setup_commands  # Only essential system commands
        from bot.events import setup_events      # Events are Discord events the bot responds to
        
        # Register event handlers with this bot instance
        # Most functionality will come through the router's tool selection
        # rather than explicit commands
        setup_commands(self)  # Sets up minimal system commands
        setup_events(self)    # Sets up event handlers like when messages are received
        
        # Log that initialization is complete
        logger.info("TradeMaster client initialized with LangGraph-style tool selection")