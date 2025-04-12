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

## Learning Resources

- [Postman Learning Center](https://learning.postman.com/)
- [Writing Tests in Postman](https://learning.postman.com/docs/writing-scripts/test-scripts/)
- [Postman API Testing Best Practices](https://blog.postman.com/api-testing-best-practices/)
