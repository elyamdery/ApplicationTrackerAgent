"""
Check Settings Script
Checks if the settings page is working correctly.
"""

import sqlite3
import os
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a connection to the database."""
    conn = sqlite3.connect('job_applications.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_settings():
    """Check if the settings page is working correctly."""
    try:
        # Check if the database exists
        if not os.path.exists('job_applications.db'):
            logger.error("Database file not found")
            return False
        
        # Check if the settings table exists
        conn = get_db_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            logger.error("Settings table not found")
            conn.close()
            return False
        
        # Check if the monitored_email setting exists
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        if not row:
            logger.error("Monitored email setting not found")
            conn.close()
            return False
        
        monitored_email = row['value']
        logger.info(f"Monitored email: {monitored_email}")
        
        # Check if the additional_email setting exists
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email'")
        row = cursor.fetchone()
        additional_email = row['value'] if row else None
        logger.info(f"Additional email: {additional_email}")
        
        # Check if the primary_email_enabled setting exists
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'primary_email_enabled'")
        row = cursor.fetchone()
        primary_email_enabled = row['value'] if row else None
        logger.info(f"Primary email enabled: {primary_email_enabled}")
        
        # Check if the additional_email_enabled setting exists
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email_enabled'")
        row = cursor.fetchone()
        additional_email_enabled = row['value'] if row else None
        logger.info(f"Additional email enabled: {additional_email_enabled}")
        
        conn.close()
        
        # Try to access the settings page
        response = requests.get('http://localhost:8080/settings')
        if response.status_code != 200:
            logger.error(f"Failed to access settings page: {response.status_code}")
            return False
        
        logger.info("Settings page is accessible")
        
        # Try to update the primary email
        response = requests.post(
            'http://localhost:8080/settings/email',
            json={
                'email': 'elyamworks@gmail.com',
                'type': 'primary',
                'enabled': True
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to update primary email: {response.status_code}")
            return False
        
        logger.info("Primary email updated successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error checking settings: {str(e)}")
        return False

if __name__ == '__main__':
    logger.info("Starting to check settings")
    success = check_settings()
    if success:
        logger.info("Settings are working correctly")
    else:
        logger.error("Settings are not working correctly")
