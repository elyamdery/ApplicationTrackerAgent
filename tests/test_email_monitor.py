"""
Tests for Email Monitor Agent functionality
"""

import pytest
from datetime import datetime
from agents.email_monitor import EmailMonitorAgent
from utils.screen_recorder import ScreenRecorder # type: ignore

@pytest.fixture
def email_agent():
    """Fixture to create EmailMonitorAgent instance"""
    return EmailMonitorAgent()

@pytest.mark.asyncio
async def test_email_agent_initialization(email_agent):
    """Test EmailMonitorAgent initialization"""
    recorder = ScreenRecorder(output_file='test_email_agent_initialization.avi')
    recorder.start_recording()
    try:
        assert isinstance(email_agent, EmailMonitorAgent)
        assert isinstance(email_agent.last_check_time, datetime)
    finally:
        recorder.stop_recording()

@pytest.mark.asyncio
async def test_scan_emails_return_type(email_agent):
    """Test scan_emails returns correct type"""
    recorder = ScreenRecorder(output_file='test_scan_emails_return_type.avi')
    recorder.start_recording()
    try:
        results = await email_agent.scan_emails(lookback_days=1)
        assert isinstance(results, list)
    finally:
        recorder.stop_recording()

@pytest.mark.asyncio
async def test_scan_emails_with_different_lookback(email_agent):
    """Test scan_emails with different lookback periods"""
    recorder = ScreenRecorder(output_file='test_scan_emails_with_different_lookback.avi')
    recorder.start_recording()
    try:
        one_day = await email_agent.scan_emails(lookback_days=1)
        assert isinstance(one_day, list)
        
        seven_days = await email_agent.scan_emails(lookback_days=7)
        assert isinstance(seven_days, list)
    finally:
        recorder.stop_recording()