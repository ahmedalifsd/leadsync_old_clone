// Main JavaScript for LeadSync

document.addEventListener('DOMContentLoaded', function() {

    // Handle category/source "Other" selection
    const categorySelect = document.getElementById('id_category_choice');
    const sourceSelect = document.getElementById('id_source_choice');
    const categoryOtherDiv = document.getElementById('category_other_div');
    const sourceOtherDiv = document.getElementById('source_other_div');

    function toggleOtherField(selectElement, otherDiv) {
        if (selectElement && otherDiv) {
            function updateVisibility() {
                if (selectElement.value === 'other') {
                    otherDiv.style.display = 'block';
                    if (otherDiv.querySelector('input, textarea')) {
                        otherDiv.querySelector('input, textarea').required = true;
                    }
                } else {
                    otherDiv.style.display = 'none';
                    if (otherDiv.querySelector('input, textarea')) {
                        otherDiv.querySelector('input, textarea').required = false;
                    }
                }
            }

            selectElement.addEventListener('change', updateVisibility);
            updateVisibility(); // Initial check
        }
    }

    toggleOtherField(categorySelect, categoryOtherDiv);
    toggleOtherField(sourceSelect, sourceOtherDiv);

    // Auto-format phone numbers
    const phoneInputs = document.querySelectorAll('input[type="tel"], input[name*="phone"], input[name*="contact"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');

            if (value.length > 3 && value.length <= 6) {
                value = value.replace(/(\d{3})(\d{0,3})/, '$1-$2');
            } else if (value.length > 6 && value.length <= 10) {
                value = value.replace(/(\d{3})(\d{3})(\d{0,4})/, '$1-$2-$3');
            }

            e.target.value = value;
        });
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Auto-submit forms on filter change
    const autoSubmitSelects = document.querySelectorAll('select[data-auto-submit]');
    autoSubmitSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Table row click for edit
    const clickableRows = document.querySelectorAll('tr[data-href]');
    clickableRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (!e.target.matches('a, button, .btn, input, select, textarea')) {
                window.location.href = this.dataset.href;
            }
        });
    });

    // Real-time notification counter
    function updateNotificationCount() {
        // This would be replaced with actual API call
        const notificationCount = 0; // Example
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            if (notificationCount > 0) {
                badge.textContent = notificationCount;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    // Update notifications every 30 seconds
    setInterval(updateNotificationCount, 30000);

    // Form validation feedback
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Dynamic form field addition
    const addMoreButtons = document.querySelectorAll('.add-more-field');
    addMoreButtons.forEach(button => {
        button.addEventListener('click', function() {
            const template = this.previousElementSibling;
            const clone = template.cloneNode(true);
            clone.style.display = 'block';
            clone.querySelectorAll('input, select, textarea').forEach(field => {
                field.value = '';
                field.name = field.name.replace(/_\d+$/, '') + '_' + Date.now();
            });
            this.parentNode.insertBefore(clone, this);
        });
    });
});

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}