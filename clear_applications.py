"""
Clear Applications Script
Clears all applications from the database.
"""

import sqlite3
import os
import logging

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

def clear_applications():
    """Clear all applications from the database."""
    try:
        conn = get_db_connection()
        
        # Get the current count of applications
        cursor = conn.execute('SELECT COUNT(*) as count FROM applications')
        row = cursor.fetchone()
        count = row['count'] if row else 0
        
        # Delete all applications
        conn.execute('DELETE FROM applications')
        conn.commit()
        
        logger.info(f"Deleted {count} applications from the database")
        
        # Check if CSV file exists and delete it
        csv_file = 'applications.csv'
        if os.path.exists(csv_file):
            os.remove(csv_file)
            logger.info(f"Deleted {csv_file}")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing applications: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    logger.info("Starting to clear applications")
    success = clear_applications()
    if success:
        logger.info("Successfully cleared all applications")
    else:
        logger.error("Failed to clear applications")
