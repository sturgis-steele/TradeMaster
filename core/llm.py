import os
import logging
import json
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from utils.config import load_config

# Configure logger for this module
logger = logging.getLogger("TradeMaster.Core.LLM")

# Try to import OpenAI for alternative LLM access
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("OpenAI package not available. Using direct API requests instead.")

class LLMHandler:
    """Handler for LLM API interactions
    
    This class manages all interactions with the Language Learning Model API,
    including processing messages, analyzing intent, and maintaining conversation
    context. It integrates with the memory system to provide personalized responses
    based on user history and preferences.
    """
    
    def __init__(self):
        """Initialize the LLM handler with necessary configurations and connections"""
        # Load configuration settings
        self.config = load_config()
        self.llm_config = self.config.get("llm", {})
        
        # Get API key from environment or config
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables. LLM functionality will be limited.")
        
        # Set up API configuration
        self.api_base = "https://api.groq.com/openai/v1"
        self.model = os.getenv("GROQ_MODEL", self.llm_config.get("model", "llama3-70b-8192"))
        
        # Initialize conversation tracking
        self.conversations = {}  # user_id -> messages mapping
        self.context_window_size = self.llm_config.get("context_window_size", 10)
        
        # Initialize user memory with retry mechanism
        self.user_memory = None
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                from core.memory import UserMemory
                self.user_memory = UserMemory()
                logger.info("User memory system initialized for LLM")
                break
            except ImportError:
                logger.warning("UserMemory module not available for LLM. Long-term memory will be disabled.")
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"Failed to initialize UserMemory after {max_retries} attempts: {str(e)}")
                else:
                    logger.warning(f"Attempt {retry_count} to initialize UserMemory failed: {str(e)}. Retrying...")
                    asyncio.sleep(1)  # Wait before retrying
        
        # System message defining the bot's capabilities
        self.system_message = """
You are TradeMaster, an AI assistant for a trading community Discord server. You have access to several specialized tools:

1. Wallet Tracking: Monitor blockchain wallets and alert users about significant activity.
2. Market Trend Analysis: Provide insights based on price data, social sentiment, and news.
3. Trade Critique: Analyze user trades and offer feedback to improve trading strategies.
4. Trading Knowledge: Answer questions about trading terminology, concepts, and strategies.

Users may ask you general trading questions or request specific actions like tracking a wallet or analyzing a trade.
When responding, be concise, helpful, and focused on trading topics. If users ask about topics outside trading, 
gently redirect the conversation back to trading-related subjects.

Present yourself as knowledgeable but careful about making specific price predictions. Always emphasize risk management.

You also have access to a memory system that stores information about each user. Use this information to personalize 
your responses and maintain context across conversations. Each user may have tracked wallets, preferences, 
and important facts that you should consider when responding.
"""
        
        logger.info("LLM Handler initialized")
    
    async def process_message(self, user_id: str, username: str, message_content: str, channel_id: str = None, channel_name: str = None) -> str:
        """Process a user message and generate an appropriate response
        
        This method handles the core interaction with the LLM. It:
        1. Retrieves user context from memory
        2. Maintains conversation history
        3. Generates appropriate responses
        4. Logs interactions for future context
        
        Args:
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            message_content (str): The user's message content
            channel_id (str, optional): The Discord channel ID
            channel_name (str, optional): The Discord channel name for context
            
        Returns:
            str: The LLM's response
        """
        # Create or update user profile in memory
        user_context = ""
        if self.user_memory:
            self.user_memory.get_user_profile(user_id, username)
            
            # Get memory summary for context
            user_context = self.user_memory.get_memory_summary(user_id)
            if user_context:
                user_context = f"USER CONTEXT:\n{user_context}\n\nRemember this context when replying, but don't explicitly mention having this information unless relevant."
        
        # Initialize conversation for this user if it doesn't exist
        if user_id not in self.conversations:
            system_message = self.system_message
            if user_context:
                system_message = f"{system_message}\n\n{user_context}"
                
            self.conversations[user_id] = [
                {"role": "system", "content": system_message}
            ]
        elif user_context:
            # Update system message with latest user context
            self.conversations[user_id][0]["content"] = f"{self.system_message}\n\n{user_context}"
        
        # Add user message to conversation
        user_message = {"role": "user", "content": message_content}
        if channel_name:
            user_message["name"] = f"{username}_{channel_name}"
        self.conversations[user_id].append(user_message)
        
        # Keep conversation history reasonably sized (system message + context_window_size*2 messages)
        max_history = 1 + (self.context_window_size * 2)  # system + (user/assistant pairs)
        if len(self.conversations[user_id]) > max_history:
            # Always keep system message and last messages
            self.conversations[user_id] = [self.conversations[user_id][0]] + self.conversations[user_id][-(max_history-1):]
        
        try:
            # Get response from LLM
            response_text = await self._call_llm_api(self.conversations[user_id])
            
            # Add response to conversation history
            self.conversations[user_id].append({"role": "assistant", "content": response_text})
            
            # Log conversation in memory system
            if self.user_memory and channel_id:
                self.user_memory.log_conversation(user_id, channel_id, message_content, response_text)
            
            return response_text
        except Exception as e:
            logger.error(f"Error processing message with LLM: {str(e)}")
            # Provide a fallback response
            return "I'm having trouble connecting to my language model at the moment. Please try again later or ask a more specific trading question I can help with directly."
    
    async def analyze_intent(self, text: str) -> Tuple[str, float]:
        """Analyze the intent of a message to determine which tool to use
        
        This method examines the user's message to classify it into one of several intent categories.
        It helps the router determine which specialized tool should handle the request.
        If the LLM API is unavailable, it falls back to the router's simpler detection method.
        
        Args:
            text (str): The user's message content
            
        Returns:
            tuple: (intent_category, confidence_score) where:
                - intent_category is one of: "track_wallet", "market_trend", "trade_critique", or "general"
                - confidence_score is a float between 0 and 1 indicating confidence in the classification
        """
        # If no API key, use a simpler method from the router
        if not self.api_key:
            from core.router_new import Router
            router = Router()
            # Use the analyze_intent method from the new router
            state = {"messages": [{"content": text}], "metadata": {}}
            updated_state = await router._analyze_intent(state)
            intent = updated_state["current_tool"]
            return intent, 0.8  # Arbitrary confidence score
        
        # Create a prompt for intent classification
        prompt = [
            {"role": "system", "content": """
            Analyze the user message and categorize it into exactly one of these intents:
            - track_wallet: For requests related to tracking blockchain wallets, addresses, or transactions.
            - market_trend: For questions about market trends, prices, sentiment, or news.
            - trade_critique: For analyzing trades, entry/exit points, or trading performance.
            - general: For general trading questions, terminology, or concepts that don't fit the other categories.
            
            Respond with a single line containing the intent category and a confidence score between 0 and 1.
            Format: "intent_category|confidence_score"
            Example: "market_trend|0.87"
            """},
            {"role": "user", "content": text}
        ]
        
        try:
            # Get response from LLM
            response_text = await self._call_llm_api(prompt, max_tokens=20)
            
            # Parse the response into intent and confidence
            parts = response_text.strip().split('|')
            if len(parts) == 2:
                intent = parts[0].strip()
                try:
                    confidence = float(parts[1].strip())
                except ValueError:
                    confidence = 0.7  # Default if parsing fails
                
                # Validate intent category
                valid_intents = ["track_wallet", "market_trend", "trade_critique", "general"]
                if intent not in valid_intents:
                    intent = "general"
                
                return intent, confidence
            else:
                # Fallback to general intent with moderate confidence
                return "general", 0.7
                
        except Exception as e:
            logger.error(f"Error analyzing intent with LLM: {str(e)}")
            # Fallback
            return "general", 0.6
    
    async def generate_response_with_tool_output(self, user_id: str, username: str, 
                                               original_message: str, tool_output: str, 
                                               tool_name: str, channel_id: str = None) -> str:
        """Generate a response that incorporates output from a specialized tool
        
        This method takes the raw output from a specialized tool (like wallet tracker or market analyzer)
        and uses the LLM to create a more natural, conversational response that incorporates this information.
        It also maintains conversation history and memory for future interactions.
        
        Args:
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            original_message (str): The user's original message
            tool_output (str): The output from the specialized tool
            tool_name (str): The name of the tool that was used
            channel_id (str, optional): The Discord channel ID
            
        Returns:
            str: The LLM's response incorporating the tool output
        """
        # If no API key, just return the tool output
        if not self.api_key:
            return tool_output
        
        # Create a prompt for generating a response with tool output
        prompt = [
            {"role": "system", "content": f"""
            You are TradeMaster, an AI assistant for traders. A user has asked a question, and one of your specialized 
            tools ({tool_name}) has generated a response. Your task is to provide a natural, conversational response
            that incorporates the tool's output. You can summarize, highlight key points, or add additional context,
            but don't contradict or make up information beyond what the tool provided.
            
            Remember to maintain your trading expertise while being helpful and concise.
            """},
            {"role": "user", "content": f"User message: {original_message}\n\nTool output: {tool_output}"}
        ]
        
        try:
            # Get response from LLM
            response_text = await self._call_llm_api(prompt, max_tokens=600)
            
            # Save this exchange to the conversation history
            if user_id not in self.conversations:
                self.conversations[user_id] = [
                    {"role": "system", "content": self.system_message}
                ]
            
            self.conversations[user_id].append({"role": "user", "content": original_message})
            self.conversations[user_id].append({"role": "assistant", "content": response_text})
            
            # Log conversation in memory system
            if self.user_memory and channel_id:
                self.user_memory.log_conversation(user_id, channel_id, original_message, response_text)
            
            return response_text
                
        except Exception as e:
            logger.error(f"Error generating response with tool output: {str(e)}")
            # Fallback to just returning the tool output
            return tool_output
    
    async def _call_llm_api(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Call the Groq API to get a response
        
        This method handles the actual HTTP request to the LLM API service.
        It formats the request according to the API specifications and handles any errors.
        
        Args:
            messages (list): List of message dictionaries with role and content
            max_tokens (int, optional): Maximum number of tokens in the response
            
        Returns:
            str: The LLM's response text
        """
        if not self.api_key:
            return "LLM integration is not available (missing API key)."
        
        # Prepare API request headers and data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.llm_config.get("temperature", 0.7)
        }
        
        # Define the endpoint URL
        endpoint = f"{self.api_base}/chat/completions"
        
        try:
            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"API error ({response.status}): {error_text}")
                        
                        # Fallback message
                        return "I'm having trouble connecting to my language model at the moment. Please try again later."
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {str(e)}")
            return "I'm having trouble with my connection. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return "I encountered an unexpected error. Please try again later."
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear the conversation history for a user
        
        This method is called when a user requests to reset their conversation.
        It keeps the system message but removes all previous exchanges.
        
        Args:
            user_id (str): The user's Discord ID
            
        Returns:
            bool: True if successfully cleared, False if no conversation existed
        """
        if user_id in self.conversations:
            # Keep only the system message
            self.conversations[user_id] = [self.conversations[user_id][0]]
            return True
        return False