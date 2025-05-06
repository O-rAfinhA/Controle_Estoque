/**
 * Common JavaScript Library for Estoque Management System
 * This file contains commonly used functions across the application
 */

// Utility Functions
const EstoqueUtils = {
    /**
     * Format a date string to Brazilian format (DD/MM/YYYY)
     * @param {Date|string} date - Date object or string
     * @returns {string} Formatted date string
     */
    formatDate: function(date) {
        if (!date) return '';
        const d = typeof date === 'string' ? new Date(date) : date;
        return d.toLocaleDateString('pt-BR');
    },

    /**
     * Format currency in Brazilian Real format
     * @param {number} value - The value to format
     * @returns {string} Formatted currency string
     */
    formatCurrency: function(value) {
        return new Intl.NumberFormat('pt-BR', { 
            style: 'currency', 
            currency: 'BRL' 
        }).format(value);
    },

    /**
     * Generate a unique ID
     * @returns {string} Unique ID
     */
    generateUniqueId: function() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Debounce function to limit the rate at which a function can fire
     * @param {Function} func - The function to debounce
     * @param {number} wait - The time to wait in milliseconds
     * @returns {Function} Debounced function
     */
    debounce: function(func, wait) {
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
};

// Form Validation
const FormValidator = {
    /**
     * Validate a form field
     * @param {HTMLElement} field - The field to validate
     * @param {Object} rules - Validation rules
     * @returns {boolean} Whether the field is valid
     */
    validateField: function(field, rules) {
        const value = field.value.trim();
        
        // Required check
        if (rules.required && !value) {
            this.showError(field, 'Este campo é obrigatório');
            return false;
        }
        
        // Min length check
        if (rules.minLength && value.length < rules.minLength) {
            this.showError(field, `Deve ter pelo menos ${rules.minLength} caracteres`);
            return false;
        }
        
        // Max length check
        if (rules.maxLength && value.length > rules.maxLength) {
            this.showError(field, `Deve ter no máximo ${rules.maxLength} caracteres`);
            return false;
        }
        
        // Pattern check
        if (rules.pattern && !rules.pattern.test(value)) {
            this.showError(field, rules.patternMessage || 'Formato inválido');
            return false;
        }
        
        // Custom validation
        if (rules.custom && typeof rules.custom === 'function') {
            const customResult = rules.custom(value);
            if (customResult !== true) {
                this.showError(field, customResult || 'Valor inválido');
                return false;
            }
        }
        
        // Clear error if validation passes
        this.clearError(field);
        return true;
    },
    
    /**
     * Display error message for a field
     * @param {HTMLElement} field - The field with error
     * @param {string} message - Error message
     */
    showError: function(field, message) {
        // Remove any existing error
        this.clearError(field);
        
        // Add error class to field
        field.classList.add('is-invalid');
        
        // Create error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        // Insert error after field
        field.parentNode.appendChild(errorDiv);
    },
    
    /**
     * Clear error message and state from a field
     * @param {HTMLElement} field - The field to clear
     */
    clearError: function(field) {
        field.classList.remove('is-invalid');
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
    },
    
    /**
     * Validate an entire form
     * @param {HTMLFormElement} form - The form to validate
     * @param {Object} validationRules - Rules for each field
     * @returns {boolean} Whether the form is valid
     */
    validateForm: function(form, validationRules) {
        let isValid = true;
        
        for (const fieldName in validationRules) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const isFieldValid = this.validateField(field, validationRules[fieldName]);
                isValid = isValid && isFieldValid;
            }
        }
        
        return isValid;
    }
};

// Pagination System
const Pagination = {
    /**
     * Initialize pagination
     * @param {Object} options - Pagination options
     * @returns {Object} Pagination controller
     */
    init: function(options) {
        const defaults = {
            container: null,            // Container element for pagination controls
            itemsPerPage: 10,           // Number of items per page
            items: [],                  // Array of items to paginate
            displayItems: null,         // Function to display items on the page
            pageInfo: null,             // Element to display page info
            onPageChange: null          // Callback when page changes
        };
        
        const settings = { ...defaults, ...options };
        
        if (!settings.container || !settings.items || !settings.displayItems) {
            console.error('Pagination: Required options are missing');
            return null;
        }
        
        const totalPages = Math.ceil(settings.items.length / settings.itemsPerPage);
        let currentPage = 1;
        
        // Create pagination controls
        this.renderControls(settings.container, totalPages);
        
        // Initial display
        this.changePage(1, settings);
        
        // Event listeners for pagination controls
        settings.container.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                
                const pageLink = e.currentTarget;
                const action = pageLink.getAttribute('data-action');
                
                if (action === 'prev' && currentPage > 1) {
                    this.changePage(currentPage - 1, settings);
                } else if (action === 'next' && currentPage < totalPages) {
                    this.changePage(currentPage + 1, settings);
                } else if (action === 'first') {
                    this.changePage(1, settings);
                } else if (action === 'last') {
                    this.changePage(totalPages, settings);
                } else if (pageLink.textContent) {
                    const pageNum = parseInt(pageLink.textContent, 10);
                    if (!isNaN(pageNum)) {
                        this.changePage(pageNum, settings);
                    }
                }
            });
        });
        
        // Return controller object
        return {
            refresh: function(newItems) {
                settings.items = newItems || settings.items;
                const newTotalPages = Math.ceil(settings.items.length / settings.itemsPerPage);
                
                // Re-render controls if total pages changed
                if (newTotalPages !== totalPages) {
                    Pagination.renderControls(settings.container, newTotalPages);
                    totalPages = newTotalPages;
                }
                
                // Adjust current page if needed
                if (currentPage > newTotalPages) {
                    currentPage = Math.max(1, newTotalPages);
                }
                
                Pagination.changePage(currentPage, settings);
            },
            goToPage: function(page) {
                Pagination.changePage(page, settings);
            }
        };
    },
    
    /**
     * Change the current page
     * @param {number} page - The page to display
     * @param {Object} settings - Pagination settings
     */
    changePage: function(page, settings) {
        const totalPages = Math.ceil(settings.items.length / settings.itemsPerPage);
        
        if (page < 1 || page > totalPages) {
            return;
        }
        
        // Update current page
        const currentPage = page;
        
        // Calculate items to display
        const startIndex = (currentPage - 1) * settings.itemsPerPage;
        const endIndex = Math.min(startIndex + settings.itemsPerPage, settings.items.length);
        const displayItems = settings.items.slice(startIndex, endIndex);
        
        // Display items
        settings.displayItems(displayItems, startIndex, endIndex);
        
        // Update page info if provided
        if (settings.pageInfo) {
            settings.pageInfo.textContent = `Mostrando ${startIndex + 1} a ${endIndex} de ${settings.items.length} itens`;
        }
        
        // Update active page in controls
        this.updateActiveState(settings.container, currentPage, totalPages);
        
        // Callback if provided
        if (typeof settings.onPageChange === 'function') {
            settings.onPageChange(currentPage, totalPages);
        }
    },
    
    /**
     * Render pagination controls
     * @param {HTMLElement} container - Container for controls
     * @param {number} totalPages - Total number of pages
     */
    renderControls: function(container, totalPages) {
        // Clear existing controls
        container.innerHTML = '';
        
        if (totalPages <= 1) {
            return;
        }
        
        // First page
        const firstLink = document.createElement('li');
        firstLink.className = 'page-item';
        firstLink.innerHTML = '<a class="page-link" href="#" data-action="first">&laquo;</a>';
        container.appendChild(firstLink);
        
        // Previous
        const prevLink = document.createElement('li');
        prevLink.className = 'page-item';
        prevLink.innerHTML = '<a class="page-link" href="#" data-action="prev">&lsaquo;</a>';
        container.appendChild(prevLink);
        
        // Page numbers (show up to 5 pages)
        const maxVisiblePages = 5;
        let startPage = 1;
        let endPage = totalPages;
        
        if (totalPages > maxVisiblePages) {
            // Show first, last, and pages around current
            startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
            endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
            
            // Adjust if needed
            if (endPage - startPage + 1 < maxVisiblePages) {
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }
        }
        
        // Add page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageLink = document.createElement('li');
            pageLink.className = 'page-item';
            pageLink.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            container.appendChild(pageLink);
        }
        
        // Next
        const nextLink = document.createElement('li');
        nextLink.className = 'page-item';
        nextLink.innerHTML = '<a class="page-link" href="#" data-action="next">&rsaquo;</a>';
        container.appendChild(nextLink);
        
        // Last page
        const lastLink = document.createElement('li');
        lastLink.className = 'page-item';
        lastLink.innerHTML = '<a class="page-link" href="#" data-action="last">&raquo;</a>';
        container.appendChild(lastLink);
    },
    
    /**
     * Update active state of pagination controls
     * @param {HTMLElement} container - Container for controls
     * @param {number} currentPage - Current active page
     * @param {number} totalPages - Total number of pages
     */
    updateActiveState: function(container, currentPage, totalPages) {
        // Remove active class from all pages
        container.querySelectorAll('.page-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Set active page
        const pageLinks = container.querySelectorAll('.page-item:not(:first-child):not(:last-child)');
        pageLinks.forEach(item => {
            const link = item.querySelector('.page-link');
            if (link && parseInt(link.textContent, 10) === currentPage) {
                item.classList.add('active');
            }
        });
        
        // Disable first/prev buttons if on first page
        const firstLink = container.querySelector('.page-item:first-child');
        const prevLink = container.querySelector('.page-item:nth-child(2)');
        if (firstLink && prevLink) {
            firstLink.classList.toggle('disabled', currentPage === 1);
            prevLink.classList.toggle('disabled', currentPage === 1);
        }
        
        // Disable next/last buttons if on last page
        const nextLink = container.querySelector('.page-item:nth-last-child(2)');
        const lastLink = container.querySelector('.page-item:last-child');
        if (nextLink && lastLink) {
            nextLink.classList.toggle('disabled', currentPage === totalPages);
            lastLink.classList.toggle('disabled', currentPage === totalPages);
        }
    }
};

// Table Search & Filter
const TableFilter = {
    /**
     * Initialize table filter
     * @param {Object} options - Filter options
     */
    init: function(options) {
        const defaults = {
            tableId: '',                // ID of the table to filter
            inputId: '',                // ID of the search input
            filterFields: [],           // Array of field indexes to search in
            caseSensitive: false,       // Whether search is case sensitive
            onFilter: null              // Callback after filtering
        };
        
        const settings = { ...defaults, ...options };
        
        if (!settings.tableId || !settings.inputId) {
            console.error('TableFilter: Required options are missing');
            return;
        }
        
        const table = document.getElementById(settings.tableId);
        const input = document.getElementById(settings.inputId);
        
        if (!table || !input) {
            console.error('TableFilter: Table or input not found');
            return;
        }
        
        // Attach event listener to input
        input.addEventListener('input', EstoqueUtils.debounce(function() {
            TableFilter.filterTable(table, input.value, settings);
        }, 300));
        
        // Add clear button
        this.addClearButton(input, function() {
            input.value = '';
            TableFilter.filterTable(table, '', settings);
        });
    },
    
    /**
     * Filter table rows based on search term
     * @param {HTMLElement} table - Table element
     * @param {string} term - Search term
     * @param {Object} settings - Filter settings
     */
    filterTable: function(table, term, settings) {
        const rows = table.querySelectorAll('tbody tr');
        let matchCount = 0;
        
        // If no filter fields specified, search all cells
        const filterFields = settings.filterFields.length > 0 ? 
                            settings.filterFields : 
                            [...Array(rows[0]?.cells.length || 0).keys()];
        
        // Process search term
        term = settings.caseSensitive ? term : term.toLowerCase();
        
        rows.forEach(row => {
            let match = false;
            
            if (!term) {
                match = true; // Empty search shows all rows
            } else {
                // Check each specified cell for a match
                filterFields.forEach(index => {
                    if (index < row.cells.length) {
                        const cell = row.cells[index];
                        const text = settings.caseSensitive ? 
                                   cell.textContent : 
                                   cell.textContent.toLowerCase();
                        
                        if (text.includes(term)) {
                            match = true;
                        }
                    }
                });
            }
            
            // Show/hide row based on match
            row.style.display = match ? '' : 'none';
            
            if (match) {
                matchCount++;
            }
        });
        
        // Callback with filter results
        if (typeof settings.onFilter === 'function') {
            settings.onFilter(matchCount, rows.length);
        }
    },
    
    /**
     * Add clear button to search input
     * @param {HTMLElement} input - Input element
     * @param {Function} callback - Function to call when clear button is clicked
     */
    addClearButton: function(input, callback) {
        // Create wrapper for input and button
        const wrapper = document.createElement('div');
        wrapper.className = 'position-relative';
        
        // Create clear button
        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.className = 'btn btn-sm position-absolute top-50 end-0 translate-middle-y text-secondary';
        clearButton.innerHTML = '<i class="fas fa-times"></i>';
        clearButton.style.display = 'none';
        
        // Insert wrapper
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(clearButton);
        
        // Show/hide clear button
        input.addEventListener('input', function() {
            clearButton.style.display = input.value ? 'block' : 'none';
        });
        
        // Clear input
        clearButton.addEventListener('click', function() {
            if (typeof callback === 'function') {
                callback();
            }
            clearButton.style.display = 'none';
        });
    }
};

// Toast Notifications
const ToastNotification = {
    /**
     * Show a toast notification
     * @param {Object} options - Toast options
     */
    show: function(options) {
        const defaults = {
            title: '',                  // Toast title
            message: '',                // Toast message
            type: 'info',               // Type: success, error, warning, info
            duration: 3000,             // Duration in milliseconds
            position: 'top-right'       // Position: top-right, top-left, bottom-right, bottom-left
        };
        
        const settings = { ...defaults, ...options };
        
        // Create toast container if not exists
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = `toast-container position-fixed ${this.getPositionClasses(settings.position)}`;
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = EstoqueUtils.generateUniqueId();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast show ${this.getTypeClass(settings.type)}`;
        toast.role = 'alert';
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Toast header
        let headerContent = '';
        if (settings.title) {
            headerContent = `
                <div class="toast-header">
                    <strong class="me-auto">${settings.title}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
        }
        
        // Toast body
        toast.innerHTML = `
            ${headerContent}
            <div class="toast-body">
                ${settings.message}
            </div>
        `;
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Close button handler
        const closeBtn = toast.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide(toastId));
        }
        
        // Auto-hide after duration
        if (settings.duration > 0) {
            setTimeout(() => this.hide(toastId), settings.duration);
        }
    },
    
    /**
     * Hide a toast notification
     * @param {string} toastId - ID of the toast to hide
     */
    hide: function(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
                
                // Remove container if empty
                const container = document.querySelector('.toast-container');
                if (container && container.children.length === 0) {
                    container.remove();
                }
            }, 300);
        }
    },
    
    /**
     * Get CSS classes for toast position
     * @param {string} position - Toast position
     * @returns {string} CSS classes
     */
    getPositionClasses: function(position) {
        switch (position) {
            case 'top-left':
                return 'top-0 start-0 p-3';
            case 'top-center':
                return 'top-0 start-50 translate-middle-x p-3';
            case 'bottom-right':
                return 'bottom-0 end-0 p-3';
            case 'bottom-left':
                return 'bottom-0 start-0 p-3';
            case 'bottom-center':
                return 'bottom-0 start-50 translate-middle-x p-3';
            case 'top-right':
            default:
                return 'top-0 end-0 p-3';
        }
    },
    
    /**
     * Get CSS class for toast type
     * @param {string} type - Toast type
     * @returns {string} CSS class
     */
    getTypeClass: function(type) {
        switch (type) {
            case 'success':
                return 'bg-success text-white';
            case 'error':
                return 'bg-danger text-white';
            case 'warning':
                return 'bg-warning';
            case 'info':
            default:
                return 'bg-info text-white';
        }
    },
    
    // Shorthand methods
    success: function(message, title = 'Sucesso') {
        this.show({ type: 'success', message, title });
    },
    
    error: function(message, title = 'Erro') {
        this.show({ type: 'error', message, title });
    },
    
    warning: function(message, title = 'Atenção') {
        this.show({ type: 'warning', message, title });
    },
    
    info: function(message, title = 'Informação') {
        this.show({ type: 'info', message, title });
    }
};

// Chart Utils
const ChartUtils = {
    /**
     * Generate default colors for charts
     * @param {number} count - Number of colors needed
     * @returns {string[]} Array of color codes
     */
    generateColors: function(count) {
        const baseColors = [
            '#4e73df', // Primary
            '#1cc88a', // Success
            '#36b9cc', // Info
            '#f6c23e', // Warning
            '#e74a3b', // Danger
            '#5a5c69', // Secondary
            '#6f42c1', // Purple
            '#fd7e14', // Orange
            '#20c9a6', // Teal
            '#36b9cc'  // Cyan
        ];
        
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        
        return colors;
    },
    
    /**
     * Format number value for tooltip
     * @param {number} value - Value to format
     * @returns {string} Formatted value
     */
    formatTooltipValue: function(value) {
        if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'k';
        }
        return value.toString();
    },
    
    /**
     * Create a bar chart
     * @param {string} canvasId - ID of canvas element
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @returns {Chart} Chart instance
     */
    createBarChart: function(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('ChartUtils: Canvas element not found');
            return null;
        }
        
        const ctx = canvas.getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 14
                    },
                    bodyFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 13
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 11
                        }
                    }
                }
            }
        };
        
        const chartOptions = { ...defaultOptions, ...options };
        
        // Create and return chart
        return new Chart(ctx, {
            type: 'bar',
            data: data,
            options: chartOptions
        });
    },
    
    /**
     * Create a line chart
     * @param {string} canvasId - ID of canvas element
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @returns {Chart} Chart instance
     */
    createLineChart: function(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('ChartUtils: Canvas element not found');
            return null;
        }
        
        const ctx = canvas.getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 14
                    },
                    bodyFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 13
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 11
                        }
                    }
                }
            }
        };
        
        const chartOptions = { ...defaultOptions, ...options };
        
        // Create and return chart
        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: chartOptions
        });
    },
    
    /**
     * Create a pie chart
     * @param {string} canvasId - ID of canvas element
     * @param {Object} data - Chart data
     * @param {Object} options - Chart options
     * @returns {Chart} Chart instance
     */
    createPieChart: function(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('ChartUtils: Canvas element not found');
            return null;
        }
        
        const ctx = canvas.getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: {
                            family: "'Roboto', Arial, sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 14
                    },
                    bodyFont: {
                        family: "'Roboto', Arial, sans-serif",
                        size: 13
                    }
                }
            }
        };
        
        const chartOptions = { ...defaultOptions, ...options };
        
        // Create and return chart
        return new Chart(ctx, {
            type: 'pie',
            data: data,
            options: chartOptions
        });
    }
};

// Export for use in other scripts
window.EstoqueUtils = EstoqueUtils;
window.FormValidator = FormValidator;
window.Pagination = Pagination;
window.TableFilter = TableFilter;
window.ToastNotification = ToastNotification;
window.ChartUtils = ChartUtils; 