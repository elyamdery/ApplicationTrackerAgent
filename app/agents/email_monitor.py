"""
Email Monitor Agent
Responsible for monitoring and processing application-related emails.
"""

import base64
import re
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class EmailMonitorAgent:
    """Agent responsible for monitoring and processing emails."""

    def __init__(self, gmail_service):
        """Initialize the Email Monitor Agent."""
        self.gmail_service = gmail_service
        self.last_check_time = datetime.now()
        logger.info(f"Email Monitor Agent initialized at {self.last_check_time}")

    def scan_emails(self, lookback_days: int = 7, target_email: str = None) -> List[Dict[str, Any]]:
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

    def dump_email_for_debugging(self, email_data, folder="email_dumps"):
        """Save email content to file for debugging purposes"""
        try:
            # Create dump folder if it doesn't exist
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            # Generate filename based on subject and date
            safe_subject = re.sub(r'[^\w\-_]', '_', email_data['subject'])[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{folder}/{timestamp}_{safe_subject}.txt"
            
            # Write email content to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"SUBJECT: {email_data['subject']}\n")
                f.write(f"FROM: {email_data['sender']}\n")
                f.write(f"DATE: {email_data['date']}\n")
                f.write(f"ID: {email_data['id']}\n")
                f.write("\n---- BODY ----\n\n")
                f.write(email_data['body'])
            
            logger.info(f"Dumped email content to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error dumping email: {str(e)}")
            return None
