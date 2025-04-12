"""
Database Agent
Manages data persistence and updates application records.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from ..database import db_manager

logger = logging.getLogger(__name__)

class DatabaseAgent:
    """Agent responsible for database operations."""

    def __init__(self):
        """Initialize the Database Agent."""
        logger.info("Database Agent initialized")

    def update_application(self, email_data: Dict[str, Any]):
        """Update or add an application in the database."""
        try:
            # Extract the necessary information from email_data
            company = email_data.get('company')
            role = email_data.get('role')
            status = email_data.get('status', 'Pending')

            # If company or role is missing, we can't update
            if not company or not role:
                return {'result': 'error', 'message': 'Missing company or role'}

            # Use the database manager to update the application
            result = db_manager.update_application_from_email({
                'company': company,
                'role': role,
                'status': status,
                'job_type': email_data.get('job_type', 'Remote'),
                'country': email_data.get('country', 'Unknown'),
                'source': email_data.get('source', 'Email'),
                'date_applied': email_data.get('date_applied', datetime.now().strftime('%Y-%m-%d'))
            })

            return result
        except Exception as e:
            logger.error(f"Error updating application: {str(e)}")
            return {'result': 'error', 'message': str(e)}

    def get_all_applications(self):
        """Get all applications from the database."""
        return db_manager.get_all_applications()

    def get_application_by_company_role(self, company, role):
        """Get an application by company and role."""
        try:
            conn = db_manager.get_db_connection()
            cursor = conn.execute(
                "SELECT * FROM applications WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)",
                (company, role)
            )
            application = cursor.fetchone()
            conn.close()
            return application
        except Exception as e:
            logger.error(f"Error getting application: {str(e)}")
            return None
