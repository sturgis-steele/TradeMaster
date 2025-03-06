import os
import logging
import logging.handlers
from typing import Optional

def setup_logging(log_file: str = "data/trademaster.log", log_level: int = logging.INFO) -> None:
    """Configure logging for the TradeMaster application
    
    Args:
        log_file (str): Path to the log file
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG)
    """
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler (with rotation)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create TradeMaster logger
    tm_logger = logging.getLogger("TradeMaster")
    tm_logger.setLevel(log_level)
    tm_logger.propagate = True
    
    tm_logger.info("Logging system initialized")

def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """Get a logger with the specified name
    
    Args:
        name (str): Logger name
        log_level (int, optional): Override default log level for this logger
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(f"TradeMaster.{name}")
    
    if log_level is not None:
        logger.setLevel(log_level)
    
    return logger