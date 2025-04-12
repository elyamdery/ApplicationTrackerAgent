"""
Classifier Agent
Analyzes email content to determine email type and intent.
"""

import re
import logging
import json
from typing import Dict, Any
from datetime import datetime
import openai
from ..config import Config

logger = logging.getLogger(__name__)

class ClassifierAgent:
    """Agent responsible for classifying emails."""

    def __init__(self):
        """Initialize the Classifier Agent."""
        logger.info("Classifier Agent initialized")
        # Set OpenAI API key if available
        if Config.OPENAI_API_KEY:
            openai.api_key = Config.OPENAI_API_KEY

    def classify_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the email and extract relevant information.
        Args:
            email: The email to classify
        Returns:
            A dictionary with classification results
        """
        # First try AI-based classification if API key is available
        if Config.OPENAI_API_KEY:
            ai_result = self.get_application_details_with_ai(email)
            if ai_result and ai_result.get('is_job_related', False):
                return ai_result

        # Fall back to rule-based classification
        app_data = self.classify_email_content(email)
        if app_data:
            return app_data

        # If no classification was successful, return basic info
        subject = email.get('subject', '').lower()
        body = email.get('body', '').lower()
        status = self.determine_email_status(email)

        return {
            'status': status,
            'is_job_related': False,
            'subject': subject,
            'body': body
        }

    def get_application_details_with_ai(self, email_data):
        """Use OpenAI to extract application details from email"""
        try:
            # Skip if OpenAI API key is not set
            if not Config.OPENAI_API_KEY:
                logger.warning("OpenAI API key not set, skipping AI extraction")
                return None

            # Limit text to avoid token limits
            max_chars = 4000
            truncated_text = email_data['body'][:max_chars]

            # Create prompt with email content
            prompt = f"""
Extract job application information from this email.
Subject: {email_data['subject']}
Sender: {email_data['sender']}
Body excerpt:
{truncated_text}

Return ONLY a JSON object with these fields:
1. company: The company name (required)
2. role: The job title/role (required)
3. status: One of [Pending, Rejected, Interview, Assignment, Offer]
4. is_job_related: true/false - is this a job application email?

If you can't determine the company or role, or if this isn't a job-related email, set is_job_related to false.
            """

            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You extract job application details from emails."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more consistent results
                max_tokens=300
            )

            # Parse JSON response
            result_text = response.choices[0].message["content"].strip()
            try:
                # Try to parse as JSON
                result = json.loads(result_text)

                # Validate required fields
                if result.get('is_job_related', False) and result.get('company') and result.get('role'):
                    logger.info(f"AI extracted: {result}")
                    return result
                else:
                    logger.info(f"AI determined email is not job-related or missing info: {result}")
                    return None
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response as JSON: {result_text}")
                return None

        except Exception as e:
            logger.error(f"Error using AI to extract application details: {str(e)}")
            return None

    def determine_email_status(self, email_data):
        """Determine application status from email with improved accuracy"""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        combined_text = subject + ' ' + body

        # Define strong indicator patterns for each status
        status_patterns = {
            'Rejected': [
                r'\b(?:unfortunately|regret|regrettably|not\s+(?:moving|proceeding))\b',
                r'\b(?:not\s+(?:selected|chosen|considered|pursue|proceed|move|shortlisted))\b',
                r'\b(?:other\s+candidates|pursuing\s+other|different\s+direction)\b',
                r'\b(?:suitable\s+match|not\s+suitable|not\s+a\s+fit|position\s+has\s+been\s+filled)\b',
                r'\b(?:your\s+application\s+was\s+not|we\s+will\s+not\s+be)\b',
                r'\bunsuccessful\b',
                r'\breceived\s+a\s+large\s+number\s+of\s+applications\b',
                r'\bcannot\s+proceed\s+with\s+your\s+application\b',
                r'\bthank\s+you\s+for\s+your\s+interest\b.*\bbest\s+wishes\b',  # Common rejection phrase combo
            ],
            'Interview': [
                r'\b(?:interview|schedule\s+a\s+(?:call|meeting)|like\s+to\s+speak|speak\s+with\s+you)\b',
                r'\b(?:next\s+(?:step|stage)|move\s+forward|further\s+discuss|conversation)\b',
                r'\b(?:availability|available\s+for|when\s+(?:are|would)\s+you\s+be)\b.*\b(?:interview|call|meet)\b',
                r'\b(?:set\s+up\s+a|schedule\s+a|arranging\s+a)\b.*\b(?:interview|call|meeting)\b',
                r'\b(?:invite\s+you\s+to|would\s+like\s+to\s+invite)\b',
                r'\b(?:recruiter|hiring\s+manager|team)\s+would\s+like\s+to\b',
                r'\bnext\s+round\b',
                r'\bcall\s+details\b',
                r'\bmeeting\s+invite\b',
                r'\binterview\s+confirmation\b',
            ],
            'Assignment': [
                r'\b(?:assignment|test|challenge|coding\s+(?:challenge|exercise|task)|take-home)\b',
                r'\b(?:technical\s+(?:assessment|task|exercise|challenge)|skills\s+assessment)\b',
                r'\b(?:complete\s+(?:the\s+following|this\s+assignment)|submit\s+(?:a|your))\b',
                r'\b(?:assessment\s+(?:link|details|instructions)|instructions\s+for\s+the\s+assessment)\b',
                r'\b(?:please\s+(?:complete|solve|implement|code))\b',
                r'\b(?:deadline|due\s+(?:date|by|in))\b.*\b(?:assignment|test|challenge|task)\b',
                r'\bproject\s+(?:brief|details|instructions)\b',
                r'\btechnical\s+evaluation\b',
            ],
            'Offer': [
                r'\b(?:job\s+offer|offer\s+(?:letter|details|package)|employment\s+offer)\b',
                r'\b(?:pleased\s+to\s+offer|happy\s+to\s+offer|formal\s+offer|extend\s+an\s+offer)\b',
                r'\b(?:starting\s+(?:date|salary)|compensation\s+package|benefits\s+package)\b',
                r'\b(?:accept\s+(?:this|the|our)\s+offer|offer\s+acceptance|offer\s+of\s+employment)\b',
                r'\b(?:welcome\s+(?:to\s+the\s+team|aboard|onboard)|onboarding\s+process)\b',
                r'\b(?:employment\s+agreement|contract\s+(?:attached|enclosed))\b',
                r'\bcongratulations\b.*\b(?:position|role|joining|selected)\b',
                r'\bwe\s+are\s+(?:pleased|delighted|happy|thrilled)\s+to\b.*\b(?:inform|tell|let\s+you\s+know|advise)\b',
            ]
        }

        # Check for strong status indicators
        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text):
                    logger.info(f"Found status pattern for {status}: {pattern}")
                    return status

        # Fallback to checking for confirmation words if no strong indicators found
        confirmation_patterns = [
            r'\b(?:received|confirm|thank\s+you\s+for|application\s+(?:received|submitted|complete))\b',
            r'\b(?:we\s+have\s+received|has\s+been\s+received|successfully\s+(?:submitted|received))\b',
            r'\b(?:in\s+review|being\s+reviewed|under\s+(?:consideration|review))\b',
            r'\b(?:acknowledge|acknowledging|receipt\s+of)\b',
            r'\b(?:thank\s+you\s+for\s+applying|thanks\s+for\s+your\s+application)\b'
        ]

        for pattern in confirmation_patterns:
            if re.search(pattern, combined_text):
                logger.info(f"Found confirmation pattern: {pattern}")
                return "Pending"

        # If all else fails, default to Pending
        logger.info("No status patterns found, defaulting to Pending")
        return "Pending"

    def classify_email_content(self, email_data):
        """Determine if email contains job application info with STRICT criteria"""
        try:
            subject = email_data.get('subject', '').lower()
            body = email_data.get('body', '').lower()
            combined_text = subject + ' ' + body

            # REQUIRE STRICT CONFIRMATION PATTERNS - must have these specific phrases
            job_application_confirmations = [
                # Very explicit application confirmations
                r'thank\s+you\s+for\s+(?:your|submitting|completing)\s+(?:application|applying)',
                r'(?:your|the)\s+application\s+(?:has\s+been|was)\s+(?:received|submitted|confirmed)',
                r'we\s+(?:have|\'ve)\s+received\s+your\s+application',
                r'application\s+(?:confirmation|received|submitted|complete)',
                r'confirmation\s+of\s+your\s+(?:job|position|role)\s+application',
                r'we\s+are\s+currently\s+reviewing\s+your\s+application',
                r'your\s+interest\s+in\s+(?:the|this|our)\s+(?:position|role|job|opportunity)',
                r'in\s+response\s+to\s+your\s+(?:recent|job)\s+application',
                r'thank\s+you\s+for\s+expressing\s+interest\s+in\s+(?:the|this|our)\s+(?:position|role|vacancy)'
            ]

            # Check if ANY of the strict patterns match
            is_job_application = False
            matching_pattern = None

            for pattern in job_application_confirmations:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    is_job_application = True
                    matching_pattern = pattern
                    break

            # If no strict pattern matched, this is NOT a job application
            if not is_job_application:
                logger.info(f"Email does not match any strict job application patterns: {subject}")
                return None

            logger.info(f"Found job application confirmation pattern: {matching_pattern}")

            # Extract company name with better filtering
            company_name = self.extract_company_name(email_data)
            if not company_name:
                logger.info(f"Could not extract company name from confirmed job application: {subject}")
                return None

            # Validate company name is not an invalid value
            invalid_companies = ['linkedin', 'update', 'alert', 'notification', 'message',
                               'tel aviv', 'new york', 'reminder', 'news']
            if any(inv.lower() in company_name.lower() for inv in invalid_companies):
                logger.info(f"Skipping invalid company name: {company_name}")
                return None

            # Company name must be at least 3 chars and not be a single letter
            if len(company_name) < 3:
                logger.info(f"Company name too short: {company_name}")
                return None

            # Extract role with fallback
            role = self.extract_role(email_data) or "Position"

            # Determine status
            status = self.determine_email_status(email_data)

            # Create application data
            app_data = {
                'company': company_name,
                'role': role,
                'status': status,
                'email_id': email_data['id'],
                'email_date': email_data['date'],
                'job_type': 'Remote',
                'country': 'Unknown',
                'source': 'Email',
                'date_applied': self.parse_date(email_data['date']),
                'is_job_related': True
            }

            logger.info(f"Classified email as {status} for {company_name}, role: {role}")
            return app_data

        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}")
            logger.exception("Classification error details:")
            return None

    def extract_company_name(self, email_data):
        """Extract company name from email data"""
        # Try to extract from sender first
        sender = email_data.get('sender', '')
        if '@' in sender:
            domain = sender.split('@')[1].split('.')[0]
            if domain and domain not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud']:
                return domain.capitalize()

        # Try to extract from subject
        subject = email_data.get('subject', '')
        # Look for patterns like "Application for [role] at [company]"
        at_company_match = re.search(r'at\s+([A-Z][A-Za-z0-9\s&]+)', subject)
        if at_company_match:
            return at_company_match.group(1).strip()

        # Look for patterns like "[Company] - Application Received"
        company_prefix_match = re.search(r'^([A-Z][A-Za-z0-9\s&]+)[\s\-:]+', subject)
        if company_prefix_match:
            return company_prefix_match.group(1).strip()

        # Try to find a company name in the body
        body = email_data.get('body', '')
        company_patterns = [
            r'from\s+([A-Z][A-Za-z0-9\s&]+)',
            r'team\s+at\s+([A-Z][A-Za-z0-9\s&]+)',
            r'([A-Z][A-Za-z0-9\s&]+)\s+team',
            r'([A-Z][A-Za-z0-9\s&]+)\s+recruitment',
            r'([A-Z][A-Za-z0-9\s&]+)\s+careers',
            r'([A-Z][A-Za-z0-9\s&]+)\s+hiring'
        ]

        for pattern in company_patterns:
            match = re.search(pattern, body)
            if match:
                return match.group(1).strip()

        # If all else fails, try to extract from sender email domain
        if '@' in sender:
            domain = sender.split('@')[1]
            if '.' in domain:
                company = domain.split('.')[0]
                if company not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud']:
                    return company.capitalize()

        return None

    def extract_role(self, email_data):
        """Extract role/position from email data"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')

        # Look for patterns like "Application for [role]"
        role_patterns = [
            r'application\s+for\s+([A-Za-z0-9\s&]+)\s+(?:at|position|role)',
            r'your\s+application\s+for\s+(?:the\s+)?([A-Za-z0-9\s&]+)\s+(?:position|role)',
            r'(?:position|role):\s+([A-Za-z0-9\s&]+)',
            r'(?:position|role)\s+of\s+([A-Za-z0-9\s&]+)',
            r'applying\s+for\s+(?:the\s+)?([A-Za-z0-9\s&]+)\s+(?:position|role)'
        ]

        # Try subject first
        for pattern in role_patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Then try body
        for pattern in role_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no specific patterns match, try to extract from subject
        if 'application' in subject.lower():
            # Remove common prefixes/suffixes
            cleaned_subject = re.sub(r'^.*?application\s+(?:for|confirmation):\s*', '', subject, flags=re.IGNORECASE)
            cleaned_subject = re.sub(r'\s+at\s+.*$', '', cleaned_subject, flags=re.IGNORECASE)

            if cleaned_subject and cleaned_subject != subject:
                return cleaned_subject.strip()

        return None

    def parse_date(self, date_str):
        """Parse date string into YYYY-MM-DD format"""
        try:
            # Try different date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', '%d %b %Y %H:%M:%S %z']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If standard formats fail, try more flexible parsing
            if ',' in date_str and ':' in date_str:
                parts = date_str.split(',', 1)[1].strip().split()
                if len(parts) >= 3:
                    day = parts[0]
                    month = parts[1]
                    year = next((p for p in parts if len(p) == 4 and p.isdigit()), None)
                    if day and month and year:
                        return f"{year}-{self.month_to_number(month):02d}-{int(day):02d}"

            # Default to today if parsing fails
            return datetime.now().strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d')

    def month_to_number(self, month_str):
        """Convert month name to number"""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_str.lower()[:3], 1)
