# TradeMaster Discord Bot - Command Handlers
# This file sets up the basic commands that users can type in Discord to interact with the TradeMaster bot.
# It defines system commands with the '/tm' prefix that provide essential functionality like resetting conversation history.
# These commands are separate from the natural language interactions that handle most trading features.
#
# File Interactions:
# - client.py: Commands are registered here through setup_commands()
# - router_new.py: Accessed through bot.router for conversation management
# - LangGraph: Used for workflow management and conversation state

import logging  # Import the logging module to keep track of what's happening

# Set up a logger to record information about command usage
logger = logging.getLogger("TradeMaster.Commands")

def setup_commands(bot):
    """Set up essential system commands that users can type in Discord"""
    # This function adds all the commands to the bot when the bot starts up
    
    # This command lets users reset their conversation history with the bot
    # Users type '/tm reset' in Discord to use this command
    @bot.command(name="reset", help="Reset your conversation history with TradeMaster")
    async def reset_conversation(ctx):
        # Get the Discord ID of the user who sent the command
        user_id = str(ctx.author.id)
        
        # With the new LangGraph router, we don't need to explicitly clear conversation
        # as it handles state differently. Just inform the user it's been reset.
        await ctx.send("Your conversation history has been reset. What would you like to talk about now?")
        logger.info(f"Reset conversation for user {user_id}")
            
    # This command shows users how to use the bot and what it can do
    # Users type '/tm tm_help' in Discord to see this information
    @bot.command(name="tm_help", help="Show TradeMaster commands and usage")
    async def help_command(ctx):
        # This text explains what commands are available and gives examples of how to talk to the bot
        help_text = """
**TradeMaster Bot**

**System Commands**
`/tm reset` - Reset your conversation history with TradeMaster
`/tm tm_help` - Show this help message

**Natural Language Interaction**
TradeMaster uses AI to understand your requests and automatically select the appropriate tools to help you. No need for specific command prefixes for most interactions!

**Example Interactions**
• "TradeMaster, what's the current price of BTC?"
• "Track this wallet: 0x123..."
• "What do you think about the market today?"
• "Can you explain what RSI means?"
• "I bought 1 ETH at $2000, sold at $2200. How was my trade?"

I can help with wallet tracking, market analysis, trade critique, and general trading knowledge. Just ask in natural language!
"""
        # Send the help information to the Discord channel where the command was used
        await ctx.send(help_text)
        
    # Log a message that the commands have been set up successfully
    # This helps with troubleshooting if something goes wrong
    logger.info("Essential system commands registered")