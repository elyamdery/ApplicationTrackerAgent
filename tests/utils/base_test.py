"""
Base test class with screen recording functionality.
"""

import unittest
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Import the screen recorder
from .screen_recorder import ScreenRecorder


class BaseTest(unittest.TestCase):
    """
    Base test class that includes screen recording functionality.

    All test classes should inherit from this class to get screen recording
    functionality automatically.
    """

    # Class variable to control whether to record all tests
    RECORD_ALL_TESTS = os.environ.get("RECORD_ALL_TESTS", "False").lower() == "true"

    # Class variable to control the recording directory
    RECORDING_DIR = os.environ.get("RECORDING_DIR", "../recordings")

    # Class variable to control whether to use unique folders for each test
    USE_UNIQUE_FOLDERS = os.environ.get("USE_UNIQUE_FOLDERS", "False").lower() == "true"

    def setUp(self):
        """Set up the test environment."""
        # Initialize the Chrome driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service)
        self.driver.maximize_window()

        # Initialize the screen recorder
        self.recorder = ScreenRecorder(
            output_dir=self.RECORDING_DIR,
            use_unique_folders=self.USE_UNIQUE_FOLDERS
        )

        # Start recording if RECORD_ALL_TESTS is True
        if self.RECORD_ALL_TESTS:
            self.recorder.start_recording(self._testMethodName)

        # Wait for elements
        self.wait = WebDriverWait(self.driver, 10)

    def tearDown(self):
        """Clean up after the test."""
        # Stop recording if it's still running
        if hasattr(self, 'recorder') and self.recorder.recording:
            video_path = self.recorder.stop_recording()
            print(f"Test recording saved to: {video_path}")

        # Close the browser
        if hasattr(self, 'driver'):
            self.driver.quit()

    def start_recording(self):
        """
        Start recording the screen.

        This method can be called explicitly in test methods when
        RECORD_ALL_TESTS is False but you want to record specific tests.
        """
        if not self.recorder.recording:
            self.recorder.start_recording(self._testMethodName)

    def stop_recording(self):
        """
        Stop recording the screen.

        This method can be called explicitly in test methods when
        you want to stop recording before the test ends.
        """
        if self.recorder.recording:
            return self.recorder.stop_recording()
        return None
