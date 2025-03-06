import os
import logging
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("TradeMaster.Utils.Config")

# Default configuration
DEFAULT_CONFIG = {
    "bot": {
        "command_prefix": "/tm ",
        "status_message": "the markets 📈"
    },
    "llm": {
        "model": "llama3-70b-8192",
        "context_window_size": 10,
        "temperature": 0.7,
        "max_tokens": 500
    },
    "memory": {
        "enabled": True,
        "conversation_timeout": 300,  # 5 minutes
        "max_memory_items": 50
    },
    "router": {
        "proactive_threshold": 0.85,  # Confidence threshold for proactive responses
        "cooldown_period": 600  # 10 minutes between proactive messages
    },
    "tools": {
        "wallet_tracking": {
            "enabled": True,
            "check_interval": 300,  # 5 minutes
            "alert_on_transactions": True
        },
        "market_analysis": {
            "enabled": True,
            "default_timeframe": "1d",
            "cache_expiry": 300  # 5 minutes
        },
        "trade_critique": {
            "enabled": True
        },
        "conversation": {
            "enabled": True
        }
    }
}

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults
    
    Args:
        config_path (str, optional): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    # Load environment variables
    load_dotenv("config/.env")
    
    # Start with default configuration
    config = DEFAULT_CONFIG.copy()
    
    # If config path is provided, try to load it
    if config_path:
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
                
            # Merge user config with defaults (shallow merge for now)
            for key, value in user_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
                    
            logger.info(f"Configuration loaded from {config_path}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading configuration from {config_path}: {str(e)}")
            logger.info("Using default configuration")
    else:
        logger.info("No configuration file provided, using default configuration")
    
    # Override with environment variables if present
    if os.getenv("DISCORD_TOKEN"):
        logger.info("Found DISCORD_TOKEN in environment variables")
    
    if os.getenv("GROQ_API_KEY"):
        logger.info("Found GROQ_API_KEY in environment variables")
    
    if os.getenv("GROQ_MODEL"):
        config["llm"]["model"] = os.getenv("GROQ_MODEL")
        logger.info(f"Using model from environment variables: {config['llm']['model']}")
    
    return config

def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """Save configuration to file
    
    Args:
        config (dict): Configuration dictionary
        config_path (str): Path to save the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {str(e)}")
        return False