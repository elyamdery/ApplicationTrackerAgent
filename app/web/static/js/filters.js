document.addEventListener('DOMContentLoaded', function() {
    console.log("Filter script loaded");
    
    // Filter toggle
    const toggleFiltersBtn = document.getElementById('toggle-filters');
    const filterOptions = document.getElementById('filter-options');
    
    if (toggleFiltersBtn && filterOptions) {
        toggleFiltersBtn.addEventListener('click', function() {
            const isHidden = filterOptions.style.display === 'none';
            filterOptions.style.display = isHidden ? 'block' : 'none';
            toggleFiltersBtn.textContent = isHidden ? 'Hide Filters' : 'Show Filters';
        });
    } else {
        console.error("Filter toggle elements not found");
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
        console.log("Applying filters");
        // Show loading state
        const applyBtn = document.getElementById('apply-filters');
        if (applyBtn) {
            applyBtn.textContent = "Filtering...";
            applyBtn.disabled = true;
        }
        
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
        
        console.log("Filter values:", filters);
        
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
                console.log("Filter response:", data);
                // Update the applications table
                updateApplicationsTable(data.applications);
                
                // Show filter count
                showFilterCount(data.filtered_count);
                
                // Reset button state
                if (applyBtn) {
                    applyBtn.textContent = "Apply Filters";
                    applyBtn.disabled = false;
                }
            } else {
                console.error('Filter error:', data.error);
                alert('Error applying filters: ' + data.error);
                
                // Reset button state
                if (applyBtn) {
                    applyBtn.textContent = "Apply Filters";
                    applyBtn.disabled = false;
                }
            }
        })
        .catch(error => {
            console.error('Error applying filters:', error);
            alert('Error applying filters. Check console for details.');
            
            // Reset button state
            if (applyBtn) {
                applyBtn.textContent = "Apply Filters";
                applyBtn.disabled = false;
            }
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
        if (!tableContainer) {
            console.error("Applications table container not found");
            return;
        }
        
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
    
    function showFilterCount(filteredCount) {
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
                const company = this.getAttribute('data-company');
                const role = this.getAttribute('data-role');
                openEditModal(company, role);
            });
        });
        
        // Reattach delete button handlers
        document.querySelectorAll('.delete-btn').forEach(button => {
            button.addEventListener('click', function() {
                const company = this.getAttribute('data-company');
                const role = this.getAttribute('data-role');
                
                if (confirm(`Are you sure you want to delete the application for ${company} - ${role}?`)) {
                    deleteApplication(company, role);
                }
            });
        });
    }
    
    function updateStatus(company, role, status) {
        fetch('/update_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company: company,
                role: role,
                status: status
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update status date display
                const row = document.querySelector(`tr[data-company="${company}"][data-role="${role}"]`);
                if (row) {
                    const statusDateCell = row.querySelector('.status-date');
                    if (statusDateCell) {
                        statusDateCell.textContent = data.status_date || 'N/A';
                    }
                    
                    // Update row class based on status
                    row.className = status.toLowerCase();
                }
            } else {
                alert('Error updating status: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error updating status:', error);
            alert('Error updating status.');
        });
    }
    
    function deleteApplication(company, role) {
        fetch('/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company: company,
                role: role
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove row from table
                const row = document.querySelector(`tr[data-company="${company}"][data-role="${role}"]`);
                if (row) row.remove();
            } else {
                alert('Error deleting application: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting application:', error);
            alert('Error deleting application.');
        });
    }
    
    function openEditModal(company, role) {
        const editModal = document.getElementById('edit-modal');
        if (editModal) {
            // Get application data
            fetch(`/get_application?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Populate form with application data
                        document.getElementById('edit-company').value = data.application.company;
                        document.getElementById('edit-role').value = data.application.role;
                        document.getElementById('edit-job-type').value = data.application.job_type;
                        document.getElementById('edit-country').value = data.application.country;
                        document.getElementById('edit-source').value = data.application.source;
                        document.getElementById('edit-date-applied').value = data.application.date_applied;
                        
                        // Set original values for reference
                        document.getElementById('original-company').value = company;
                        document.getElementById('original-role').value = role;
                        
                        // Show modal
                        editModal.style.display = 'block';
                    } else {
                        alert('Error loading application details: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error loading application details:', error);
                    alert('Error loading application details.');
                });
        }
    }
});