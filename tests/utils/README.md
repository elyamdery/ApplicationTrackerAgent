# Test Utilities

This directory contains utility classes and functions for test automation.

## Screen Recorder

The `ScreenRecorder` class allows you to record the screen during test execution, making it easier to debug and review tests.

### Features

- Records the screen during test execution
- Runs in a separate thread to avoid blocking the test
- Automatically creates output directories
- Configurable frame rate and video codec
- Saves recordings with test names and timestamps

### Requirements

The screen recorder requires the following Python packages:

- opencv-python
- pyautogui
- numpy

These dependencies are included in the main `requirements.txt` file.

### Usage

#### Basic Usage

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

#### Using with Selenium Tests

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

#### Environment Variables

The `BaseTest` class supports the following environment variables:

- `RECORD_ALL_TESTS`: Set to "true" to automatically record all tests
- `RECORDING_DIR`: Directory where recordings will be saved (default: "../recordings")

Example:

```bash
# Windows
set RECORD_ALL_TESTS=true
set RECORDING_DIR=C:\test_recordings

# Linux/Mac
export RECORD_ALL_TESTS=true
export RECORDING_DIR=/path/to/recordings
```

### Example

See `test_with_recording.py` for a complete example of how to use the screen recorder in a test.

## BaseTest Class

The `BaseTest` class is a base class for Selenium tests that includes screen recording functionality.

### Features

- Initializes the WebDriver
- Sets up the screen recorder
- Provides methods to start and stop recording
- Automatically cleans up resources in tearDown

### Usage

```python
from utils import BaseTest

class MyTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.driver.get("http://localhost:8080")
    
    def test_something(self):
        # Your test code here...
        pass
```
