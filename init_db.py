"""
Database Initialization Script
Creates the database and tables needed for the application.
"""

import os
import sys
import logging

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app.database.db_manager import init_db

if __name__ == '__main__':
    logger.info("Initializing database")
    init_db()
    logger.info("Database initialization complete")
