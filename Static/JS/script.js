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
});