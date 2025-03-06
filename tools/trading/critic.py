import os
import logging
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from utils.config import load_config
from core.llm import LLMHandler
from tools.market.price import PriceDataFetcher

logger = logging.getLogger("TradeMaster.Tools.Trading.Critic")

class TradeCritic:
    """Analyzes and critiques trading decisions"""
    
    def __init__(self):
        """Initialize the trade critic tool"""
        # Load configuration
        self.config = load_config()
        self.critic_config = self.config.get("tools", {}).get("trade_critique", {})
        
        # Initialize LLM handler for advanced analysis
        self.llm_handler = LLMHandler()
        
        # Initialize price data fetcher
        self.price_fetcher = PriceDataFetcher()
        
        # Load trade patterns and common mistakes
        self.patterns = self._load_patterns()
        self.common_mistakes = self._load_common_mistakes()
        
        logger.info("TradeCritic initialized")
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load trading patterns from JSON file
        
        Returns:
            dict: Trading patterns data
        """
        try:
            with open("data/knowledge/trade_patterns.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Trade patterns file not found or invalid. Using default patterns.")
            return {
                "breakout": {
                    "description": "Price breaking through a resistance level with increased volume",
                    "success_factors": ["Volume confirmation", "Clear resistance level", "Strong momentum"]
                },
                "support_bounce": {
                    "description": "Price bouncing off a support level",
                    "success_factors": ["Previous support test", "Decreasing selling volume", "Bullish candlestick pattern"]
                },
                "trend_following": {
                    "description": "Entering in the direction of the established trend",
                    "success_factors": ["Clear trend direction", "Pullback to moving average", "Continuation pattern"]
                }
            }
    
    def _load_common_mistakes(self) -> Dict[str, Any]:
        """Load common trading mistakes from JSON file
        
        Returns:
            dict: Common trading mistakes data
        """
        try:
            with open("data/knowledge/common_mistakes.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Common mistakes file not found or invalid. Using default mistakes.")
            return {
                "fomo": {
                    "description": "Fear of missing out - buying after a significant price increase",
                    "indicators": ["Buying after 20%+ price increase", "All-time high price", "Extreme bullish sentiment"],
                    "advice": "Wait for a pullback or consolidation before entering"
                },
                "no_stop_loss": {
                    "description": "Trading without a defined stop loss",
                    "indicators": ["No mention of stop loss", "Unclear exit strategy"],
                    "advice": "Always set a stop loss to limit potential losses"
                },
                "position_sizing": {
                    "description": "Improper position sizing relative to account",
                    "indicators": ["Position too large relative to account", "All-in approach"],
                    "advice": "Limit position size to 1-2% of your trading capital per trade"
                }
            }
    
    async def process(self, text: str, message) -> str:
        """Process a trade critique request
        
        Args:
            text (str): The message text
            message: The Discord message object
            
        Returns:
            str: Response to the request
        """
        user_id = str(message.author.id)
        username = message.author.name
        
        # Extract trade information from the message
        trade_info = self._extract_trade_info(text)
        
        if not trade_info:
            return "I couldn't identify a trade to analyze. Please provide details about your trade, including the asset, entry price, exit price, and optionally your strategy or reasoning."
        
        # Analyze the trade
        analysis = await self._analyze_trade(trade_info, user_id, username)
        
        # Format the response
        response = self._format_analysis(trade_info, analysis)
        
        return response
    
    def _extract_trade_info(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract trade information from text
        
        Args:
            text (str): The message text
            
        Returns:
            dict or None: Extracted trade information or None if not found
        """
        # Initialize trade info
        trade_info = {
            "asset": None,
            "entry_price": None,
            "exit_price": None,
            "position_type": None,  # "long" or "short"
            "strategy": None,
            "stop_loss": None,
            "take_profit": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Extract asset (symbol)
        symbol_pattern = r'(?:bought|sold|traded|long|short)\s+(?:some\s+)?([A-Za-z]{2,5})'
        symbol_match = re.search(symbol_pattern, text, re.IGNORECASE)
        
        if symbol_match:
            trade_info["asset"] = symbol_match.group(1).upper()
        else:
            # Try to find any ticker symbol in the text
            ticker_pattern = r'\$?([A-Za-z]{2,5})'
            ticker_matches = re.findall(ticker_pattern, text)
            
            if ticker_matches:
                # Filter out common words that might match the pattern
                common_words = ["bought", "sold", "trade", "price", "from", "with", "this", "that", "when", "what", "long", "short"]
                filtered_matches = [m for m in ticker_matches if m.upper() not in [w.upper() for w in common_words]]
                
                if filtered_matches:
                    trade_info["asset"] = filtered_matches[0].upper()
        
        # Extract prices
        price_pattern = r'(?:at|for|price|from|to)\s+\$?([\d,.]+)'
        price_matches = re.findall(price_pattern, text)
        
        if len(price_matches) >= 2:
            # Assume first is entry, second is exit
            trade_info["entry_price"] = float(price_matches[0].replace(",", ""))
            trade_info["exit_price"] = float(price_matches[1].replace(",", ""))
        elif len(price_matches) == 1:
            # Only one price found, assume it's entry price
            trade_info["entry_price"] = float(price_matches[0].replace(",", ""))
        
        # Determine position type (long or short)
        if "bought" in text.lower() or "long" in text.lower():
            trade_info["position_type"] = "long"
        elif "sold" in text.lower() or "short" in text.lower():
            trade_info["position_type"] = "short"
        elif trade_info["entry_price"] and trade_info["exit_price"]:
            # Infer from prices if not explicitly stated
            trade_info["position_type"] = "long" if trade_info["exit_price"] > trade_info["entry_price"] else "short"
        
        # Extract stop loss and take profit if mentioned
        sl_pattern = r'(?:stop loss|sl)(?:\s+at)?\s+\$?([\d,.]+)'
        sl_match = re.search(sl_pattern, text, re.IGNORECASE)
        if sl_match:
            trade_info["stop_loss"] = float(sl_match.group(1).replace(",", ""))
        
        tp_pattern = r'(?:take profit|tp)(?:\s+at)?\s+\$?([\d,.]+)'
        tp_match = re.search(tp_pattern, text, re.IGNORECASE)
        if tp_match:
            trade_info["take_profit"] = float(tp_match.group(1).replace(",", ""))
        
        # Extract strategy if mentioned
        strategy_patterns = [
            r'(?:using|with|based on)\s+([^.]+)(?:strategy|analysis|indicator|pattern)',
            r'strategy(?:\s+is|:\s+|\s+was)?\s+([^.]+)'
        ]
        
        for pattern in strategy_patterns:
            strategy_match = re.search(pattern, text, re.IGNORECASE)
            if strategy_match:
                trade_info["strategy"] = strategy_match.group(1).strip()
                break
        
        # Validate extracted information
        if not trade_info["asset"] or not trade_info["entry_price"]:
            return None
        
        return trade_info
    
    async def _analyze_trade(self, trade_info: Dict[str, Any], user_id: str, username: str) -> Dict[str, Any]:
        """Analyze a trade
        
        Args:
            trade_info (dict): Trade information
            user_id (str): The user's Discord ID
            username (str): The user's Discord username
            
        Returns:
            dict: Trade analysis
        """
        analysis = {
            "profit_loss": None,
            "profit_loss_percentage": None,
            "risk_reward_ratio": None,
            "identified_pattern": None,
            "mistakes": [],
            "strengths": [],
            "suggestions": [],
            "market_context": None
        }
        
        # Calculate profit/loss if both entry and exit prices are available
        if trade_info["entry_price"] and trade_info["exit_price"]:
            if trade_info["position_type"] == "long":
                analysis["profit_loss"] = trade_info["exit_price"] - trade_info["entry_price"]
                analysis["profit_loss_percentage"] = (analysis["profit_loss"] / trade_info["entry_price"]) * 100
            else:  # short
                analysis["profit_loss"] = trade_info["entry_price"] - trade_info["exit_price"]
                analysis["profit_loss_percentage"] = (analysis["profit_loss"] / trade_info["entry_price"]) * 100
        
        # Calculate risk-reward ratio if stop loss and take profit are available
        if trade_info["stop_loss"] and trade_info["take_profit"] and trade_info["entry_price"]:
            if trade_info["position_type"] == "long":
                risk = trade_info["entry_price"] - trade_info["stop_loss"]
                reward = trade_info["take_profit"] - trade_info["entry_price"]
            else:  # short
                risk = trade_info["stop_loss"] - trade_info["entry_price"]
                reward = trade_info["entry_price"] - trade_info["take_profit"]
            
            if risk > 0:  # Avoid division by zero
                analysis["risk_reward_ratio"] = reward / risk
        
        # Get current market data for context
        if trade_info["asset"]:
            try:
                current_price_data = await self.price_fetcher.get_crypto_price(trade_info["asset"])
                if not current_price_data:
                    current_price_data = await self.price_fetcher.get_stock_price(trade_info["asset"])
                
                if current_price_data:
                    analysis["market_context"] = {
                        "current_price": current_price_data["price_usd"],
                        "24h_change": current_price_data.get("price_change_24h", 0)
                    }
            except Exception as e:
                logger.error(f"Error fetching market data: {str(e)}")
        
        # Identify trading pattern
        if trade_info["strategy"]:
            for pattern_name, pattern_data in self.patterns.items():
                if pattern_name.lower() in trade_info["strategy"].lower():
                    analysis["identified_pattern"] = {
                        "name": pattern_name,
                        "description": pattern_data["description"],
                        "success_factors": pattern_data["success_factors"]
                    }
                    break
        
        # Identify potential mistakes
        if analysis["profit_loss"] is not None and analysis["profit_loss"] < 0:
            # Trade was a loss, check for common mistakes
            for mistake_name, mistake_data in self.common_mistakes.items():
                for indicator in mistake_data["indicators"]:
                    if self._check_mistake_indicator(indicator, trade_info, analysis):
                        analysis["mistakes"].append({
                            "name": mistake_name,
                            "description": mistake_data["description"],
                            "advice": mistake_data["advice"]
                        })
                        break
        
        # Identify strengths
        if trade_info["stop_loss"]:
            analysis["strengths"].append("Used a stop loss to manage risk")
        
        if trade_info["take_profit"]:
            analysis["strengths"].append("Set a take profit target")
        
        if analysis["risk_reward_ratio"] and analysis["risk_reward_ratio"] >= 2:
            analysis["strengths"].append(f"Good risk-reward ratio of {analysis['risk_reward_ratio']:.2f}")
        
        if trade_info["strategy"]:
            analysis["strengths"].append("Used a defined trading strategy")
        
        # Generate suggestions using LLM if available
        if self.llm_handler.api_key:
            suggestions = await self._generate_suggestions_with_llm(trade_info, analysis)
            if suggestions:
                analysis["suggestions"] = suggestions
        else:
            # Basic suggestions without LLM
            analysis["suggestions"] = self._generate_basic_suggestions(trade_info, analysis)
        
        return analysis
    
    def _check_mistake_indicator(self, indicator: str, trade_info: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Check if a mistake indicator applies to the trade
        
        Args:
            indicator (str): The mistake indicator
            trade_info (dict): Trade information
            analysis (dict): Trade analysis
            
        Returns:
            bool: True if the indicator applies, False otherwise
        """
        indicator = indicator.lower()
        
        if "no mention of stop loss" in indicator and not trade_info["stop_loss"]:
            return True
        
        if "buying after" in indicator and "price increase" in indicator and trade_info["position_type"] == "long":
            # This would require historical price data to properly check
            # For now, we'll assume it doesn't apply
            return False
        
        if "position too large" in indicator:
            # We don't have position size information
            return False
        
        # Add more indicator checks as needed
        
        return False
    
    async def _generate_suggestions_with_llm(self, trade_info: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
        """Generate trade suggestions using LLM
        
        Args:
            trade_info (dict): Trade information
            analysis (dict): Trade analysis
            
        Returns:
            list: List of suggestions
        """
        # Create a prompt for the LLM
        prompt = [
            {"role": "system", "content": """
            You are a professional trading coach analyzing a trade. Provide 3-5 specific, actionable suggestions 
            to improve the trader's performance based on the trade details provided. Focus on risk management, 
            entry/exit timing, and strategy refinement. Be concise and specific.
            """},
            {"role": "user", "content": f"""
            Trade details:
            - Asset: {trade_info['asset']}
            - Position type: {trade_info['position_type']}
            - Entry price: ${trade_info['entry_price']}
            - Exit price: ${trade_info['exit_price'] if trade_info['exit_price'] else 'Not exited yet'}
            - Stop loss: ${trade_info['stop_loss'] if trade_info['stop_loss'] else 'Not set'}
            - Take profit: ${trade_info['take_profit'] if trade_info['take_profit'] else 'Not set'}
            - Strategy: {trade_info['strategy'] if trade_info['strategy'] else 'Not specified'}
            
            Analysis:
            - Profit/Loss: ${analysis['profit_loss'] if analysis['profit_loss'] is not None else 'N/A'}
            - P/L Percentage: {analysis['profit_loss_percentage'] if analysis['profit_loss_percentage'] is not None else 'N/A'}%
            - Risk/Reward Ratio: {analysis['risk_reward_ratio'] if analysis['risk_reward_ratio'] is not None else 'N/A'}
            
            Based on this trade, provide 3-5 specific, actionable suggestions to improve trading performance.
            Format each suggestion as a separate point. Be concise and specific.
            """
            }
        ]
        
        try:
            # Get LLM response
            response = await self.llm_handler.get_response(prompt)
            
            # Split response into suggestions
            suggestions = []
            for line in response.split('\n'):
                line = line.strip()
                # Skip empty lines and non-suggestion lines
                if not line or not any(line.startswith(c) for c in ['- ', '• ', '* ', '1. ', '2. ', '3. ', '4. ', '5. ']):
                    continue
                
                # Clean up the suggestion
                suggestion = line.lstrip('- •*123456789. ')
                suggestions.append(suggestion)
            
            return suggestions[:5]  # Return up to 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions with LLM: {str(e)}")
            return self._generate_basic_suggestions(trade_info, analysis)
    
    def _generate_basic_suggestions(self, trade_info: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
        """Generate basic trade suggestions without LLM
        
        Args:
            trade_info (dict): Trade information
            analysis (dict): Trade analysis
            
        Returns:
            list: List of suggestions
        """
        suggestions = []
        
        # Risk management suggestions
        if not trade_info["stop_loss"]:
            suggestions.append("Always set a stop loss to protect your capital")
        
        if not trade_info["take_profit"]:
            suggestions.append("Define a clear take profit target before entering trades")
        
        if analysis["risk_reward_ratio"] and analysis["risk_reward_ratio"] < 2:
            suggestions.append("Aim for a minimum risk-reward ratio of 2:1")
        
        # Strategy suggestions
        if not trade_info["strategy"]:
            suggestions.append("Develop and document a clear trading strategy")
        
        # Add market context based suggestions
        if analysis["market_context"]:
            current_price = analysis["market_context"]["current_price"]
            price_change = analysis["market_context"]["24h_change"]
            
            if abs(price_change) > 10:
                suggestions.append("Be cautious of high volatility - consider reducing position size")
        
        # Add general suggestions if we don't have enough
        if len(suggestions) < 3:
            general_suggestions = [
                "Keep a trading journal to track and review your trades",
                "Consider using multiple timeframes for analysis before entering a trade",
                "Wait for confirmation signals before entering a trade",
                "Focus on consistent small wins rather than occasional big wins",
                "Review your trading plan regularly and adjust as needed"
            ]
            
            # Add general suggestions until we have at least 3
            for suggestion in general_suggestions:
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
                    if len(suggestions) >= 3:
                        break
        
        return suggestions[:5]  # Return up to 5 suggestions
    
    def _format_analysis(self, trade_info: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Format the trade analysis into a readable response
        
        Args:
            trade_info (dict): Trade information
            analysis (dict): Trade analysis
            
        Returns:
            str: Formatted analysis response
        """
        lines = ["📊 **Trade Analysis**\n"]
        
        # Trade details
        lines.append("**Trade Details:**")
        lines.append(f"• Asset: {trade_info['asset']}")
        lines.append(f"• Position: {trade_info['position_type'].upper()}")
        lines.append(f"• Entry Price: ${trade_info['entry_price']:,.2f}")
        
        if trade_info["exit_price"]:
            lines.append(f"• Exit Price: ${trade_info['exit_price']:,.2f}")
        
        if trade_info["stop_loss"]:
            lines.append(f"• Stop Loss: ${trade_info['stop_loss']:,.2f}")
        
        if trade_info["take_profit"]:
            lines.append(f"• Take Profit: ${trade_info['take_profit']:,.2f}")
        
        if trade_info["strategy"]:
            lines.append(f"• Strategy: {trade_info['strategy']}")
        
        lines.append("")
        
        # Performance metrics
        if analysis["profit_loss"] is not None:
            profit_loss = analysis["profit_loss"]
            profit_loss_pct = analysis["profit_loss_percentage"]
            
            # Determine emoji based on profit/loss
            emoji = "🟢" if profit_loss > 0 else "🔴" if profit_loss < 0 else "⚪"
            
            lines.append("**Performance:**")
            lines.append(f"• P/L: {emoji} ${profit_loss:,.2f} ({profit_loss_pct:,.2f}%)")
            
            if analysis["risk_reward_ratio"]:
                lines.append(f"• Risk/Reward Ratio: {analysis['risk_reward_ratio']:.2f}")
            
            lines.append("")
        
        # Market context
        if analysis["market_context"]:
            current_price = analysis["market_context"]["current_price"]
            price_change = analysis["market_context"]["24h_change"]
            
            # Determine emoji based on 24h change
            emoji = "🟢" if price_change > 0 else "🔴" if price_change < 0 else "⚪"
            
            lines.append("**Market Context:**")
            lines.append(f"• Current Price: ${current_price:,.2f}")
            lines.append(f"• 24h Change: {emoji} {price_change:,.2f}%")
            lines.append("")
        
        # Trading pattern
        if analysis["identified_pattern"]:
            pattern = analysis["identified_pattern"]
            lines.append("**Pattern Analysis:**")
            lines.append(f"• Pattern: {pattern['name'].title()}")
            lines.append(f"• Description: {pattern['description']}")
            lines.append("• Success Factors:")
            for factor in pattern["success_factors"]:
                lines.append(f"  - {factor}")
            lines.append("")
        
        # Strengths
        if analysis["strengths"]:
            lines.append("**Strengths:**")
            for strength in analysis["strengths"]:
                lines.append(f"✅ {strength}")
            lines.append("")
        
        # Mistakes
        if analysis["mistakes"]:
            lines.append("**Areas for Improvement:**")
            for mistake in analysis["mistakes"]:
                lines.append(f"⚠️ {mistake['description']}")
                lines.append(f"   💡 {mistake['advice']}")
            lines.append("")
        
        # Suggestions
        if analysis["suggestions"]:
            lines.append("**Suggestions:**")
            for suggestion in analysis["suggestions"]:
                lines.append(f"📌 {suggestion}")
        
        return "\n".join(lines)