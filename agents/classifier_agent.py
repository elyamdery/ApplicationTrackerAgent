"""
Classifier Agent
Analyzes email content to determine email type and intent.
"""

from typing import Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ClassifierAgent:
    """Agent responsible for classifying emails."""

    def __init__(self):
        """Initialize the Classifier Agent."""
        logger.info("Classifier Agent initialized")

    def classify_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the email and extract relevant information.
        Args:
            email: The email to classify
        Returns:
            A dictionary with classification results
        """
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()

        # Determine the status based on the email content
        status = 'Pending'
        if 'interview' in body:
            status = 'Interview'
        elif 'offer' in body:
            status = 'Offer'
        elif 'rejection' in body:
            status = 'Rejected'

        return {
            'status': status,
            'subject': subject,
            'body': body
        }