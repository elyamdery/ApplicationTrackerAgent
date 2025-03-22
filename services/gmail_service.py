"""
Gmail Service
Handles interactions with the Gmail API.
"""

import os
import pickle
from typing import List, Dict, Any
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from utils.logger import setup_logger

logger = setup_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = 'token.pickle'

class GmailService:
    """Service to interact with Gmail API."""

    def __init__(self, creds: Credentials = None):
        """Initialize the Gmail Service."""
        self.creds = creds
        self.service = None
        if creds:
            self._build_service()
        else:
            logger.warning("GmailService initialized without credentials. Ensure they are provided later.")

    def _build_service(self):
        """Build the Gmail service."""
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail service built successfully with provided credentials")
        except Exception as e:
            logger.error(f"Error building Gmail service: {str(e)}")
            raise

    async def get_recent_emails(self, since_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch recent emails since the given date.
        Args:
            since_date: datetime to start fetching emails from
        Returns:
            List of email data dictionaries
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Ensure credentials are provided.")
        try:
            query = f'after:{int(since_date.timestamp())}'
            results = self.service.users().messages().list(
                userId='me',
                q=query
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                email = self._process_message(msg['id'])
                if email:
                    emails.append(email)

            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise

    def _process_message(self, msg_id: str) -> Dict[str, Any]:
        """Process a single email message."""
        try:
            msg_data = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            return {
                'id': msg_data['id'],
                'threadId': msg_data['threadId'],
                'subject': self._get_header(msg_data, 'Subject'),
                'from': self._get_header(msg_data, 'From'),
                'date': self._get_header(msg_data, 'Date'),
                'body': self._get_body(msg_data)
            }

        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {str(e)}")
            return None

    def _get_header(self, msg_data: Dict[str, Any], header_name: str) -> str:
        """Extract a header value from the message data."""
        headers = msg_data['payload']['headers']
        return next(
            (header['value'] for header in headers if header['name'].lower() == header_name.lower()),
            ''
        )

    def _get_body(self, msg_data: Dict[str, Any]) -> str:
        """Extract the email body."""
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    return self._decode_body(part['body'].get('data', ''))
        elif 'body' in msg_data['payload']:
            return self._decode_body(msg_data['payload']['body'].get('data', ''))
        return ''

    def _decode_body(self, data: str) -> str:
        """Decode base64 email body."""
        import base64
        if not data:
            return ''
        return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8')