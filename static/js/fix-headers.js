// Fix for white text on light backgrounds in supplier evaluation headers
document.addEventListener('DOMContentLoaded', function() {
    // Add the section-title class to all headers in the form sections
    const formSectionHeaders = document.querySelectorAll('.form-section h2, .form-section h3');
    formSectionHeaders.forEach(header => {
        header.classList.add('section-title');
    });

    // Make sure table headers have white text
    const tableHeaders = document.querySelectorAll('table thead th');
    tableHeaders.forEach(th => {
        th.style.color = 'white';
        th.style.backgroundColor = '#4e73df';
    });

    // Fix specific headers by ID or content
    const specificHeaders = [
        'Lista de Recebimentos',
        'Lista de Fornecedores',
        'Avaliação dos Fornecedores',
        'Ranking de Fornecedores'
    ];

    specificHeaders.forEach(headerText => {
        const headers = document.evaluate(
            `//*[contains(text(), '${headerText}')]`,
            document,
            null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
            null
        );

        for (let i = 0; i < headers.snapshotLength; i++) {
            const header = headers.snapshotItem(i);
            if (header.tagName === 'H2' || header.tagName === 'H3') {
                header.classList.add('section-title');
            }
        }
    });

    // Ensure all table containers have table-responsive class
    document.querySelectorAll('table').forEach(table => {
        const parent = table.parentElement;
        if (!parent.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });

    // Fix table row heights
    document.querySelectorAll('table tbody tr').forEach(row => {
        row.style.height = 'auto';
    });

    // Make the recebimentos table ID column narrower
    const recebimentosTable = document.getElementById('recebimentosTable');
    if (recebimentosTable) {
        // Make sure the ID column is narrow
        const firstColumnCells = recebimentosTable.querySelectorAll('tr > *:first-child');
        firstColumnCells.forEach(cell => {
            cell.style.width = '40px';
            cell.style.minWidth = '40px';
        });
    }
    
    // Convert all date displays to Brazilian format
    formatDateDisplays();
    
    // Set up date inputs to show Brazilian format
    setupDateInputs();
    
    // Add swipe gesture support for tabs on mobile
    const tabContent = document.querySelector('.tab-content');
    let touchStartX = 0;
    let touchEndX = 0;
    
    if (tabContent && window.innerWidth <= 768) {
        tabContent.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, false);
        
        tabContent.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, false);
    }
    
    function handleSwipe() {
        const activePaneId = document.querySelector('.tab-pane.active').id;
        const allTabs = Array.from(document.querySelectorAll('[data-bs-toggle="tab"]'));
        const activeTabIndex = allTabs.findIndex(tab => tab.getAttribute('data-bs-target') === '#' + activePaneId);
        
        if (touchEndX < touchStartX - 50) { // Swipe left
            if (activeTabIndex < allTabs.length - 1) {
                const nextTab = allTabs[activeTabIndex + 1];
                const tab = new bootstrap.Tab(nextTab);
                tab.show();
            }
        }
        
        if (touchEndX > touchStartX + 50) { // Swipe right
            if (activeTabIndex > 0) {
                const prevTab = allTabs[activeTabIndex - 1];
                const tab = new bootstrap.Tab(prevTab);
                tab.show();
            }
        }
    }
    
    // Make forms more responsive
    if (window.innerWidth <= 768) {
        const formSections = document.querySelectorAll('.form-section');
        formSections.forEach(section => {
            const rows = section.querySelectorAll('.row');
            rows.forEach(row => {
                row.style.display = 'flex';
                row.style.flexDirection = 'column';
            });
            
            const cols = section.querySelectorAll('[class*="col-"]');
            cols.forEach(col => {
                col.style.width = '100%';
                col.style.marginBottom = '1rem';
            });
        });
    }
    
    // Auto-scroll tab navigation if active tab is not fully visible
    const activeTab = document.querySelector('.nav-tabs .active');
    if (activeTab) {
        const navTabs = document.querySelector('.nav-tabs');
        if (navTabs) {
            setTimeout(() => {
                const activeTabPosition = activeTab.offsetLeft;
                const navTabsScrollPosition = navTabs.scrollLeft;
                const navTabsWidth = navTabs.clientWidth;
                
                if (activeTabPosition < navTabsScrollPosition || 
                    activeTabPosition + activeTab.clientWidth > navTabsScrollPosition + navTabsWidth) {
                    navTabs.scrollTo({
                        left: activeTabPosition - navTabsWidth / 2 + activeTab.clientWidth / 2,
                        behavior: 'smooth'
                    });
                }
            }, 100);
        }
    }
});

// Function to format all date displays to Brazilian format
function formatDateDisplays() {
    // Look for all table cells containing date patterns (XX/XX/XXXX or XXXX-XX-XX)
    document.querySelectorAll('td').forEach(cell => {
        const text = cell.textContent.trim();
        
        // Check for ISO format (YYYY-MM-DD)
        if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
            const parts = text.split('-');
            cell.textContent = `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
    });
}

// Function to set up date inputs for Brazilian format
function setupDateInputs() {
    document.querySelectorAll('input[type="date"]').forEach(input => {
        // Store the original value for form submission
        const originalValue = input.value;
        
        // If a date is present, format it for display
        if (originalValue) {
            // The input will still have the ISO format for submission
            // but we can show a formatted version nearby if needed
            const dateParts = originalValue.split('-');
            if (dateParts.length === 3) {
                const formattedDate = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
                
                // Create a label with the formatted date if needed
                if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('formatted-date')) {
                    const label = document.createElement('div');
                    label.classList.add('formatted-date', 'small', 'text-muted', 'mt-1');
                    label.textContent = `${formattedDate}`;
                    input.parentNode.insertBefore(label, input.nextSibling);
                }
            }
        }
    });
} 