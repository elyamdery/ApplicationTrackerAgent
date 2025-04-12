# Selenium Tests for Application Tracker

This directory contains Selenium tests for the Application Tracker web interface.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. Install the required packages:

```bash
pip install selenium webdriver-manager pytest
```

2. Make sure the Application Tracker server is running on `http://localhost:8080`

## Test Files

- `test_dashboard.py`: Tests for the main dashboard
- `test_settings.py`: Tests for the settings page
- `test_guide.py`: Tests for the user guide page

## How to Run Tests

To run all tests:

```bash
pytest tests/selenium
```

To run a specific test file:

```bash
pytest tests/selenium/test_dashboard.py
```

## Test Structure

Each test file follows this structure:

1. **Setup**: Initialize the WebDriver and navigate to the appropriate page
2. **Test Cases**: Individual test methods for specific functionality
3. **Teardown**: Clean up resources after tests

## Writing Tests

When implementing the TODO sections in the test files, follow these guidelines:

1. Use descriptive test method names
2. Use clear assertions with meaningful error messages
3. Use WebDriverWait for elements that may take time to load
4. Keep tests independent of each other

Example of implementing a test:

```python
def test_dashboard_loads(self):
    """Test that the dashboard loads correctly."""
    # Check that the page title is correct
    self.assertEqual("Application Tracker - Dashboard", self.driver.title)
    
    # Check that the status bar is visible
    status_bar = self.wait.until(
        EC.visibility_of_element_located((By.CLASS_NAME, "status-bar"))
    )
    self.assertTrue(status_bar.is_displayed())
    
    # Check that the applications table is visible
    applications_table = self.wait.until(
        EC.visibility_of_element_located((By.ID, "applications-table"))
    )
    self.assertTrue(applications_table.is_displayed())
```

## Learning Resources

- [Selenium with Python Documentation](https://selenium-python.readthedocs.io/)
- [WebDriver Manager for Python](https://github.com/SergeyPirogov/webdriver_manager)
- [Pytest Documentation](https://docs.pytest.org/en/stable/)
- [Selenium Best Practices](https://www.selenium.dev/documentation/en/guidelines_and_recommendations/)
