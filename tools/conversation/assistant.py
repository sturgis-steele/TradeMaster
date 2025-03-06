import os
import re
import logging
import random
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

logger = logging.getLogger("TradeMaster.Tools.Conversation.Assistant")

class ConversationalAI:
    """General conversation functionality for trading discussions"""
    
    def __init__(self):
        """Initialize the conversational AI assistant"""
        # Load trading knowledge base and terminology
        self.knowledge_base = self._load_knowledge_base()
        self.terminology = self._load_terminology()
        
        logger.info("ConversationalAI initialized")
    
    def _load_terminology(self):
        """Load trading terminology from a JSON file"""
        try:
            with open("data/knowledge/trading_terms.json", "r") as f:
                data = json.load(f)
                return data.get("terminology", {})
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("No terminology file found or invalid format. Using default terminology.")
            return {}
        except Exception as e:
            logger.error(f"Error loading terminology: {str(e)}")
            return {}
    
    def _load_knowledge_base(self):
        """Load trading knowledge base from the trading_terms.json file"""
        try:
            with open("data/knowledge/trading_terms.json", "r") as f:
                data = json.load(f)
                return data.get("concepts", {})
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("No knowledge base file found or invalid format. Creating default knowledge base.")
            return self._create_default_knowledge_base()
    
    def _create_default_knowledge_base(self):
        """Create a default trading knowledge base"""
        # Basic trading concepts and explanations
        return {
            "technical_analysis": {
                "support_resistance": "Support and resistance are price levels where an asset historically struggles to fall below (support) or rise above (resistance). These levels form due to market psychology and can be used to identify potential entry and exit points.",
                "moving_averages": "Moving averages smooth out price data to create a single flowing line, making it easier to identify the direction of the trend. The two main types are Simple Moving Average (SMA) and Exponential Moving Average (EMA), with the latter giving more weight to recent prices.",
                "rsi": "The Relative Strength Index (RSI) is a momentum oscillator that measures the speed and change of price movements on a scale from 0 to 100. Traditional interpretation is that RSI values above 70 indicate overbought conditions while values below 30 indicate oversold conditions.",
                "macd": "The Moving Average Convergence Divergence (MACD) is a trend-following momentum indicator that shows the relationship between two moving averages of an asset's price. The MACD is calculated by subtracting the 26-period EMA from the 12-period EMA. A nine-day EMA of the MACD, called the 'signal line', is then plotted on top of the MACD, functioning as a trigger for buy and sell signals."
            },
            "market_psychology": {
                "fear_greed": "The Fear and Greed Index measures market sentiment on a scale from extreme fear to extreme greed. It's based on the premise that excessive fear tends to drive prices lower than they should be, while excessive greed tends to drive prices higher than they should be.",
                "market_cycles": "Markets typically move in cycles characterized by accumulation, uptrend (markup), distribution, and downtrend (markdown) phases. Understanding these cycles can help traders position themselves appropriately for each phase.",
                "contrarian_approach": "A contrarian trading approach involves going against prevailing market trends or sentiment, based on the belief that the crowd is usually wrong at market extremes. This might involve buying when others are fearful or selling when others are greedy."
            },
            "risk_management": {
                "position_sizing": "Position sizing refers to determining the appropriate amount of capital to risk on a single trade. A common guideline is to risk no more than 1-2% of your total trading capital on any single position.",
                "stop_loss": "A stop-loss order is designed to limit an investor's potential loss on a position. It automatically exits the position when the price reaches a predetermined level, helping to manage risk and prevent emotional decision-making.",
                "risk_reward": "The risk-reward ratio compares the potential profit of a trade to its potential loss. A general guideline is to aim for trades with a risk-reward ratio of at least 1:2, meaning the potential reward is at least twice the potential risk."
            },
            "trading_strategies": {
                "trend_following": "Trend following strategies aim to capture gains by riding the momentum of an existing trend. These strategies typically use indicators like moving averages to identify and follow the direction of the market trend.",
                "breakout": "Breakout trading involves entering positions when the price breaks through a significant support or resistance level with increased volume. The idea is that once a breakout occurs, there will be enough momentum to continue the price movement in the breakout direction.",
                "mean_reversion": "Mean reversion strategies are based on the idea that prices and returns eventually move back toward their historical average or mean. These strategies involve buying assets when their prices are much lower than their historical averages and selling when they're much higher."
            },
            "crypto_specific": {
                "blockchain_basics": "A blockchain is a distributed ledger technology that records transactions across many computers in a way that ensures no single record can be altered retroactively. This technology underpins cryptocurrencies like Bitcoin and Ethereum.",
                "defi": "Decentralized Finance (DeFi) refers to financial services and applications built on blockchain technology that operate without central authorities like banks. DeFi applications include lending platforms, decentralized exchanges, and yield farming protocols.",
                "tokenomics": "Tokenomics refers to the economic model of a cryptocurrency or token. It includes factors such as the token's utility, supply mechanisms (inflation or deflation), distribution, and incentive structures. Understanding tokenomics is crucial for evaluating the long-term potential of a crypto asset."
            }
        }
    
    async def process(self, text, message):
        """Process a general conversation request
        
        Args:
            text (str): The message text
            message (discord.Message): The Discord message object
            
        Returns:
            str: Response to the request
        """
        # Extract user information
        user_id = str(message.author.id)
        username = message.author.name
        
        # Check if this is a terminology question
        term_match = self._find_terminology_match(text)
        if term_match:
            return self._explain_term(term_match)
        
        # Check if this is a concept explanation request
        concept_match = self._find_concept_match(text)
        if concept_match:
            return self._explain_concept(concept_match)
        
        # Check if this is a general trading question
        if "?" in text and any(word in text.lower() for word in ["trading", "trade", "invest", "market", "crypto", "stock"]):
            return self._answer_trading_question(text)
        
        # Generic response for conversation
        return self._generate_conversation_response(text, user_id, username)
    
    def _find_terminology_match(self, text):
        """Find a matching trading term in the text
        
        Args:
            text (str): The message text
            
        Returns:
            str or None: The matched term or None if no match
        """
        text_lower = text.lower()
        
        # Check for explicit questions about terms
        term_patterns = [
            r"what(?:'s| is) (a |an |the )?([\w\s]+)\?",
            r"explain (a |an |the )?([\w\s]+)",
            r"define (a |an |the )?([\w\s]+)",
            r"meaning of (a |an |the )?([\w\s]+)"
        ]
        
        for pattern in term_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                term = match[1].strip() if isinstance(match, tuple) else match.strip()
                if term in self.terminology:
                    return term
                # Check for partial matches
                for known_term in self.terminology:
                    if term in known_term or known_term in term:
                        return known_term
        
        # Check for direct mentions of terms
        for term in self.terminology:
            if term in text_lower:
                return term
                
        return None
    
    def _explain_term(self, term):
        """Provide an explanation for a trading term
        
        Args:
            term (str): The trading term
            
        Returns:
            str: Explanation of the term
        """
        explanation = self.terminology.get(term, "I don't have information about that term.")
        return f"**{term.title()}**: {explanation}"
    
    def _find_concept_match(self, text):
        """Find a matching trading concept in the text
        
        Args:
            text (str): The message text
            
        Returns:
            tuple or None: (category, concept) or None if no match
        """
        text_lower = text.lower()
        
        for category, concepts in self.knowledge_base.items():
            # Check if category is mentioned
            if category.replace("_", " ") in text_lower:
                # If specific concept is mentioned, return it
                for concept in concepts:
                    if concept.replace("_", " ") in text_lower:
                        return (category, concept)
                # If only category is mentioned, return the first concept
                if concepts:
                    return (category, next(iter(concepts)))
            
            # Check if any concept is mentioned
            for concept in concepts:
                if concept.replace("_", " ") in text_lower:
                    return (category, concept)
        
        return None
    
    def _explain_concept(self, concept_match):
        """Provide an explanation for a trading concept
        
        Args:
            concept_match (tuple): (category, concept)
            
        Returns:
            str: Explanation of the concept
        """
        category, concept = concept_match
        explanation = self.knowledge_base[category][concept]
        
        return f"**{concept.replace('_', ' ').title()}**\n\n{explanation}"
    
    def _answer_trading_question(self, text):
        """Answer a general trading question
        
        Args:
            text (str): The question text
            
        Returns:
            str: Answer to the question
        """
        # This would ideally use the LLM for more dynamic responses
        # For now, we'll use some generic responses based on keywords
        
        text_lower = text.lower()
        
        if "start" in text_lower and ("trading" in text_lower or "invest" in text_lower):
            return "To start trading, I recommend these steps:\n\n1. **Educate yourself** about markets and trading basics\n2. **Start small** with an amount you can afford to lose\n3. **Practice with paper trading** before using real money\n4. **Develop a trading plan** with clear entry/exit criteria\n5. **Keep a trading journal** to track and learn from your trades\n\nWould you like more specific information about any of these steps?"
        
        if "best" in text_lower and ("strategy" in text_lower or "approach" in text_lower):
            return "There's no single 'best' trading strategy as it depends on your goals, risk tolerance, and time commitment. Some popular approaches include:\n\n• **Day Trading**: Opening and closing positions within the same day\n• **Swing Trading**: Holding positions for days to weeks to capture 'swings' in price\n• **Position Trading**: Longer-term approach holding assets for weeks to months\n• **Value Investing**: Buying undervalued assets with strong fundamentals\n\nThe key is finding a strategy that matches your personality and lifestyle."
        
        if "risk" in text_lower and "manage" in text_lower:
            return "Effective risk management is crucial for trading success. Key principles include:\n\n• **Position Sizing**: Limit each trade to 1-2% of your total capital\n• **Stop Losses**: Always use stop losses to limit potential losses\n• **Risk/Reward Ratio**: Aim for at least 1:2 (potential loss vs. potential gain)\n• **Diversification**: Don't put all your capital in one asset or sector\n• **Correlation Awareness**: Be careful of assets that move together\n\nRemember, protecting your capital should be your first priority."
        
        # Generic response for other questions
        return "That's a good question about trading. While I don't have a specific answer prepared, I'd recommend researching reliable sources like investopedia.com or taking structured courses on trading fundamentals. Is there a specific aspect of trading you're interested in learning more about?"