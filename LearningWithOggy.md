# Learning Automation Testing with Oggy

Welcome to your personalized automation testing learning journey with Oggy! This README contains our structured learning plan to help you master UI and API testing for the Application Tracker project.

## 👋 Introduction

Hey there! I'm Oggy, your automation testing mentor. Together, we'll explore the world of test automation using Selenium for UI testing and Postman for API testing. We'll also learn how to record test executions to make debugging easier.

## 🎯 Learning Objectives

- Master the fundamentals of test automation
- Write and execute Selenium UI tests with confidence
- Create and run Postman API tests like a pro
- Use screen recording to visualize and debug test execution
- Develop skills in test organization and reporting

## 🛠️ Prerequisites

1. Python 3.7+ installed
2. Postman desktop application installed
3. Chrome browser installed
4. Application Tracker running on localhost:8080

## 📚 Learning Path

### Section 1: Getting Started (Week 1)

#### 1.1 Setup and Introduction

- [ ] Install required dependencies:
  ```bash
  pip install -r tests/requirements.txt
  ```
- [ ] Review the test directory structure
- [ ] Understand the BaseTest class and screen recorder functionality
- [ ] Import the Postman collection into Postman

#### 1.2 Running Your First Tests

- [ ] Run a simple Selenium test:
  ```bash
  python -m tests.selenium.test_dashboard
  ```
- [ ] Run a simple Postman test using the Postman application
- [ ] Review the generated recordings and logs

### Section 2: UI Testing with Selenium (Weeks 2-3)

#### 2.1 Dashboard Tests

- [ ] Implement `test_dashboard_loads()` in `test_dashboard.py`
  - Verify page title
  - Check status bar visibility
  - Verify applications table or empty state
- [ ] Run the test and review the recording
- [ ] Implement `test_add_application()` in `test_dashboard.py`
  - Click the "Add Application" button
  - Fill in the application form
  - Submit the form
  - Verify the new application appears in the table
- [ ] Run the test and review the recording
- [ ] Implement `test_filter_applications()` in `test_dashboard.py`
  - Add applications with different statuses
  - Select a status from the filter dropdown
  - Verify only applications with the selected status are displayed

#### 2.2 Settings Tests

- [ ] Implement `test_settings_page_loads()` in `test_settings.py`
  - Verify page title
  - Check that the email settings tab is active by default
  - Verify primary email field is visible
- [ ] Run the test and review the recording
- [ ] Implement `test_update_email_settings()` in `test_settings.py`
  - Enter a new primary email
  - Toggle the primary email switch
  - Click the Save button
  - Verify success message is displayed
- [ ] Run the test and review the recording
- [ ] Implement `test_navigation_between_tabs()` in `test_settings.py`
  - Click on different tabs
  - Verify the correct content is displayed for each tab

#### 2.3 Guide Tests

- [ ] Implement `test_guide_page_loads()` in `test_guide.py`
  - Verify page title
  - Check that the overview tab is active by default
  - Verify mind map is visible
- [ ] Run the test and review the recording
- [ ] Implement `test_navigation_between_tabs()` in `test_guide.py`
  - Click on different tabs
  - Verify the correct content is displayed for each tab

### Section 3: API Testing with Postman (Weeks 4-5)

#### 3.1 GET Endpoints

- [ ] Implement tests for "Get All Applications" request
  - Verify status code is 200
  - Check that response is JSON
  - Verify response has applications property
  - Check that applications is an array
- [ ] Run the test and review the logs and saved response
- [ ] Implement tests for "Get Application by ID" request
  - Verify status code is 200
  - Check that response is JSON
  - Verify response has the correct application data
- [ ] Run the test and review the logs and saved response

#### 3.2 POST Endpoints

- [ ] Implement tests for "Create Application" request
  - Verify status code is 200
  - Check that response has success property
  - Verify response has id property for the new application
- [ ] Run the test and review the logs and saved response
- [ ] Create a test for error handling (e.g., missing required fields)
  - Submit an invalid request
  - Verify appropriate error response
  - Check error message content

#### 3.3 Advanced API Testing

- [ ] Create environment variables in Postman
- [ ] Set up a test data generation script
- [ ] Implement a test sequence that creates, retrieves, updates, and deletes an application

### Section 4: Advanced Topics (Weeks 6-7)

#### 4.1 Test Data Management

- [ ] Create a test data generator for applications
- [ ] Implement database cleanup after tests
- [ ] Use fixtures for common test data

#### 4.2 Test Reporting

- [ ] Generate HTML reports for Selenium tests
  ```bash
  pytest tests/selenium --html=report.html
  ```
- [ ] Create custom Newman reporters for Postman tests
- [ ] Set up email notifications for test results

#### 4.3 Continuous Integration

- [ ] Create a GitHub Actions workflow for running tests
- [ ] Set up scheduled test runs
- [ ] Implement test result visualization

### Section 5: Project: End-to-End Test Suite (Week 8)

- [ ] Design a comprehensive test suite that combines UI and API tests
- [ ] Implement the test suite with proper setup and teardown
- [ ] Create a detailed test report with screenshots and recordings
- [ ] Present the results and lessons learned

## 📅 Weekly Schedule

### Week 1: Getting Started
- Monday: Setup and introduction
- Wednesday: Run first tests
- Friday: Review and plan next steps

### Week 2: Dashboard Tests
- Monday: Implement dashboard_loads test
- Wednesday: Implement add_application test
- Friday: Implement filter_applications test

### Week 3: Settings and Guide Tests
- Monday: Implement settings tests
- Wednesday: Implement guide tests
- Friday: Review UI testing progress

### Week 4: GET API Tests
- Monday: Implement Get All Applications test
- Wednesday: Implement Get Application by ID test
- Friday: Review API GET testing

### Week 5: POST API Tests
- Monday: Implement Create Application test
- Wednesday: Implement error handling tests
- Friday: Review API POST testing

### Week 6: Advanced Topics Part 1
- Monday: Test data management
- Wednesday: Test reporting
- Friday: Review progress

### Week 7: Advanced Topics Part 2
- Monday: Continuous integration setup
- Wednesday: Scheduled test runs
- Friday: Review progress

### Week 8: Final Project
- Monday-Wednesday: Implement end-to-end test suite
- Friday: Present results and review learning journey

## 📊 Progress Tracking

| Test | Status | Date Completed | Notes |
|------|--------|----------------|-------|
| test_dashboard_loads | Not Started | | |
| test_add_application | Not Started | | |
| test_filter_applications | Not Started | | |
| test_settings_page_loads | Not Started | | |
| test_update_email_settings | Not Started | | |
| test_settings_navigation | Not Started | | |
| test_guide_page_loads | Not Started | | |
| test_guide_navigation | Not Started | | |
| Get All Applications | Not Started | | |
| Create Application | Not Started | | |
| Get Application by ID | Not Started | | |

## 📝 Notes and Questions

Use this section to jot down questions, insights, or challenges as we progress through the learning plan:

1. 
2. 
3. 

## 🔗 Resources

### Selenium Resources
- [Selenium with Python Documentation](https://selenium-python.readthedocs.io/)
- [WebDriver Manager for Python](https://github.com/SergeyPirogov/webdriver_manager)
- [Pytest Documentation](https://docs.pytest.org/en/stable/)

### Postman Resources
- [Postman Learning Center](https://learning.postman.com/)
- [Writing Tests in Postman](https://learning.postman.com/docs/writing-scripts/test-scripts/)
- [Newman Documentation](https://github.com/postmanlabs/newman)

### Screen Recording Resources
- [OpenCV Documentation](https://docs.opencv.org/4.x/index.html)
- [PyAutoGUI Documentation](https://pyautogui.readthedocs.io/en/latest/)

## 💬 Communication

Feel free to ask questions at any time! I'm here to help you learn and grow as a test automation engineer. We'll adjust the pace and focus based on your interests and progress.

Happy testing!

~ Oggy
