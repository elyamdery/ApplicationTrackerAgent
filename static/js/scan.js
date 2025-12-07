document.addEventListener('DOMContentLoaded', function() {
    const scanNowBtn = document.getElementById('scan-now-btn');
    const scanSpinner = document.getElementById('scan-spinner');
    const scanText = document.getElementById('scan-text');
    const scanStatus = document.getElementById('scan-status');
    const connectionDot = document.getElementById('connection-dot');
    const lastScanSpan = document.getElementById('last-scan');
    const scanWindowSelect = document.getElementById('scan-window-select');
    const scanLogList = document.getElementById('scan-log-list');
    const scanLogEmptyState = document.getElementById('scan-log-empty');
    const refreshLogsBtn = document.getElementById('refresh-logs');
    const scanUpdatesList = document.getElementById('scan-updates-list');
    const scanUpdatesEmpty = document.getElementById('scan-updates-empty');
    let currentWindow = scanWindowSelect ? scanWindowSelect.value : 'weekly';

    const persistWindowPreference = (windowValue) => {
        fetch('/settings/scan_window', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ window: windowValue })
        }).catch(error => console.error('Failed to persist scan window preference', error));
    };

    function renderScanLogs(logs = []) {
        if (!scanLogList) return;
        scanLogList.innerHTML = '';

        if (!logs.length) {
            if (scanLogEmptyState) scanLogEmptyState.hidden = false;
            return;
        }

        if (scanLogEmptyState) scanLogEmptyState.hidden = true;

        logs.forEach((log) => {
            const li = document.createElement('li');
            const outcomeClass = log.outcome || 'unknown';
            li.className = `scan-log-item outcome-${outcomeClass}`;

            const main = document.createElement('div');
            main.className = 'log-main';
            const subject = document.createElement('p');
            subject.className = 'log-subject';
            subject.textContent = log.subject || 'No subject';
            const meta = document.createElement('p');
            meta.className = 'log-meta';
            meta.textContent = `${log.company || 'Unknown company'} • ${log.role || 'Unknown role'}`;
            main.appendChild(subject);
            main.appendChild(meta);

            const details = document.createElement('div');
            details.className = 'log-details';
            if (log.status) {
                const statusBadge = document.createElement('span');
                statusBadge.className = 'log-status';
                statusBadge.textContent = log.status;
                details.appendChild(statusBadge);
            }
            const outcome = document.createElement('span');
            outcome.className = 'log-outcome';
            outcome.textContent = outcomeClass;
            details.appendChild(outcome);

            const timestamp = document.createElement('span');
            timestamp.className = 'log-timestamp';
            timestamp.textContent = log.created_at || '';
            details.appendChild(timestamp);

            li.appendChild(main);
            li.appendChild(details);

            if (log.reason) {
                const reason = document.createElement('p');
                reason.className = 'log-reason';
                reason.textContent = log.reason;
                li.appendChild(reason);
            }

            scanLogList.appendChild(li);
        });
    }

    function loadScanLogs() {
        if (!scanLogList) return;
        fetch('/scan_logs?limit=10')
            .then(response => response.json())
            .then(data => {
                renderScanLogs(data.logs || []);
            })
            .catch(error => console.error('Failed to load scan logs', error));
    }

    const renderScanUpdates = (updates = []) => {
        if (!scanUpdatesList) return;
        scanUpdatesList.innerHTML = '';

        if (!updates.length) {
            scanUpdatesList.hidden = true;
            if (scanUpdatesEmpty) scanUpdatesEmpty.hidden = false;
            return;
        }

        scanUpdatesList.hidden = false;
        if (scanUpdatesEmpty) scanUpdatesEmpty.hidden = true;

        updates.slice(0, 8).forEach((update) => {
            const li = document.createElement('li');
            const type = update.type || 'other';
            li.className = `scan-update-pill type-${type}`;
            const labelPrefix = type === 'new' ? 'New' : type === 'updated' ? 'Updated' : 'Seen';
            const company = update.company || 'Unknown company';
            const role = update.role || 'Unknown role';
            const status = update.status ? ` · ${update.status}` : '';
            li.textContent = `${labelPrefix}: ${company} - ${role}${status}`;
            scanUpdatesList.appendChild(li);
        });
    };
    
    // Function to check scan status
    function checkScanStatus() {
        fetch('/scan_status')
            .then(response => response.json())
            .then(data => {
                // Update last scan time
                if (lastScanSpan && data.last_scan_time) {
                    lastScanSpan.textContent = `Last scan: ${data.last_scan_time}`;
                }

                if (scanWindowSelect && data.window_days) {
                    const serverWindow = data.window_days <= 1 ? 'daily' : 'weekly';
                    if (scanWindowSelect.value !== serverWindow) {
                        scanWindowSelect.value = serverWindow;
                    }
                    currentWindow = serverWindow;
                }

                renderScanUpdates(Array.isArray(data.updates) ? data.updates : []);
                
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
                            const summary = data.result || 'Scan completed successfully!';
                            scanStatus.textContent = summary;
                            scanStatus.className = 'status-text success';
                            
                            // Clear status message after 5 seconds
                            setTimeout(() => {
                                scanStatus.textContent = '';
                                scanStatus.className = 'status-text';
                            }, 5000);
                        }
                        loadScanLogs();
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
            const windowQuery = currentWindow ? `?window=${encodeURIComponent(currentWindow)}` : '';
            fetch(`/scan_now${windowQuery}`)
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

    if (scanWindowSelect) {
        scanWindowSelect.addEventListener('change', () => {
            currentWindow = scanWindowSelect.value;
            persistWindowPreference(currentWindow);
        });
    }

    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', (event) => {
            event.preventDefault();
            loadScanLogs();
        });
    }

    loadScanLogs();
});