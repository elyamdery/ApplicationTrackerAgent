"""
Configuration Module
Handles all configuration settings for the application.
"""

import os
import secrets
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Email settings
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    MONITORED_EMAIL = os.getenv('MONITORED_EMAIL', 'elyam.work@gmail.com')
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Google API settings
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/oauth2callback')
    
    # Flask settings
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Database settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'job_applications.db')
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'oauth_flow.log')
    
    # Google API scopes
    GOOGLE_API_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    # Token storage
    TOKEN_PATH = os.getenv('TOKEN_PATH', 'token.pickle')
    CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', 'credentials.json')
    
    # Email scanning settings
    EMAIL_LOOKBACK_DAYS = int(os.getenv('EMAIL_LOOKBACK_DAYS', 30))
    
    # Only set this environment variable in development, NEVER in production
    OAUTHLIB_INSECURE_TRANSPORT = os.getenv('OAUTHLIB_INSECURE_TRANSPORT', '1')
    
    @classmethod
    def configure_logging(cls):
        """Configure logging for the application"""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
