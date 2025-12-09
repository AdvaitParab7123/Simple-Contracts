/**
 * Contract Management Module - JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
    initPopovers();
    initConfirmDialogs();
    initFileUploadPreviews();
    initSearchDebounce();
});

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap popovers
 */
function initPopovers() {
    var popoverTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="popover"]')
    );
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Initialize confirmation dialogs for delete actions
 */
function initConfirmDialogs() {
    document.querySelectorAll('[data-confirm]').forEach(function(element) {
        element.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize file upload previews
 */
function initFileUploadPreviews() {
    document.querySelectorAll('input[type="file"]').forEach(function(input) {
        input.addEventListener('change', function() {
            var preview = document.querySelector(
                '[data-preview-for="' + this.id + '"]'
            );
            
            if (preview && this.files && this.files[0]) {
                var file = this.files[0];
                var fileName = file.name;
                var fileSize = formatFileSize(file.size);
                
                preview.innerHTML = '<i class="bi bi-file-earmark me-2"></i>' +
                    fileName + ' <span class="text-muted">(' + fileSize + ')</span>';
                preview.classList.remove('d-none');
            }
        });
    });
}

/**
 * Initialize search input debouncing
 */
function initSearchDebounce() {
    var searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        var debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                // Auto-submit form after typing stops
                var form = searchInput.closest('form');
                if (form && searchInput.value.length >= 3) {
                    // form.submit(); // Uncomment to enable auto-submit
                }
            }, 500);
        });
    }
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    var k = 1024;
    var sizes = ['Bytes', 'KB', 'MB', 'GB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard!', 'success');
        });
    } else {
        // Fallback for older browsers
        var textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Copied to clipboard!', 'success');
    }
}

/**
 * Show a toast notification
 */
function showToast(message, type) {
    type = type || 'info';
    
    var toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    var toastId = 'toast-' + Date.now();
    var bgClass = 'bg-' + type;
    
    var toastHtml = '<div id="' + toastId + '" class="toast align-items-center text-white ' + bgClass + ' border-0" role="alert">' +
        '<div class="d-flex">' +
        '<div class="toast-body">' + message + '</div>' +
        '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
        '</div></div>';
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    var toastElement = document.getElementById(toastId);
    var toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 3000 });
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Format currency value
 */
function formatCurrency(amount, currency) {
    currency = currency || 'INR';
    
    var symbols = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    };
    
    var symbol = symbols[currency] || currency + ' ';
    var formatted = parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    
    return symbol + formatted;
}

/**
 * Calculate days between two dates
 */
function daysBetween(date1, date2) {
    var oneDay = 24 * 60 * 60 * 1000;
    var firstDate = new Date(date1);
    var secondDate = new Date(date2);
    
    return Math.round((secondDate - firstDate) / oneDay);
}

/**
 * Export table to CSV
 */
function exportTableToCSV(tableId, filename) {
    var table = document.getElementById(tableId);
    if (!table) return;
    
    var csv = [];
    var rows = table.querySelectorAll('tr');
    
    rows.forEach(function(row) {
        var cols = row.querySelectorAll('td, th');
        var rowData = [];
        
        cols.forEach(function(col) {
            var text = col.innerText.replace(/"/g, '""');
            rowData.push('"' + text + '"');
        });
        
        csv.push(rowData.join(','));
    });
    
    var csvContent = csv.join('\n');
    var blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    
    if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, filename);
    } else {
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

