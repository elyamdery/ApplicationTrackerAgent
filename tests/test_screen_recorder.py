"""
Test for Screen Recorder Utility
"""

import pytest
from utils.screen_recorder import ScreenRecorder # type: ignore

@pytest.mark.asyncio
async def test_screen_recorder():
    """Test screen recording functionality"""
    recorder = ScreenRecorder(output_file='test_screen_recorder.avi')
    recorder.start_recording()
    try:
        # Simulate some activity
        import time
        time.sleep(5)  # Record for 5 seconds
    finally:
        recorder.stop_recording()