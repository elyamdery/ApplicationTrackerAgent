"""Selenium dashboard tests with screen recording."""

import os
import time
from datetime import datetime

import pytest

if os.getenv('CI') == 'true':
    pytest.skip("UI tests are disabled in CI", allow_module_level=True)

pytest.importorskip("selenium")

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from tests.utils.base_test import BaseTest


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
            self.assertIn("Job Applications Tracker", self.driver.title)
            
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
            # Fill in the inline form to add an application
            unique_company = f"Test Company {datetime.now().strftime('%H%M%S')}"
            form = self.wait.until(EC.visibility_of_element_located((By.ID, "application-form")))

            company_input = self.driver.find_element(By.ID, "company")
            company_input.clear()
            company_input.send_keys(unique_company)

            Select(self.driver.find_element(By.ID, "role")).select_by_index(0)
            Select(self.driver.find_element(By.ID, "job_type")).select_by_value("Remote")

            country_input = self.driver.find_element(By.ID, "country")
            country_input.clear()
            country_input.send_keys("IL")

            today_checkbox = self.driver.find_element(By.ID, "today")
            if not today_checkbox.is_selected():
                today_checkbox.click()

            Select(self.driver.find_element(By.ID, "source")).select_by_index(0)

            submit_button = form.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()

            # Form triggers a reload on success; wait for the DOM to refresh
            self.wait.until(EC.staleness_of(form))

            self.wait.until(
                EC.text_to_be_present_in_element(
                    (By.ID, "applications-table"),
                    unique_company
                )
            )

            table_text = self.driver.find_element(By.ID, "applications-table").text
            self.assertIn(unique_company, table_text)
        finally:
            # Stop recording explicitly (not needed if RECORD_ALL_TESTS is True)
            self.stop_recording()


if __name__ == "__main__":
    import unittest
    unittest.main()
