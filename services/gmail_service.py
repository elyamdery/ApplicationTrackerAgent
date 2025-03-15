"""
Gmail Service Stub for Testing
"""
from typing import List, Dict, Any
from datetime import datetime

class GmailService:
    """Stub Gmail service for testing"""
    
    async def get_recent_emails(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Stub method returning empty list for now"""
        return []