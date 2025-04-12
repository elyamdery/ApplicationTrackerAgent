# Automation Tests for Application Tracker

This directory contains automation tests for the Application Tracker application.

## Test Types

- **Postman Tests**: API tests using Postman
- **Selenium Tests**: UI tests using Selenium WebDriver
- **Screen Recording**: Utility for recording test execution

## Directory Structure

```
tests/
├── postman/
│   ├── application_tracker_collection.json
│   └── README.md
├── selenium/
│   ├── test_dashboard.py
│   ├── test_dashboard_with_recording.py
│   ├── test_settings.py
│   ├── test_guide.py
│   └── README.md
├── utils/
│   ├── screen_recorder.py
│   ├── base_test.py
│   ├── test_with_recording.py
│   └── README.md
├── recordings/  # Created automatically when tests run
└── README.md
```

## Getting Started

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure the Application Tracker server is running on `http://localhost:8080`
3. Follow the instructions in the README files in each subdirectory to set up and run the tests

## Screen Recording

The screen recorder utility allows you to record the screen during test execution, making it easier to debug and review tests.

### Basic Usage

```python
from utils import ScreenRecorder

# Create a recorder instance
recorder = ScreenRecorder()

# Start recording
recorder.start_recording("my_test")

# Perform test actions...

# Stop recording
recorder.stop_recording()
```

### Using with Selenium Tests

The easiest way to use the screen recorder with Selenium tests is to inherit from the `BaseTest` class:

```python
from utils import BaseTest

class MyTest(BaseTest):
    def test_something(self):
        # Recording starts automatically if RECORD_ALL_TESTS is True
        # Otherwise, you can start it explicitly:
        self.start_recording()

        # Your test code here...

        # Stop recording (optional, will be stopped in tearDown if not)
        self.stop_recording()
```

### Using Unique Folders for Each Test

You can configure the screen recorder to save recordings in unique folders for each test:

```python
# Create a recorder with unique folders
recorder = ScreenRecorder(use_unique_folders=True)

# Or set the environment variable
os.environ["USE_UNIQUE_FOLDERS"] = "true"
```

This will create a separate folder for each test, making it easier to organize and review test recordings.

### Environment Variables

The screen recorder supports the following environment variables:

- `RECORD_ALL_TESTS`: Set to "true" to automatically record all tests
- `RECORDING_DIR`: Directory where recordings will be saved
- `USE_UNIQUE_FOLDERS`: Set to "true" to create a unique folder for each test

See the `utils/README.md` file for more details on the screen recorder.

## Postman Test Recording

The Postman tests also support recording test execution in unique folders:

### Global Variables

The Postman collection sets the following global variables:

- `USE_UNIQUE_FOLDERS`: Whether to create a unique folder for each test (default: true)
- `RESPONSE_DIR`: Directory where responses will be saved
- `LOG_DIR`: Directory where logs will be saved

### Utility Functions

The collection includes utility functions for saving responses and logs:

- `saveResponseToFile(testName, useUniqueFolder, baseDir)`: Saves the current response to a file
- `logToFile(testName, message, level, useUniqueFolder, baseDir)`: Logs a message to a file

See the `postman/README.md` file for more details on the Postman test recording.

## Learning Automation Testing

This repository is set up to help you learn automation testing. The test files contain TODO sections that you can implement as you learn.

### Suggested Learning Path

1. **Start with Postman Tests**:
   - Learn about API testing concepts
   - Understand how to use Postman for API testing
   - Implement the tests in the Postman collection

2. **Move on to Selenium Tests**:
   - Learn about UI testing concepts
   - Understand how to use Selenium WebDriver
   - Implement the TODO sections in the Selenium test files

3. **Advanced Topics**:
   - Test data management
   - Test reporting
   - Continuous integration with tests

## Resources for Learning

### API Testing with Postman
- [Postman Learning Center](https://learning.postman.com/)
- [API Testing with Postman (YouTube)](https://www.youtube.com/watch?v=VywxIQ2ZXw4)
- [Postman API Testing Best Practices](https://blog.postman.com/api-testing-best-practices/)

### UI Testing with Selenium
- [Selenium with Python Documentation](https://selenium-python.readthedocs.io/)
- [Selenium WebDriver with Python (YouTube)](https://www.youtube.com/watch?v=Xjv1sY630Uc)
- [Selenium Best Practices](https://www.selenium.dev/documentation/en/guidelines_and_recommendations/)

### General Testing Concepts
- [Test Automation University](https://testautomationu.applitools.com/)
- [Software Testing Help](https://www.softwaretestinghelp.com/)
- [Ministry of Testing](https://www.ministryoftesting.com/)
