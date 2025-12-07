document.addEventListener('DOMContentLoaded', () => {
    const toast = document.getElementById('global-toast');
    const form = document.getElementById('application-form');
    const todayCheckbox = document.getElementById('today');
    const dateInput = document.getElementById('date_applied');
    const searchInput = document.getElementById('search');
    const exportBtn = document.getElementById('export-btn');
    const editModal = document.getElementById('editModal');
    const deleteModal = document.getElementById('deleteModal');
    const editForm = document.getElementById('edit-form');
    const editFeedback = document.getElementById('edit-feedback');
    const formFeedback = document.getElementById('form-feedback');
    const modalCloseButtons = document.querySelectorAll('.modal .close-btn');
    const cancelEditBtn = document.getElementById('cancel-edit');
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    const cancelDeleteBtn = document.getElementById('cancel-delete');
    let deleteContext = null;

    const showToast = (message, type = 'info') => {
        if (!toast) {
            alert(message);
            return;
        }
        toast.textContent = message;
        toast.dataset.state = type;
        toast.hidden = false;
        clearTimeout(showToast._timeout);
        showToast._timeout = setTimeout(() => {
            toast.hidden = true;
        }, 4000);
    };

    const setInlineFeedback = (node, message, type = 'info') => {
        if (!node) return;
        node.textContent = message;
        node.dataset.state = type;
        node.hidden = !message;
    };

    const handleResponse = async (response) => {
        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || 'Request failed');
        }
        return response.json();
    };

    if (todayCheckbox && dateInput) {
        todayCheckbox.addEventListener('change', (event) => {
            if (event.target.checked) {
                const today = new Date();
                const formatted = today.toISOString().split('T')[0];
                dateInput.value = formatted;
                dateInput.setAttribute('disabled', 'disabled');
            } else {
                dateInput.removeAttribute('disabled');
            }
        });
    }

    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            setInlineFeedback(formFeedback, '')
            const payload = {
                company: document.getElementById('company').value.trim(),
                role: document.getElementById('role').value,
                job_type: document.getElementById('job_type').value,
                country: document.getElementById('country').value.trim(),
                date_applied: dateInput.value,
                source: document.getElementById('source').value,
                resume_version: '1.0',
                status: 'Pending'
            };

            for (const [key, value] of Object.entries(payload)) {
                if (!value) {
                    setInlineFeedback(formFeedback, `Please fill out the ${key.replace('_', ' ')} field.`, 'error');
                    return;
                }
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;

            try {
                const response = await fetch('/add_application', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await handleResponse(response);
                if (data.success) {
                    showToast('Application added!', 'success');
                    form.reset();
                    if (todayCheckbox && todayCheckbox.checked) {
                        todayCheckbox.checked = false;
                        dateInput.removeAttribute('disabled');
                    }
                    window.location.reload();
                } else {
                    setInlineFeedback(formFeedback, data.error || 'Failed to add application', 'error');
                }
            } catch (error) {
                console.error(error);
                setInlineFeedback(formFeedback, 'Server error while adding application.', 'error');
            } finally {
                submitBtn.disabled = false;
            }
        });
    }

    const statusSelects = document.querySelectorAll('.status-select');
    statusSelects.forEach((select) => {
        select.addEventListener('change', async (event) => {
            const company = event.target.dataset.company;
            const role = event.target.dataset.role;
            const newStatus = event.target.value;
            try {
                const response = await fetch('/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company, role, status: newStatus })
                });
                const data = await handleResponse(response);
                if (data.success) {
                    showToast('Status updated', 'success');
                    const row = event.target.closest('tr');
                    row.className = `status-${newStatus.toLowerCase()}`;
                } else {
                    showToast(data.error || 'Failed to update status', 'error');
                }
            } catch (error) {
                console.error(error);
                showToast('Server error while updating status', 'error');
            }
        });
    });

    document.querySelectorAll('.edit-btn').forEach((button) => {
        button.addEventListener('click', () => {
            if (!editModal) return;
            editModal.hidden = false;
            document.getElementById('edit-original-company').value = button.dataset.company;
            document.getElementById('edit-original-role').value = button.dataset.role;
            document.getElementById('edit-company').value = button.dataset.company;
            document.getElementById('edit-role').value = button.dataset.role;
            document.getElementById('edit-job_type').value = button.dataset.jobType;
            document.getElementById('edit-country').value = button.dataset.country;
            document.getElementById('edit-date_applied').value = button.dataset.date;
            document.getElementById('edit-source').value = button.dataset.source;
            setInlineFeedback(editFeedback, '');
        });
    });

    const closeModal = (modal) => {
        if (modal) {
            modal.hidden = true;
        }
    };

    modalCloseButtons.forEach((btn) => btn.addEventListener('click', () => closeModal(btn.closest('.modal'))));
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => closeModal(editModal));
    }

    if (window) {
        window.addEventListener('click', (event) => {
            if (event.target === editModal) closeModal(editModal);
            if (event.target === deleteModal) closeModal(deleteModal);
        });
    }

    if (editForm) {
        editForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const payload = {
                original_company: document.getElementById('edit-original-company').value,
                original_role: document.getElementById('edit-original-role').value,
                company: document.getElementById('edit-company').value.trim(),
                role: document.getElementById('edit-role').value,
                job_type: document.getElementById('edit-job_type').value,
                country: document.getElementById('edit-country').value.trim(),
                date_applied: document.getElementById('edit-date_applied').value,
                source: document.getElementById('edit-source').value
            };

            for (const [key, value] of Object.entries(payload)) {
                if (!value) {
                    setInlineFeedback(editFeedback, `Missing ${key.replace('_', ' ')}`, 'error');
                    return;
                }
            }

            try {
                const response = await fetch('/edit_application', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await handleResponse(response);
                if (data.success) {
                    showToast('Application updated', 'success');
                    window.location.reload();
                } else {
                    setInlineFeedback(editFeedback, data.error || 'Failed to update application', 'error');
                }
            } catch (error) {
                console.error(error);
                setInlineFeedback(editFeedback, 'Server error while editing application', 'error');
            }
        });
    }

    document.querySelectorAll('.delete-btn').forEach((button) => {
        button.addEventListener('click', () => {
            if (!deleteModal) return;
            deleteContext = {
                company: button.dataset.company,
                role: button.dataset.role
            };
            deleteModal.hidden = false;
        });
    });

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async () => {
            if (!deleteContext) return;
            try {
                const response = await fetch('/delete_application', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(deleteContext)
                });
                const data = await handleResponse(response);
                if (data.success) {
                    showToast('Application deleted', 'success');
                    window.location.reload();
                } else {
                    showToast(data.error || 'Failed to delete application', 'error');
                }
            } catch (error) {
                console.error(error);
                showToast('Server error while deleting application', 'error');
            }
        });
    }

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', () => {
            deleteContext = null;
            closeModal(deleteModal);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            const term = event.target.value.toLowerCase();
            document.querySelectorAll('#applications-table tbody tr').forEach((row) => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(term) ? '' : 'none';
            });
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/export');
                if (!response.ok) throw new Error('Export failed');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const anchor = document.createElement('a');
                anchor.href = url;
                anchor.download = 'job_applications.csv';
                document.body.appendChild(anchor);
                anchor.click();
                document.body.removeChild(anchor);
                window.URL.revokeObjectURL(url);
                showToast('Export ready', 'success');
            } catch (error) {
                console.error(error);
                showToast('Unable to export CSV right now', 'error');
            }
        });
    }
});
