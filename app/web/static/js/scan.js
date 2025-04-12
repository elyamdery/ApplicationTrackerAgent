document.addEventListener('DOMContentLoaded', function() {
    const scanNowBtn = document.getElementById('scan-now-btn');
    const scanSpinner = document.getElementById('scan-spinner');
    const scanText = document.getElementById('scan-text');
    const scanStatus = document.getElementById('scan-status');
    const connectionDot = document.getElementById('connection-dot');
    const lastScanSpan = document.getElementById('last-scan');
    
    // Function to check scan status
    function checkScanStatus() {
        fetch('/scan_status')
            .then(response => response.json())
            .then(data => {
                // Update last scan time
                if (lastScanSpan && data.last_scan_time) {
                    lastScanSpan.textContent = `Last scan: ${data.last_scan_time}`;
                }
                
                // Handle active scanning
                if (data.is_scanning) {
                    if (scanNowBtn) scanNowBtn.disabled = true;
                    if (scanSpinner) scanSpinner.style.display = 'inline-block';
                    if (scanText) scanText.textContent = 'Scanning...';
                    if (scanStatus) {
                        scanStatus.textContent = 'Scanning emails...';
                        scanStatus.className = 'status-text scanning';
                    }
                    
                    // Check again in 2 seconds
                    setTimeout(checkScanStatus, 2000);
                } else {
                    // Scan completed or not running
                    if (scanNowBtn) scanNowBtn.disabled = false;
                    if (scanSpinner) scanSpinner.style.display = 'none';
                    if (scanText) scanText.textContent = 'Scan Now';
                    
                    if (data.status === 'completed') {
                        if (scanStatus) {
                            scanStatus.textContent = 'Scan completed successfully!';
                            scanStatus.className = 'status-text success';
                            
                            // Clear status message after 5 seconds
                            setTimeout(() => {
                                scanStatus.textContent = '';
                                scanStatus.className = 'status-text';
                            }, 5000);
                        }
                    } else if (data.status === 'error') {
                        if (scanStatus) {
                            scanStatus.textContent = `Error: ${data.error || 'Unknown error'}`;
                            scanStatus.className = 'status-text error';
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error checking scan status:', error);
                if (scanStatus) {
                    scanStatus.textContent = '';
                }
                if (scanNowBtn) scanNowBtn.disabled = false;
                if (scanSpinner) scanSpinner.style.display = 'none';
                if (scanText) scanText.textContent = 'Scan Now';
            });
    }
    
    // Check status on page load
    checkScanStatus();
    
    // Add click event to scan button
    if (scanNowBtn) {
        scanNowBtn.addEventListener('click', function() {
            // Disable button and show spinner
            scanNowBtn.disabled = true;
            scanSpinner.style.display = 'inline-block';
            scanText.textContent = 'Scanning...';
            
            if (scanStatus) {
                scanStatus.textContent = 'Starting scan...';
                scanStatus.className = 'status-text scanning';
            }
            
            // Call the scan endpoint
            fetch('/scan_now')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Start polling for status updates
                        setTimeout(checkScanStatus, 1000);
                    } else {
                        // Show error message
                        if (scanStatus) {
                            scanStatus.textContent = 'Error: ' + (data.error || 'Failed to start scan');
                            scanStatus.className = 'status-text error';
                        }
                        // Reset button
                        scanText.textContent = 'Scan Now';
                        scanSpinner.style.display = 'none';
                        scanNowBtn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (scanStatus) {
                        scanStatus.textContent = 'Error connecting to server';
                        scanStatus.className = 'status-text error';
                    }
                    // Reset button
                    scanText.textContent = 'Scan Now';
                    scanSpinner.style.display = 'none';
                    scanNowBtn.disabled = false;
                });
        });
    }
});