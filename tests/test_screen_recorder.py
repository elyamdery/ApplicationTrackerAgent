"""Test for Screen Recorder Utility."""

import os
import time

import pytest

from utils.screen_recorder import ScreenRecorder  # type: ignore


pytestmark = pytest.mark.skipif(
    os.getenv('CI') == 'true', reason='Requires desktop capture not available in CI'
)

@pytest.mark.asyncio
async def test_screen_recorder():
    """Test screen recording functionality"""
    recorder = ScreenRecorder(output_file='test_screen_recorder.avi')
    recorder.start_recording()
    try:
        time.sleep(5)  # Record for 5 seconds
    finally:
        recorder.stop_recording()