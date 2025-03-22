"""
Database Agent
Manages data persistence and updates application records.
"""

import sqlite3
from typing import Dict, Any
from utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

class DatabaseAgent:
    """Agent responsible for database operations."""

    def __init__(self):
        """Initialize the Database Agent."""
        logger.info("Database Agent initialized")

    def get_db_connection(self):
        """Get a connection to the database."""
        conn = sqlite3.connect('job_applications.db')
        conn.row_factory = sqlite3.Row
        return conn

    def update_application(self, email_data: Dict[str, Any]):
        """Update or add an application in the database."""
        try:
            # Extract the necessary information from email_data
            company = email_data.get('company')
            role = email_data.get('role')
            status = email_data.get('status', 'Pending')
            
            # ISSUE: 'from' is a reserved keyword in Python
            # Change any usage of email_data['from'] to email_data['sender']
            sender = email_data.get('sender')  # Use 'sender' instead of 'from'
            
            # If company or role is missing, we can't update
            if not company or not role:
                return {'result': 'error', 'message': 'Missing company or role'}
            
            # Current date for status updates
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Connect to database
            conn = self.get_db_connection()
            
            # Check if application already exists
            cursor = conn.execute(
                "SELECT * FROM applications WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)", 
                (company, role)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Only update if status is different
                if existing['status'] != status:
                    conn.execute("""
                        UPDATE applications 
                        SET status = ?, status_date = ?
                        WHERE id = ?
                    """, (status, today, existing['id']))
                    conn.commit()
                    return {'result': 'updated', 'id': existing['id']}
                else:
                    return {'result': 'no_change', 'id': existing['id']}
            else:
                # Insert new application
                conn.execute("""
                    INSERT INTO applications (
                        company, role, job_type, country, source, date_applied, 
                        resume_version, status, status_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company,
                    role,
                    email_data.get('job_type', 'Remote'),
                    email_data.get('country', 'Unknown'),
                    email_data.get('source', 'Email'),
                    email_data.get('date_applied', today),
                    '1.0',  # Default resume version
                    status,
                    today
                ))
                conn.commit()
                cursor = conn.execute("SELECT last_insert_rowid()")
                last_id = cursor.fetchone()[0]
                return {'result': 'inserted', 'id': last_id}
        except Exception as e:
            logger.error(f"Error updating application: {str(e)}")
            return {'result': 'error', 'message': str(e)}
        finally:
            if 'conn' in locals() and conn:
                conn.close()