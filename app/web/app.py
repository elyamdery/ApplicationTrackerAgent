"""
Flask Application
Main entry point for the web application.
"""

import os
import logging
from flask import Flask
from flask.sessions import SecureCookieSessionInterface

# Use relative imports to avoid circular dependencies
from ..config import Config
from ..database import db_manager

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    # Configure logging
    Config.configure_logging()

    # Initialize the database
    db_manager.init_db()

    # Create Flask app
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    # Configure Flask app
    app.secret_key = Config.FLASK_SECRET_KEY
    app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
    app.session_interface = SecureCookieSessionInterface()

    # Import routes here to avoid circular imports
    from .routes import register_routes
    register_routes(app)

    logger.info("Flask application created and configured")
    return app
