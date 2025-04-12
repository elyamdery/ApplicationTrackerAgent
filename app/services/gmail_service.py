"""
Gmail Service
Handles authentication and interaction with Gmail API.
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
import base64
import re
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import Config
from ..database import db_manager

logger = logging.getLogger(__name__)

class GmailService:
    """Service for interacting with Gmail API."""

    def __init__(self):
        """Initialize the Gmail Service."""
        self.service = None
        logger.info("Gmail Service initialized")

    def authenticate(self):
        """Authenticate with Gmail API."""
        try:
            logger.info("Starting Gmail authentication")
            creds = None
            token_path = Config.TOKEN_PATH
            credentials_path = Config.CREDENTIALS_PATH

            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                    logger.info("Loaded credentials from token.pickle")
            else:
                logger.warning("No token.pickle file found")

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials")
                        creds.refresh(Request())
                        logger.info("Credentials refreshed successfully")
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials: {str(e)}")
                        creds = None

                if not creds:
                    if not os.path.exists(credentials_path):
                        logger.error(f"No credentials.json file found at {os.path.abspath(credentials_path)}")
                        return None

                    logger.info("Starting new authentication flow")
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, Config.GOOGLE_API_SCOPES)
                    creds = flow.run_local_server(port=8090)

                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("New credentials saved to token.pickle")

            self.service = build('gmail', 'v1', credentials=creds)
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info(f"Successfully authenticated as: {profile.get('emailAddress')}")

            email_address = profile.get('emailAddress')
            db_manager.update_setting('monitored_email', email_address)

            return self.service
        except Exception as e:
            logger.error(f"Error in Gmail authentication: {str(e)}")
            logger.exception("Authentication error details:")
            return None

    def get_service(self):
        """Get the Gmail service, authenticating if necessary."""
        if not self.service:
            self.service = self.authenticate()
        return self.service

    def search_emails(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for emails using the provided query.
        Args:
            query: The search query
            max_results: Maximum number of results to return
        Returns:
            List of message IDs and threads
        """
        try:
            service = self.get_service()
            if not service:
                logger.error("Gmail service not available")
                return []

            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} emails matching query: {query}")
            return messages
        except Exception as e:
            logger.error(f"Error searching emails: {str(e)}")
            return []

    def get_email_content(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the content of an email.
        Args:
            msg_id: The message ID
        Returns:
            Email content as a dictionary
        """
        try:
            service = self.get_service()
            if not service:
                logger.error("Gmail service not available")
                return None

            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = {header['name'].lower(): header['value'] for header in message['payload']['headers']}
            subject = headers.get('subject', '')
            sender = headers.get('from', '')
            date = headers.get('date', '')
            body = self._extract_email_body(message['payload'])

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

    def _extract_email_body(self, payload, body_text=""):
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
                body_text = self._extract_email_body(part, body_text)

        return body_text

    def search_job_application_emails(self, days: int = 30, target_email: str = None) -> List[Dict[str, Any]]:
        """
        Search for job application related emails.
        Args:
            days: Number of days to look back
            target_email: Target email address to search for
        Returns:
            List of email IDs
        """
        try:
            # Get target email if not provided
            if not target_email:
                target_email = db_manager.get_setting('monitored_email', Config.MONITORED_EMAIL)

            # Calculate date range
            today = datetime.now()
            start_date = (today - timedelta(days=days)).strftime('%Y/%m/%d')

            # Create search query
            query = f"to:{target_email} after:{start_date}"

            # Add job application related keywords
            keywords = [
                'application',
                'job',
                'position',
                'interview',
                'offer',
                'rejection',
                'resume',
                'cv',
                'hiring',
                'recruitment',
                'opportunity'
            ]

            # Add keywords to query
            keyword_query = ' OR '.join(f'"{keyword}"' for keyword in keywords)
            query = f"{query} AND ({keyword_query})"

            logger.info(f"Searching for job application emails with query: {query}")
            return self.search_emails(query)
        except Exception as e:
            logger.error(f"Error searching job application emails: {str(e)}")
            return []
