/**
 * app.js
 * 
 * Main application logic for the VWAP Reports Gallery.
 * Handles manifest loading, dropdown population, filtering, and URL parameters.
 * Auto-selects first available date range when timeframe is chosen.
 */

let manifest = null;
let currentSelection = {
    contract: null,
    timeframe: null,
    dateRange: null
};

// DOM elements
const contractSelect = document.getElementById('contract-select');
const timeframeSelect = document.getElementById('timeframe-select');
const reportContent = document.getElementById('report-content');
const noSelection = document.getElementById('no-selection');
const htmlLinks = document.getElementById('html-links');
const dashboardsSection = document.getElementById('dashboards-section');


/**
 * Load manifest.json and initialize the application
 */
async function loadManifest() {
    try {
        const response = await fetch('manifest.json');
        if (!response.ok) {
            throw new Error(`Failed to load manifest: ${response.statusText}`);
        }
        manifest = await response.json();
        initializeApp();
    } catch (error) {
        console.error('Error loading manifest:', error);
        document.body.innerHTML = `
            <div class="container">
                <h1>Error</h1>
                <p>Failed to load manifest.json. Please run generate_manifest.py first.</p>
                <p>Error: ${error.message}</p>
            </div>
        `;
    }
}


/**
 * Initialize the application: populate dropdowns and handle URL parameters
 */
function initializeApp() {
    populateContracts();
    
    // Check for URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const contractParam = urlParams.get('contract');
    const tfParam = urlParams.get('tf');
    const rangeParam = urlParams.get('range'); // Still support for backward compatibility
    
    if (contractParam && tfParam) {
        // Set selections from URL params
        currentSelection.contract = contractParam;
        currentSelection.timeframe = tfParam;
        
        contractSelect.value = contractParam;
        populateTimeframes();
        timeframeSelect.value = tfParam;
        
        // Auto-select date range
        if (rangeParam) {
            // Use provided range if valid
            currentSelection.dateRange = rangeParam;
        } else {
            // Auto-select first available date range
            autoSelectDateRange();
        }
        
        if (currentSelection.dateRange) {
            displayReport();
        }
    }
    
    // Set up event listeners
    contractSelect.addEventListener('change', handleContractChange);
    timeframeSelect.addEventListener('change', handleTimeframeChange);
}


/**
 * Populate the contracts dropdown
 */
function populateContracts() {
    const contracts = Object.keys(manifest).sort();
    contracts.forEach(contract => {
        const option = document.createElement('option');
        option.value = contract;
        option.textContent = contract;
        contractSelect.appendChild(option);
    });
}


/**
 * Populate the timeframes dropdown based on selected contract
 */
function populateTimeframes() {
    timeframeSelect.innerHTML = '<option value="">-- Select Timeframe --</option>';
    
    if (!currentSelection.contract || !manifest[currentSelection.contract]) {
        timeframeSelect.disabled = true;
        return;
    }
    
    timeframeSelect.disabled = false;
    const timeframes = Object.keys(manifest[currentSelection.contract])
        .sort((a, b) => {
            // Sort by numeric value: 1m, 5m, 15m, 30m
            const aNum = parseInt(a);
            const bNum = parseInt(b);
            return aNum - bNum;
        });
    
    timeframes.forEach(tf => {
        const option = document.createElement('option');
        option.value = tf;
        option.textContent = tf;
        timeframeSelect.appendChild(option);
    });
}


/**
 * Auto-select the first available date range for the current contract and timeframe
 */
function autoSelectDateRange() {
    if (!currentSelection.contract || !currentSelection.timeframe ||
        !manifest[currentSelection.contract] ||
        !manifest[currentSelection.contract][currentSelection.timeframe]) {
        currentSelection.dateRange = null;
        return;
    }
    
    const dateRanges = Object.keys(
        manifest[currentSelection.contract][currentSelection.timeframe]
    ).sort((a, b) => {
        // Sort by start date (first 8 digits)
        const aStart = a.substring(0, 8);
        const bStart = b.substring(0, 8);
        return aStart.localeCompare(bStart);
    });
    
    // Select first date range
    if (dateRanges.length > 0) {
        currentSelection.dateRange = dateRanges[0];
    } else {
        currentSelection.dateRange = null;
    }
}


/**
 * Handle contract selection change
 */
function handleContractChange() {
    currentSelection.contract = contractSelect.value || null;
    currentSelection.timeframe = null;
    currentSelection.dateRange = null;
    
    timeframeSelect.value = '';
    
    populateTimeframes();
    clearReport();
    updateURL();
}


/**
 * Handle timeframe selection change
 */
function handleTimeframeChange() {
    currentSelection.timeframe = timeframeSelect.value || null;
    currentSelection.dateRange = null;
    
    // Auto-select first date range when timeframe is selected
    autoSelectDateRange();
    
    if (currentSelection.dateRange) {
        displayReport();
    } else {
        clearReport();
    }
    
    updateURL();
}


/**
 * Display the selected report
 */
function displayReport() {
    if (!currentSelection.contract || !currentSelection.timeframe || !currentSelection.dateRange) {
        clearReport();
        return;
    }
    
    const reportData = manifest[currentSelection.contract]?.[currentSelection.timeframe]?.[currentSelection.dateRange];
    
    if (!reportData) {
        clearReport();
        return;
    }
    
    // Show report content, hide no-selection message
    reportContent.classList.remove('hidden');
    noSelection.classList.add('hidden');
    
    // Display HTML dashboards only (PNG gallery removed)
    displayHTMLDashboards(reportData.html);
}


/**
 * Remove date portion from filename for display
 * Input: "NQU25_20250623-20250915_1m_daily_max_extensions.html"
 * Output: "daily_max_extensions.html"
 */
function cleanFilenameForDisplay(filename) {
    // Remove the date pattern: _YYYYMMDD-YYYYMMDD_
    // Pattern matches: _ followed by 8 digits, dash, 8 digits, underscore
    return filename.replace(/_\d{8}-\d{8}_/, '_');
}


/**
 * Check if a report should be excluded from display
 * Returns true if the report should be hidden/removed
 */
function shouldExcludeReport(filename) {
    // Remove date portion to check against patterns
    const cleaned = cleanFilenameForDisplay(filename);
    
    // Reports to exclude (applies to all contracts and timeframes)
    const excludePatterns = [
        'touch_sequence_stats.html',
        'touches_per_day_distribution.html',
        'vwap_events.html',
        'vwap_performance_all_events.html',
        'vwap_performance_crosses_only.html',
        'definitions_summary.html',
        'first_touch_time_distribution.html',
        'index.html'
    ];
    
    // Check if filename matches any exclude pattern
    return excludePatterns.some(pattern => cleaned.includes(pattern));
}


/**
 * Display HTML dashboard links (filtered to exclude specific reports and match timeframe)
 */
function displayHTMLDashboards(htmlFiles) {
    htmlLinks.innerHTML = '';
    
    if (!htmlFiles || htmlFiles.length === 0) {
        dashboardsSection.classList.add('hidden');
        return;
    }
    
    // Filter out excluded reports, wrong-contract files, and ensure timeframe matches
    const filteredFiles = htmlFiles.filter(htmlPath => {
        const filename = htmlPath.split('/').pop();
        
        // First check if report should be excluded
        if (shouldExcludeReport(filename)) {
            return false;
        }
        
        // Ensure the file belongs to the selected contract (exclude wrongly-placed files from other contracts)
        // Pattern: CONTRACT_YYYYMMDD-YYYYMMDD_1m_ or .html/.csv at end
        const otherContractMatch = filename.match(/^([A-Z0-9]+)_\d{8}-\d{8}_\d+m(?:_|\.)/);
        if (otherContractMatch && otherContractMatch[1] !== currentSelection.contract) {
            return false;
        }
        
        // Then check if timeframe matches the selected timeframe
        // If filename has explicit timeframe (e.g. MGCZ25_..._30m_dashboard.html), use that; else use path.
        if (currentSelection.timeframe) {
            const tfInFilename = filename.match(/_(\d+m)_/);
            const fileTimeframe = tfInFilename ? tfInFilename[1] : null;
            const pathHasTimeframe = htmlPath.includes(`_${currentSelection.timeframe}_`);
            
            const matches = fileTimeframe
                ? (fileTimeframe === currentSelection.timeframe)
                : pathHasTimeframe;
            
            if (!matches) {
                console.log(`Filtered out (timeframe mismatch): ${htmlPath} (file tf: ${fileTimeframe || 'path'}, selected: ${currentSelection.timeframe})`);
                return false;
            }
        }
        
        return true;
    });
    
    if (filteredFiles.length === 0) {
        dashboardsSection.classList.add('hidden');
        return;
    }
    
    dashboardsSection.classList.remove('hidden');
    
    // Deduplicate: track seen filenames to prevent duplicates
    const seenFilenames = new Set();
    
    filteredFiles.forEach(htmlPath => {
        const fullFilename = htmlPath.split('/').pop();
        
        // Skip if we've already seen this exact filename
        if (seenFilenames.has(fullFilename)) {
            console.log(`Skipping duplicate: ${fullFilename}`);
            return;
        }
        
        seenFilenames.add(fullFilename);
        
        const link = document.createElement('a');
        link.href = htmlPath;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'dashboard-link';
        link.textContent = cleanFilenameForDisplay(fullFilename);
        htmlLinks.appendChild(link);
    });
}


/**
 * Clear the report display
 */
function clearReport() {
    reportContent.classList.add('hidden');
    noSelection.classList.remove('hidden');
    htmlLinks.innerHTML = '';
    dashboardsSection.classList.add('hidden');
}


/**
 * Update URL parameters to reflect current selection
 */
function updateURL() {
    const params = new URLSearchParams();
    
    if (currentSelection.contract) {
        params.set('contract', currentSelection.contract);
    }
    if (currentSelection.timeframe) {
        params.set('tf', currentSelection.timeframe);
    }
    // Note: We don't include range in URL anymore, but still support it for backward compatibility
    
    const newURL = params.toString() 
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
    
    window.history.replaceState({}, '', newURL);
}


// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadManifest);
} else {
    loadManifest();
}
