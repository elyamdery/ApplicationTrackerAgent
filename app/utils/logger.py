"""
Logger utility for tracking application events
"""

import logging
import os
from datetime import datetime

def setup_logger(name, level=logging.INFO):
    """Set up and return a logger with the given name and level."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger  # Logger already set up
    
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # File handler with date in filename
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_handler = logging.FileHandler(f'logs/app_{date_str}.log')
    
    # Console handler
    console_handler = logging.StreamHandler()
    
    # Set format for handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
