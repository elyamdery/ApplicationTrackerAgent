/**
 * Postman utilities for saving test responses and logs in unique folders.
 * 
 * This file contains utility functions that can be used in Postman tests
 * to save API responses and logs in unique folders for each test.
 */

/**
 * Save the current response to a file in a unique folder.
 * 
 * @param {string} testName - The name of the test
 * @param {boolean} useUniqueFolder - Whether to create a unique folder for this test
 * @param {string} baseDir - The base directory where responses will be saved
 * @returns {Object} - Information about the saved file
 */
function saveResponseToFile(testName, useUniqueFolder = false, baseDir = 'postman_responses') {
    // Create a clean test name (no spaces or special characters)
    const cleanTestName = testName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Generate a timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Determine the directory path
    let dirPath;
    if (useUniqueFolder) {
        dirPath = `${baseDir}/${cleanTestName}`;
        // Create the directory if it doesn't exist
        try {
            pm.visualizer.create(`Creating directory: ${dirPath}`);
        } catch (e) {
            console.log(`Error creating directory: ${e.message}`);
        }
    } else {
        dirPath = baseDir;
    }
    
    // Generate the file name
    const fileName = `${cleanTestName}_${timestamp}.json`;
    const filePath = `${dirPath}/${fileName}`;
    
    // Get the response body
    let responseBody;
    try {
        responseBody = pm.response.json();
    } catch (e) {
        responseBody = {
            error: 'Could not parse response as JSON',
            rawBody: pm.response.text()
        };
    }
    
    // Create an object with response details
    const responseDetails = {
        testName: testName,
        url: pm.request.url.toString(),
        method: pm.request.method,
        timestamp: new Date().toISOString(),
        status: pm.response.status,
        statusCode: pm.response.code,
        responseTime: pm.response.responseTime,
        responseSize: pm.response.size(),
        responseHeaders: pm.response.headers.toJSON(),
        responseBody: responseBody
    };
    
    // Save the response details to a file
    // Note: In Postman, we can't actually write to the file system directly
    // This is a placeholder for the concept - in a real implementation,
    // you would need to use Newman or a custom script to save the files
    console.log(`Response would be saved to: ${filePath}`);
    console.log(JSON.stringify(responseDetails, null, 2));
    
    // In a real implementation, you might use pm.sendRequest to send the data to a server
    // that can save it, or use Newman's reporters when running the collection
    
    return {
        filePath: filePath,
        responseDetails: responseDetails
    };
}

/**
 * Log a message to a file in a unique folder.
 * 
 * @param {string} testName - The name of the test
 * @param {string} message - The message to log
 * @param {string} level - The log level (info, warn, error)
 * @param {boolean} useUniqueFolder - Whether to create a unique folder for this test
 * @param {string} baseDir - The base directory where logs will be saved
 * @returns {Object} - Information about the logged message
 */
function logToFile(testName, message, level = 'info', useUniqueFolder = false, baseDir = 'postman_logs') {
    // Create a clean test name (no spaces or special characters)
    const cleanTestName = testName.replace(/[^a-zA-Z0-9]/g, '_');
    
    // Generate a timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Determine the directory path
    let dirPath;
    if (useUniqueFolder) {
        dirPath = `${baseDir}/${cleanTestName}`;
        // Create the directory if it doesn't exist
        try {
            pm.visualizer.create(`Creating directory: ${dirPath}`);
        } catch (e) {
            console.log(`Error creating directory: ${e.message}`);
        }
    } else {
        dirPath = baseDir;
    }
    
    // Generate the file name
    const fileName = `${cleanTestName}_log_${timestamp}.txt`;
    const filePath = `${dirPath}/${fileName}`;
    
    // Create a log entry
    const logEntry = {
        timestamp: new Date().toISOString(),
        level: level,
        testName: testName,
        message: message
    };
    
    // Format the log entry
    const formattedLogEntry = `[${logEntry.timestamp}] [${logEntry.level.toUpperCase()}] [${logEntry.testName}] ${logEntry.message}`;
    
    // Save the log entry to a file
    // Note: In Postman, we can't actually write to the file system directly
    // This is a placeholder for the concept - in a real implementation,
    // you would need to use Newman or a custom script to save the files
    console.log(`Log would be saved to: ${filePath}`);
    console.log(formattedLogEntry);
    
    // In a real implementation, you might use pm.sendRequest to send the data to a server
    // that can save it, or use Newman's reporters when running the collection
    
    return {
        filePath: filePath,
        logEntry: logEntry,
        formattedLogEntry: formattedLogEntry
    };
}

/**
 * Example of how to use these utilities in a Postman test.
 * 
 * This function demonstrates how to use the saveResponseToFile and logToFile
 * functions in a Postman test.
 * 
 * @param {string} testName - The name of the test
 * @param {boolean} useUniqueFolder - Whether to create a unique folder for this test
 */
function exampleUsage(testName, useUniqueFolder = false) {
    // Log the start of the test
    logToFile(testName, 'Test started', 'info', useUniqueFolder);
    
    // Run the test
    pm.test(testName, function() {
        // Your test code here...
        pm.expect(pm.response.code).to.be.oneOf([200, 201, 202]);
        
        // Log a message during the test
        logToFile(testName, 'Response received', 'info', useUniqueFolder);
        
        // Save the response to a file
        saveResponseToFile(testName, useUniqueFolder);
        
        // Log the end of the test
        logToFile(testName, 'Test completed', 'info', useUniqueFolder);
    });
}

// Export the functions for use in Postman tests
// Note: In Postman, you would need to copy these functions into your test scripts
// or use the Postman Pre-request Script to define them globally
module.exports = {
    saveResponseToFile,
    logToFile,
    exampleUsage
};
