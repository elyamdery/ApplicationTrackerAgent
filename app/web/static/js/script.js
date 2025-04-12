document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("application-form");

    // Form submission handler
    form.addEventListener("submit", function (event) {
        event.preventDefault();

        // Gather form data
        const formData = {
            company: document.getElementById("company").value.trim(),
            role: document.getElementById("role").value.trim(),
            job_type: document.getElementById("job_type").value.trim(),
            country: document.getElementById("country").value.trim(),
            date_applied: document.getElementById("today").checked 
                ? new Date().toISOString().split("T")[0] 
                : document.getElementById("date_applied").value,
            source: document.getElementById("source").value.trim()
        };

        // Validate all fields are filled
        for (const [key, value] of Object.entries(formData)) {
            if (!value) {
                alert(`Please fill out the ${key.replace('_', ' ')} field!`);
                return;
            }
        }

        // Send data to server
        fetch("/add", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(formData),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert("Application added successfully!");
                form.reset();
                window.location.reload();
            } else {
                alert(data.error || "Error adding application");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Error adding application");
        });
    });

    // Delete button handler
    document.querySelectorAll(".delete-btn").forEach(button => {
        button.addEventListener("click", function () {
            if (confirm("Are you sure you want to delete this application?")) {
                const company = this.getAttribute("data-company");
                const role = this.getAttribute("data-role");

                fetch("/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ company, role }),
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        alert("Application deleted successfully!");
                        window.location.reload();
                    } else {
                        alert(data.error || "Error deleting application");
                    }
                })
                .catch(error => {
                    console.error("Error:", error);
                    alert("Error deleting application");
                });
            }
        });
    });

    // Today checkbox handler
    document.getElementById("today").addEventListener("change", function () {
        const dateField = document.getElementById("date_applied");
        if (this.checked) {
            dateField.value = new Date().toISOString().split("T")[0];
            dateField.disabled = true;
        } else {
            dateField.disabled = false;
        }
    });

    // Search functionality
    document.getElementById("search").addEventListener("keyup", function () {
        const query = this.value.toLowerCase();
        document.querySelectorAll("#applications-table tbody tr").forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(query) ? "" : "none";
        });
    });

    // Export to CSV functionality
    document.getElementById("export-btn").addEventListener("click", function() {
        fetch("/export")
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'job_applications.csv';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error exporting applications');
            });
    });

    // Status change handler
    document.querySelectorAll(".status-select").forEach(select => {
        select.addEventListener("change", function() {
            const company = this.getAttribute("data-company");
            const role = this.getAttribute("data-role");
            const newStatus = this.value;
            const row = this.closest('tr');

            fetch("/update_status", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    company: company,
                    role: role,
                    status: newStatus 
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update row class for styling
                    row.className = `status-${newStatus.toLowerCase()}`;
                } else {
                    alert(data.error || "Error updating status");
                    // Reset select to previous value if update failed
                    this.value = row.className.split('-')[1];
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("Error updating status");
                // Reset select to previous value
                this.value = row.className.split('-')[1];
            });
        });
    });

    // Edit modal functionality
    const modal = document.getElementById("editModal");
    const closeBtn = document.querySelector(".close");

    // Edit button handler
    document.querySelectorAll(".btn-warning").forEach(button => {
        button.addEventListener("click", function() {
            const row = this.closest('tr');
            const company = row.cells[0].textContent;
            const role = row.cells[1].textContent;
            const jobType = row.cells[2].textContent;
            const country = row.cells[3].textContent;
            const dateApplied = row.cells[4].textContent;
            const source = row.cells[5].textContent;

            // Set form values
            document.getElementById("edit-original-company").value = company;
            document.getElementById("edit-original-role").value = role;
            document.getElementById("edit-company").value = company;
            document.getElementById("edit-role").value = role;
            document.getElementById("edit-job_type").value = jobType;
            document.getElementById("edit-country").value = country;
            document.getElementById("edit-date_applied").value = formatDate(dateApplied);
            document.getElementById("edit-source").value = source;

            modal.style.display = "block";
        });
    });

    // Close modal
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    // Edit form submission
    document.getElementById("edit-form").addEventListener("submit", function(event) {
        event.preventDefault();

        const formData = {
            original_company: document.getElementById("edit-original-company").value,
            original_role: document.getElementById("edit-original-role").value,
            company: document.getElementById("edit-company").value,
            role: document.getElementById("edit-role").value,
            job_type: document.getElementById("edit-job_type").value,
            country: document.getElementById("edit-country").value,
            date_applied: document.getElementById("edit-date_applied").value,
            source: document.getElementById("edit-source").value
        };

        // Validate all fields
        for (const [key, value] of Object.entries(formData)) {
            if (!value && !key.startsWith('original_')) {
                alert(`Please fill out the ${key.replace('_', ' ')} field!`);
                return;
            }
        }

        fetch("/edit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert("Application updated successfully!");
                modal.style.display = "none";
                window.location.reload();
            } else {
                alert(data.error || "Error updating application");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Error updating application");
        });
    });

    // Helper function to format date
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toISOString().split('T')[0];
    }

   // Status bar functionality
    const scanBtn = document.getElementById('scan-now-btn');
    const scanText = document.getElementById('scan-text');
    const scanSpinner = document.getElementById('scan-spinner');
    const statusMessage = document.getElementById('status-message');
    const connectionDot = document.getElementById('connection-dot');
    const lastScanEl = document.getElementById('last-scan');
    
    if (scanBtn) {
        scanBtn.addEventListener('click', function() {
            // Show scanning status
            scanBtn.disabled = true;
            scanText.textContent = 'Scanning...';
            scanSpinner.style.display = 'inline-block';
            statusMessage.textContent = 'Scanning emails for new applications...';
            
            // Call the scan endpoint
            fetch('/scan_now')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusMessage.textContent = data.message;
                        lastScanEl.textContent = 'Last scan: Just now';
                        
                        // Reload the page after a delay to show updated applications
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    } else {
                        statusMessage.textContent = 'Error: ' + (data.error || 'Failed to scan');
                        connectionDot.classList.remove('connected');
                        connectionDot.classList.add('disconnected');
                    }
                })
                .catch(error => {
                    statusMessage.textContent = 'Error connecting to server';
                    connectionDot.classList.remove('connected');
                    connectionDot.classList.add('disconnected');
                    console.error('Error:', error);
                })
                .finally(() => {
                    scanBtn.disabled = false;
                    scanText.textContent = 'Scan Now';
                    scanSpinner.style.display = 'none';
                });
        });
    }
    
    // Set today's date when checkbox is clicked
    const todayCheckbox = document.getElementById('today');
    const dateInput = document.getElementById('date_applied');
    
    if (todayCheckbox && dateInput) {
        todayCheckbox.addEventListener('change', function() {
            if (this.checked) {
                const today = new Date();
                const year = today.getFullYear();
                const month = String(today.getMonth() + 1).padStart(2, '0');
                const day = String(today.getDate()).padStart(2, '0');
                dateInput.value = `${year}-${month}-${day}`;
                dateInput.disabled = true;
            } else {
                dateInput.disabled = false;
            }
        });
    }
    
    // Form submission handling
    const applicationForm = document.getElementById('application-form');
    if (applicationForm) {
        applicationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                company: document.getElementById('company').value,
                role: document.getElementById('role').value,
                job_type: document.getElementById('job_type').value,
                country: document.getElementById('country').value,
                date_applied: document.getElementById('date_applied').value,
                source: document.getElementById('source').value,
                resume_version: '1.0', // Default value
                status: 'Pending' // Default status
            };
            
            // Validate all fields are filled
            for (const [key, value] of Object.entries(formData)) {
                if (!value) {
                    alert(`Please fill out the ${key.replace('_', ' ')} field!`);
                    return;
                }
            }
            
            fetch('/add_application', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert("Application added successfully!");
                    applicationForm.reset();
                    window.location.reload();
                } else {
                    alert(data.error || 'Failed to add application');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while adding the application');
            });
        });
    }
    
    // Status change handling
    const statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', function() {
            const company = this.getAttribute('data-company');
            const role = this.getAttribute('data-role');
            const newStatus = this.value;
            const row = this.closest('tr');
            
            fetch('/update_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company: company,
                    role: role,
                    status: newStatus
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update row class for styling
                    row.className = '';
                    row.classList.add('status-' + newStatus.toLowerCase());
                } else {
                    alert(data.error || 'Failed to update status');
                    // Reset select to previous value if update failed
                    this.value = row.className.split('-')[1];
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating the status');
                // Reset select to previous value
                this.value = row.className.split('-')[1];
            });
        });
    });
    
    // Handle delete buttons
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('Are you sure you want to delete this application?')) {
                const company = this.getAttribute('data-company');
                const role = this.getAttribute('data-role');
                
                fetch('/delete_application', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        company: company,
                        role: role
                    }),
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        alert("Application deleted successfully!");
                        window.location.reload();
                    } else {
                        alert(data.error || 'Failed to delete application');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while deleting the application');
                });
            }
        });
    });
    
    // Edit modal functionality
    const editModal = document.getElementById('editModal');
    const modalCloseBtn = document.querySelector('.close');
    const editButtons = document.querySelectorAll('.edit-btn');
    const editForm = document.getElementById('edit-form');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const company = this.getAttribute('data-company');
            const role = this.getAttribute('data-role');
            const jobType = this.getAttribute('data-job-type');
            const country = this.getAttribute('data-country');
            const date = this.getAttribute('data-date');
            const source = this.getAttribute('data-source');
            
            document.getElementById('edit-original-company').value = company;
            document.getElementById('edit-original-role').value = role;
            document.getElementById('edit-company').value = company;
            document.getElementById('edit-role').value = role;
            document.getElementById('edit-job_type').value = jobType;
            document.getElementById('edit-country').value = country;
            document.getElementById('edit-date_applied').value = formatDate(date);
            document.getElementById('edit-source').value = source;
            
            editModal.style.display = 'block';
        });
    });
    
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', function() {
            editModal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', function(event) {
        if (event.target == editModal) {
            editModal.style.display = 'none';
        }
    });
    
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                original_company: document.getElementById('edit-original-company').value,
                original_role: document.getElementById('edit-original-role').value,
                company: document.getElementById('edit-company').value,
                role: document.getElementById('edit-role').value,
                job_type: document.getElementById('edit-job_type').value,
                country: document.getElementById('edit-country').value,
                date_applied: document.getElementById('edit-date_applied').value,
                source: document.getElementById('edit-source').value
            };
            
            // Validate all fields
            for (const [key, value] of Object.entries(formData)) {
                if (!value && !key.startsWith('original_')) {
                    alert(`Please fill out the ${key.replace('_', ' ')} field!`);
                    return;
                }
            }
            
            fetch('/edit_application', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert("Application updated successfully!");
                    editModal.style.display = 'none';
                    window.location.reload();
                } else {
                    alert(data.error || 'Failed to update application');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating the application');
            });
        });
    }
    
    // Search functionality
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('#applications-table tbody tr');
            
            rows.forEach(row => {
                const company = row.cells[0].textContent.toLowerCase();
                const role = row.cells[1].textContent.toLowerCase();
                
                if (company.includes(searchTerm) || role.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Export to CSV functionality
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            fetch('/export_csv')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.blob();
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'job_applications.csv';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Failed to export data');
                });
        });
    }
    
    // Helper function to format date
    function formatDate(dateString) {
        try {
            // Handle different date formats
            if (dateString.includes('-')) {
                // Already in YYYY-MM-DD format
                return dateString;
            }
            
            // Convert from other formats
            const date = new Date(dateString);
            if (isNaN(date.getTime())) {
                // If invalid date, return original
                return dateString;
            }
            
            // Format as YYYY-MM-DD
            return date.toISOString().split('T')[0];
        } catch (e) {
            console.error("Error formatting date:", e);
            return dateString;
        }
    }
});

// Scan Now button functionality
document.addEventListener('DOMContentLoaded', function() {
    const scanNowBtn = document.getElementById('scan-now-btn');
    const scanSpinner = document.getElementById('scan-spinner');
    const scanText = document.getElementById('scan-text');
    const scanStatus = document.getElementById('scan-status');
    
    if (scanNowBtn) {
        scanNowBtn.addEventListener('click', function() {
            // Disable button and show spinner
            scanNowBtn.disabled = true;
            scanSpinner.style.display = 'inline-block';
            scanText.textContent = 'Scanning...';
            
            if (scanStatus) {
                scanStatus.textContent = 'Scanning emails...';
                scanStatus.className = 'status-text scanning';
            }
            
            // Call the scan endpoint
            fetch('/scan_now')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Show success message
                        if (scanStatus) {
                            scanStatus.textContent = 'Scan completed successfully!';
                            scanStatus.className = 'status-text success';
                        }
                        
                        // Refresh the page after 3 seconds to show updated data
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    } else {
                        // Show error message
                        if (scanStatus) {
                            scanStatus.textContent = 'Error: ' + data.error;
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
                        scanStatus.textContent = 'Error during scan. Check console for details.';
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

// Add this to your static/js/main.js file
document.addEventListener('DOMContentLoaded', function() {
    // Filter toggle
    const toggleFiltersBtn = document.getElementById('toggle-filters');
    const filterOptions = document.getElementById('filter-options');
    
    if (toggleFiltersBtn && filterOptions) {
        toggleFiltersBtn.addEventListener('click', function() {
            const isHidden = filterOptions.style.display === 'none';
            filterOptions.style.display = isHidden ? 'block' : 'none';
            toggleFiltersBtn.textContent = isHidden ? 'Hide Filters' : 'Show Filters';
        });
    }
    
    // Apply filters
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // Reset filters
    const resetFiltersBtn = document.getElementById('reset-filters');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    function applyFilters() {
        // Collect filter values
        const filters = {
            status: document.getElementById('filter-status').value,
            date_from: document.getElementById('status-date-from').value,
            date_to: document.getElementById('status-date-to').value,
            applied_from: document.getElementById('applied-date-from').value,
            applied_to: document.getElementById('applied-date-to').value,
            new_only: document.getElementById('filter-new-only').checked,
            recently_updated: document.getElementById('filter-recent-updates').checked,
            sort_by: document.getElementById('filter-sort-by').value,
            sort_dir: document.getElementById('filter-sort-dir').value
        };
        
        // Send filter request
        fetch('/filter_applications', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(filters),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the applications table
                updateApplicationsTable(data.applications);
                
                // Show filter count
                showFilterCount(data.filtered_count, data.applications.length);
            } else {
                console.error('Filter error:', data.error);
            }
        })
        .catch(error => {
            console.error('Error applying filters:', error);
        });
    }
    
    function resetFilters() {
        // Reset all filter inputs
        document.getElementById('filter-status').value = '';
        document.getElementById('status-date-from').value = '';
        document.getElementById('status-date-to').value = '';
        document.getElementById('applied-date-from').value = '';
        document.getElementById('applied-date-to').value = '';
        document.getElementById('filter-new-only').checked = false;
        document.getElementById('filter-recent-updates').checked = false;
        document.getElementById('filter-sort-by').value = 'status_date';
        document.getElementById('filter-sort-dir').value = 'DESC';
        
        // Reload all applications
        window.location.reload();
    }
    
    function updateApplicationsTable(applications) {
        const tableContainer = document.getElementById('applications-table');
        if (!tableContainer) return;
        
        // Clear existing table
        tableContainer.innerHTML = '';
        
        if (applications.length === 0) {
            tableContainer.innerHTML = '<div class="no-results">No applications match your filter criteria</div>';
            return;
        }
        
        // Create new table
        const table = document.createElement('table');
        table.className = 'applications';
        
        // Add header
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Job Type</th>
                <th>Country</th>
                <th>Source</th>
                <th>Date Applied</th>
                <th>Status</th>
                <th>Status Date</th>
                <th>Actions</th>
            </tr>
        `;
        table.appendChild(thead);
        
        // Add body
        const tbody = document.createElement('tbody');
        applications.forEach(app => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-company', app.company);
            tr.setAttribute('data-role', app.role);
            
            // Status class for row color
            tr.className = app.status.toLowerCase();
            
            tr.innerHTML = `
                <td>${app.company}</td>
                <td>${app.role}</td>
                <td>${app.job_type}</td>
                <td>${app.country}</td>
                <td>${app.source}</td>
                <td>${app.date_applied}</td>
                <td>
                    <select class="status-select" data-company="${app.company}" data-role="${app.role}">
                        <option value="Pending" ${app.status === 'Pending' ? 'selected' : ''}>Pending</option>
                        <option value="Interview" ${app.status === 'Interview' ? 'selected' : ''}>Interview</option>
                        <option value="Assignment" ${app.status === 'Assignment' ? 'selected' : ''}>Assignment</option>
                        <option value="Offer" ${app.status === 'Offer' ? 'selected' : ''}>Offer</option>
                        <option value="Rejected" ${app.status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                    </select>
                </td>
                <td class="status-date">${app.status_date || 'N/A'}</td>
                <td>
                    <button class="edit-btn" data-company="${app.company}" data-role="${app.role}">Edit</button>
                    <button class="delete-btn" data-company="${app.company}" data-role="${app.role}">Delete</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        
        // Add table to container
        tableContainer.appendChild(table);
        
        // Re-attach event listeners
        attachTableEventListeners();
    }
    
    function showFilterCount(filteredCount, totalCount) {
        const filterHeader = document.querySelector('.filter-header h3');
        if (filterHeader) {
            filterHeader.textContent = `Filter Applications (${filteredCount} matched)`;
        }
    }
    
    function attachTableEventListeners() {
        // Reattach status change handlers
        document.querySelectorAll('.status-select').forEach(select => {
            select.addEventListener('change', function() {
                updateStatus(
                    this.getAttribute('data-company'),
                    this.getAttribute('data-role'),
                    this.value
                );
            });
        });
        
        // Reattach edit button handlers
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', function() {
                editApplication(
                    this.getAttribute('data-company'),
                    this.getAttribute('data-role')
                );
            });
        });
        
        // Reattach delete button handlers
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', function() {
                deleteApplication(
                    this.getAttribute('data-company'),
                    this.getAttribute('data-role')
                );
            });
        });
    }
});