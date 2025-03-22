"""
Notification Agent
Sends real-time alerts and status summaries.
"""

import smtplib
from email.mime.text import MIMEText
from utils.logger import setup_logger

logger = setup_logger(__name__)

class NotificationAgent:
    """Agent responsible for sending notifications."""

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """Initialize the Notification Agent."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        logger.info("Notification Agent initialized")

    def send_email(self, to_address: str, subject: str, body: str):
        """
        Send an email notification.
        Args:
            to_address: The recipient's email address
            subject: The email subject
            body: The email body
        """
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
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")