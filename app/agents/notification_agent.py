"""
Notification Agent
Sends real-time alerts and status summaries.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from ..config import Config

logger = logging.getLogger(__name__)

class NotificationAgent:
    """Agent responsible for sending notifications."""

    def __init__(self, smtp_server=None, smtp_port=None, username=None, password=None):
        """Initialize the Notification Agent."""
        self.smtp_server = smtp_server or Config.SMTP_SERVER
        self.smtp_port = smtp_port or Config.SMTP_PORT
        self.username = username or Config.EMAIL_USERNAME
        self.password = password or Config.EMAIL_PASSWORD
        logger.info("Notification Agent initialized")

    def send_email(self, to_address: str, subject: str, body: str):
        """
        Send an email notification.
        Args:
            to_address: The recipient's email address
            subject: The email subject
            body: The email body
        """
        # Check if SMTP settings are configured
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            logger.error("SMTP settings not configured. Cannot send email.")
            return False

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = to_address

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_address, msg.as_string())
                logger.info(f"Email sent to {to_address}")
                return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
