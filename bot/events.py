# TradeMaster Discord Bot - Event Handlers
# This file manages Discord event listeners for the TradeMaster bot.
# It handles events like when the bot connects to Discord and when messages are received.
# The event handlers process incoming messages, apply cooldowns for proactive messages,
# and route messages to the appropriate response handlers.
#
# File Interactions:
# - client.py: Events are registered here through setup_events()
# - router_new.py: Messages are sent to Router.analyze() for processing
# - logging.py: Uses logging configuration for event tracking
# - langgraph: Used for workflow management and conversation state
# - tools/*: Various tool modules are used by the router to process messages

import discord  # Library for interacting with Discord
import asyncio   # Library for handling asynchronous operations (doing multiple things at once)
import logging   # Library for recording what the bot is doing

# Set up a logger to keep track of what happens in the bot
logger = logging.getLogger("TradeMaster.Events")

def setup_events(bot):
    """This function sets up all the event handlers for the bot.
    
    Event handlers are like the bot's senses - they detect when something happens on Discord
    (like receiving a message) and tell the bot how to respond.
    """
    
    @bot.event
    async def on_ready():
        """This function runs when the bot successfully connects to Discord.
        
        It's like the bot's 'morning routine' when it wakes up and gets ready for the day.
        """
        # Record information about the bot's login in the log file
        logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
        logger.info(f'Connected to {len(bot.guilds)} guilds')  # A guild is Discord's term for a server
        
        # Set the bot's status message that users will see in Discord
        # This makes the bot appear as "Watching the markets 📈"
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="the markets 📈"
        ))
        
        # Log that everything is ready to go
        logger.info("TradeMaster is ready!")

    @bot.event
    async def on_message(message):
        """This function runs every time the bot sees a new message on Discord.
        
        It's like the bot's ears and brain - it hears a message and decides if and how to respond.
        """
        # First, check if the message starts with the bot's command prefix (like '!' or '$')
        # If it does, it might be a direct command for the bot (like '!help')
        # These are typically used for system-level commands, while most trading features
        # use natural language (regular conversation)
        if message.content.startswith(bot.command_prefix):
            await bot.process_commands(message)  # Handle it as a command
            return  # Stop processing this message further
            
        # Ignore messages that the bot itself sent
        # This prevents the bot from responding to itself and creating infinite loops
        if message.author == bot.user:
            return
            
        try:
            # Get information about where the message came from
            channel_id = str(message.channel.id)  # The unique ID of the Discord channel
            current_time = asyncio.get_event_loop().time()  # The current time (used for cooldowns)
            
            # Send the message to the bot's "router" - this is the brain of the bot
            # The router reads the message, understands what the user wants,
            # and decides which trading tools or features to use to respond
            # 
            # It returns two things:
            # 1. response: What the bot should say back (if anything)
            # 2. is_proactive: Whether this is the bot volunteering information (True)
            #    or directly answering a question (False)
            response, is_proactive = await bot.router.analyze(message)
            
            # If the bot has something to say in response...
            if response:
                # For proactive messages (where the bot volunteers information without being asked),
                # we need to check the cooldown timer to avoid spamming the channel
                if is_proactive:
                    # Check if we've sent a proactive message to this channel recently
                    if channel_id in bot.cooldowns:
                        last_time = bot.cooldowns[channel_id]  # When we last sent a message
                        # If it's been less than 10 minutes (600 seconds), don't send another one
                        if current_time - last_time < 600:  # 10 minutes in seconds
                            logger.debug(f"Skipping proactive message due to cooldown in channel {channel_id}")
                            return
                    
                    # If we do send a message, update the cooldown timer for this channel
                    # This starts the 10-minute countdown before we can send another proactive message
                    bot.cooldowns[channel_id] = current_time
                
                # Make the bot appear to be "typing" before sending the response
                # This makes the interaction feel more natural and human-like
                async with message.channel.typing():
                    # For longer responses, we type longer (seems more realistic)
                    # We calculate the delay based on message length, but cap it at 3 seconds
                    typing_delay = min(len(response) / 100, 3)  # Max 3 seconds
                    await asyncio.sleep(typing_delay)  # Wait for the calculated time
                
                # Finally, send the response message to the Discord channel
                await message.channel.send(response)
                
                # Log that we responded, including where the message was sent
                # (either a server name or DM for direct message)
                logger.info(f"Responded to message in {message.guild.name if message.guild else 'DM'} - {message.channel.name if hasattr(message.channel, 'name') else 'DM'}")
        
        except Exception as e:
            # If anything goes wrong while processing the message, log the error
            # This helps with troubleshooting when the bot doesn't work as expected
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    # Log that all the event handlers have been set up successfully
    # This is the last step in the bot's initialization process
    logger.info("Event handlers registered")