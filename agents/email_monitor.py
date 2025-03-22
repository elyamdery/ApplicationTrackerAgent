"""
Email Monitor Agent
Responsible for monitoring and processing application-related emails.
"""

import base64
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils.logger import setup_logger
from google.oauth2.credentials import Credentials
from services.gmail_service import GmailService
from utils.database import get_db_connection  # Import the function

logger = setup_logger(__name__)

class EmailMonitorAgent:
    """Agent responsible for monitoring and processing emails."""

    def __init__(self, gmail_service: GmailService):
        """Initialize the Email Monitor Agent."""
        self.gmail_service = gmail_service
        self.db_connection = get_db_connection()
        self.last_check_time = datetime.now()
        logger.info(f"Email Monitor Agent initialized at {self.last_check_time}")

    async def scan_emails(self, lookback_days: int = 7, target_email: str = None) -> List[Dict[str, Any]]:
        """
        Scan emails for application-related content.
        Args:
            lookback_days: Number of days to look back
            target_email: Target email address to search for
        Returns:
            List of processed emails
        """
        try:
            logger.info("Starting scan_emails method")
            # Calculate the date range for the email search
            today = datetime.now()
            start_date = (today - timedelta(days=lookback_days)).strftime('%Y/%m/%d')
            
            # Define the search query
            query = f"to:{target_email} after:{start_date}"
            logger.info(f"Email search query: {query}")
            
            # Execute the search
            results = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails in search")
            
            # Retrieve full email content for each message
            emails = []
            for msg in messages:
                email_data = self.get_email_content(msg['id'])
                if email_data:
                    emails.append(email_data)
                    logger.debug(f"Processed email: {email_data['subject']}")
            
            logger.info(f"Successfully processed {len(emails)} emails")
            return emails
        except Exception as e:
            logger.error(f"Error in scan_emails: {str(e)}")
            return []

    def get_email_content(self, msg_id):
        """Retrieve and parse email content"""
        try:
            message = self.gmail_service.users().messages().get(
                userId='me', 
                id=msg_id, 
                format='full'
            ).execute()
            
            headers = {header['name'].lower(): header['value'] for header in message['payload']['headers']}
            subject = headers.get('subject', '')
            sender = headers.get('from', '')
            date = headers.get('date', '')
            body = self.extract_email_body(message['payload'])
            
            return {
                'id': msg_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body
            }
        except Exception as e:
            logger.error(f"Error retrieving email content for message {msg_id}: {str(e)}")
            return None

    def extract_email_body(self, payload, body_text=""):
        """Extract text from email recursively"""
        if 'body' in payload and 'data' in payload['body'] and payload['body']['data']:
            try:
                data = payload['body']['data']
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                if payload.get('mimeType') == 'text/html':
                    decoded = re.sub(r'<[^>]+>', ' ', decoded)
                    decoded = re.sub(r'\s+', ' ', decoded)
                body_text += decoded
            except Exception as e:
                logger.error(f"Error decoding email part: {str(e)}")
        
        if 'parts' in payload:
            for part in payload['parts']:
                body_text = self.extract_email_body(part, body_text)
        
        return body_text

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