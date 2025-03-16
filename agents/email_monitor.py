"""
Email Monitor Agent
Responsible for monitoring and processing application-related emails.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils.logger import setup_logger
from services.gmail_service import GmailService

logger = setup_logger(__name__)

class EmailMonitorAgent:
    """Agent responsible for monitoring and processing emails."""

    def __init__(self):
        """Initialize the Email Monitor Agent."""
        self.gmail_service = GmailService()
        self.last_check_time = datetime.now()
        logger.info(f"Email Monitor Agent initialized at {self.last_check_time}")

    async def scan_emails(self, lookback_days: int = 1) -> List[Dict[str, Any]]:
        """
        Scan emails for application-related content.
        Args:
            lookback_days: Number of days to look back
        Returns:
            List of processed emails
        """
        try:
            logger.info(f"Starting email scan for past {lookback_days} days")
            since_date = self.last_check_time - timedelta(days=lookback_days)
            emails = await self.gmail_service.get_recent_emails(since_date)
            
            processed_emails = []
            for email in emails:
                logger.info(f"Processing email: {email['subject']}")
                if self._is_application_related(email):
                    processed_data = await self._process_email(email)
                    processed_emails.append(processed_data)

            self.last_check_time = datetime.now()
            logger.info(f"Email scan complete. Found {len(processed_emails)} relevant emails")
            return processed_emails

        except Exception as e:
            logger.error(f"Error during email scan: {str(e)}")
            raise

    def _is_application_related(self, email: Dict[str, Any]) -> bool:
        """
        Check if an email is application-related.
        """
        keywords = [
            'application',
            'interview',
            'job opportunity',
            'position',
            'offer',
            'rejection'
        ]
        
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        
        return any(keyword in subject or body for keyword in keywords)

    async def _process_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an application-related email.
        """
        # Extract relevant information from the email
        subject = email.get('subject')
        sender = email.get('from')
        body = email.get('body')

        # Determine the status based on the email content
        status = 'Pending'
        if 'interview' in body.lower():
            status = 'Interview'
        elif 'offer' in body.lower():
            status = 'Offer'
        elif 'rejection' in body.lower():
            status = 'Rejected'

        # Check if the application already exists
        conn = get_db_connection()
        cursor = conn.execute('SELECT * FROM applications WHERE company = ? AND role = ?', (sender, subject))
        application = cursor.fetchone()

        if application:
            # Update existing application status
            conn.execute('UPDATE applications SET status = ? WHERE company = ? AND role = ?', (status, sender, subject))
        else:
            # Add new application
            conn.execute('INSERT INTO applications (company, role, job_type, country, source, date_applied, resume_version, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (sender, subject, 'Unknown', 'Unknown', 'Email', datetime.now().strftime('%Y-%m-%d'), subject, status))

        conn.commit()
        conn.close()

        return {
            'subject': subject,
            'date': email.get('date'),
            'sender': sender,
            'body': body,
            'processed_date': datetime.now().isoformat()
        }