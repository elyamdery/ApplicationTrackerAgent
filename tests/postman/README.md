# Postman Tests for Application Tracker

This directory contains Postman tests for the Application Tracker API.

## Getting Started

1. Install [Postman](https://www.postman.com/downloads/)
2. Import the collection file `application_tracker_collection.json`
3. Make sure the Application Tracker server is running on `http://localhost:8080`

## Test Cases

The collection includes the following test cases:

1. **Get All Applications**: Tests the GET endpoint to retrieve all applications
2. **Create Application**: Tests the POST endpoint to create a new application
3. **Get Application by ID**: Tests the GET endpoint to retrieve a specific application by ID

## How to Run Tests

1. Open Postman
2. Import the collection
3. Click on the "Runner" button
4. Select the "Application Tracker API Tests" collection
5. Click "Start Run"

## Adding Tests

To add tests to the requests, you can use the "Tests" tab in Postman. Here's an example of a test for the "Get All Applications" request:

```javascript
// Example test to be added
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response is an array", function () {
    var jsonData = pm.response.json();
    pm.expect(Array.isArray(jsonData.applications)).to.be.true;
});
```

## Recording Test Execution

The collection includes utility functions for recording test execution. These functions allow you to save API responses and logs in unique folders for each test.

### Global Variables

The collection sets the following global variables:

- `USE_UNIQUE_FOLDERS`: Whether to create a unique folder for each test (default: true)
- `RESPONSE_DIR`: Directory where responses will be saved (default: 'postman_responses')
- `LOG_DIR`: Directory where logs will be saved (default: 'postman_logs')

### Utility Functions

The collection includes the following utility functions:

- `saveResponseToFile(testName, useUniqueFolder, baseDir)`: Saves the current response to a file
- `logToFile(testName, message, level, useUniqueFolder, baseDir)`: Logs a message to a file

### Using the Utility Functions

Here's an example of how to use the utility functions in a test:

```javascript
// Get the test name
const testName = pm.info.requestName;

// Log the start of the test
eval(pm.globals.get('logToFile'))(testName, 'Test started', 'info', pm.globals.get('USE_UNIQUE_FOLDERS'), pm.globals.get('LOG_DIR'));

// Run your tests...

// Save the response to a file
eval(pm.globals.get('saveResponseToFile'))(testName, pm.globals.get('USE_UNIQUE_FOLDERS'), pm.globals.get('RESPONSE_DIR'));

// Log the end of the test
eval(pm.globals.get('logToFile'))(testName, 'Test completed', 'info', pm.globals.get('USE_UNIQUE_FOLDERS'), pm.globals.get('LOG_DIR'));
```

### Running with Newman

When running the collection with Newman, you can use the `--export-environment` option to save the environment variables and the `--reporters` option to generate reports:

```bash
newman run application_tracker_collection.json --export-environment environment.json --reporters cli,json,html --reporter-json-export results/json-report.json --reporter-html-export results/html-report.html
```

## Learning Resources

- [Postman Learning Center](https://learning.postman.com/)
- [Writing Tests in Postman](https://learning.postman.com/docs/writing-scripts/test-scripts/)
- [Postman API Testing Best Practices](https://blog.postman.com/api-testing-best-practices/)
