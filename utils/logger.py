"""
Logger utility for tracking application events
"""

import logging
import os
from datetime import datetime

def setup_logger(name: str):
    """
    Creates a logger with both console and file output
    
    Args:
        name (str): Name of the logger (usually __name__ from the calling module)
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Create logger
    logger = logging.getLogger(name)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # File handler
        file_handler = logging.FileHandler(
            f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger