"""
Selenium tests for the Application Tracker dashboard with screen recording.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import os

# Add the parent directory to the path so we can import the utils package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import BaseTest


class DashboardTest(BaseTest):
    """Test cases for the Application Tracker dashboard with screen recording."""

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        self.driver.get("http://localhost:8080")

    def test_dashboard_loads(self):
        """Test that the dashboard loads correctly."""
        # Start recording explicitly (not needed if RECORD_ALL_TESTS is True)
        self.start_recording()
        
        try:
            # Check that the page title is correct
            self.assertIn("Application Tracker", self.driver.title)
            
            # Check that the status bar is visible
            status_bar = self.wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, "status-bar"))
            )
            self.assertTrue(status_bar.is_displayed())
            
            # Check that the applications table or empty state is visible
            try:
                applications_table = self.wait.until(
                    EC.visibility_of_element_located((By.ID, "applications-table"))
                )
                self.assertTrue(applications_table.is_displayed())
            except:
                # If the table is not found, check for the empty state
                empty_state = self.wait.until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "empty-state"))
                )
                self.assertTrue(empty_state.is_displayed())
        finally:
            # Stop recording explicitly (not needed if RECORD_ALL_TESTS is True)
            self.stop_recording()

    def test_add_application(self):
        """Test adding a new application."""
        # Start recording explicitly (not needed if RECORD_ALL_TESTS is True)
        self.start_recording()
        
        try:
            # Click the "Add Application" button
            add_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "add-application-btn"))
            )
            add_button.click()
            
            # Wait for the modal to appear
            add_modal = self.wait.until(
                EC.visibility_of_element_located((By.ID, "add-modal"))
            )
            self.assertTrue(add_modal.is_displayed())
            
            # Fill in the form
            self.driver.find_element(By.ID, "company").send_keys("Test Company")
            self.driver.find_element(By.ID, "role").send_keys("Test Role")
            self.driver.find_element(By.ID, "date_applied").send_keys("2025-04-15")
            self.driver.find_element(By.ID, "notes").send_keys("Test notes")
            
            # Submit the form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "#add-form button[type='submit']")
            submit_button.click()
            
            # Wait for the page to reload
            time.sleep(2)
            
            # Verify that the new application appears in the table
            applications_table = self.wait.until(
                EC.visibility_of_element_located((By.ID, "applications-table"))
            )
            
            # Assert that the new application is in the table
            self.assertIn("Test Company", applications_table.text)
            self.assertIn("Test Role", applications_table.text)
        finally:
            # Stop recording explicitly (not needed if RECORD_ALL_TESTS is True)
            self.stop_recording()


if __name__ == "__main__":
    import unittest
    unittest.main()
