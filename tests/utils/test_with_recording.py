"""
Example of how to use the screen recorder in a test.
"""

import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import the screen recorder
from screen_recorder import ScreenRecorder


class TestWithRecording(unittest.TestCase):
    """Example test class that uses the screen recorder."""
    
    def setUp(self):
        """Set up the test environment."""
        # Initialize the Chrome driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service)
        self.driver.maximize_window()
        
        # Initialize the screen recorder
        self.recorder = ScreenRecorder(output_dir="../recordings")
        
        # Wait for elements
        self.wait = WebDriverWait(self.driver, 10)
    
    def tearDown(self):
        """Clean up after the test."""
        # Stop recording if it's still running
        if hasattr(self, 'recorder') and self.recorder.recording:
            self.recorder.stop_recording()
        
        # Close the browser
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def test_example_with_recording(self):
        """Example test with screen recording."""
        # Start recording with the test name
        self.recorder.start_recording(self._testMethodName)
        
        try:
            # Navigate to the application
            self.driver.get("http://localhost:8080")
            
            # Wait for the page to load
            self.wait.until(EC.title_contains("Application Tracker"))
            
            # Perform test actions
            # For example, click the "Add Application" button
            add_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "add-application-btn"))
            )
            add_button.click()
            
            # Wait for the modal to appear
            self.wait.until(
                EC.visibility_of_element_located((By.ID, "add-modal"))
            )
            
            # Fill in the form
            self.driver.find_element(By.ID, "company").send_keys("Test Company")
            self.driver.find_element(By.ID, "role").send_keys("Test Role")
            self.driver.find_element(By.ID, "date_applied").send_keys("2025-04-15")
            
            # Submit the form
            self.driver.find_element(By.CSS_SELECTOR, "#add-form button[type='submit']").click()
            
            # Wait for the page to reload
            time.sleep(2)
            
            # Verify that the new application appears in the table
            applications_table = self.wait.until(
                EC.visibility_of_element_located((By.ID, "applications-table"))
            )
            
            # Assert that the new application is in the table
            self.assertTrue(
                "Test Company" in applications_table.text,
                "New application was not added to the table"
            )
            
        finally:
            # Stop recording
            video_path = self.recorder.stop_recording()
            print(f"Test recording saved to: {video_path}")


if __name__ == "__main__":
    unittest.main()
