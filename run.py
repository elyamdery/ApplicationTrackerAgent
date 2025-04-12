"""
Application Entry Point
Starts the Flask web server.
"""

import os
import sys
import logging

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.web.app import create_app
from app.config import Config

# Configure logging
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Create the Flask application
    app = create_app()

    # Run the application
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8080, debug=True)
