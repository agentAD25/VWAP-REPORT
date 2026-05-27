/**
 * app.js
 *
 * VWAP Reports Gallery — manifest-driven contract/timeframe routing to
 * dashboard index pages (dashboards/index.html or folder index.html).
 */

let manifest = null;

const contractSelect = document.getElementById('contract-select');
const timeframeSelect = document.getElementById('timeframe-select');
const reportContent = document.getElementById('report-content');
const noSelection = document.getElementById('no-selection');
const routingMessage = document.getElementById('routing-message');
const routingMessageText = document.getElementById('routing-message-text');

/**
 * Read timeframe from URL (?tf= or ?timeframe=).
 */
function getTimeframeParam(urlParams) {
    return urlParams.get('tf') || urlParams.get('timeframe');
}

/**
 * Build gallery URL with optional contract/timeframe query params.
 */
function buildGalleryUrl(contract, timeframe) {
    const params = new URLSearchParams();
    if (contract) {
        params.set('contract', contract);
    }
    if (timeframe) {
        params.set('timeframe', timeframe);
    }
    const qs = params.toString();
    return qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
}

/**
 * Persist gallery selection in the address bar without adding a history entry.
 */
function syncGalleryUrl(contract, timeframe) {
    const galleryUrl = buildGalleryUrl(contract, timeframe);
    history.replaceState({ page: 'gallery', contract, timeframe }, '', galleryUrl);
}

/**
 * Contract has at least one active routable report.
 */
function contractHasActiveRoutes(contract) {
    const timeframes = manifest[contract];
    if (!timeframes) {
        return false;
    }
    return Object.keys(timeframes).some((tf) => resolveReport(contract, tf) !== null);
}

/**
 * Resolve the canonical (or best active) report for contract + timeframe.
 * Returns { dateRange, ...entry } or null.
 */
function resolveReport(contract, timeframe) {
    const ranges = manifest[contract]?.[timeframe];
    if (!ranges) {
        return null;
    }

    const scoreEntry = (entry) => {
        let score = 0;
        if (entry.public_safe) {
            score += 100;
        }
        if (entry.status === 'CURRENT_CERTIFIED_PUBLIC') {
            score += 50;
        }
        if ((entry.dashboard_index || '').includes('/dashboards/index.html')) {
            score += 25;
        }
        if ((entry.dashboard_index || '').includes('vwap-')) {
            score += 10;
        }
        if (entry.status === 'LEGACY_WITH_DATA_EXPORTS') {
            score -= 200;
        }
        return score;
    };

    const canonicalCandidates = Object.entries(ranges)
        .filter(([, entry]) => entry.active && entry.canonical && entry.dashboard_index)
        .sort((a, b) => scoreEntry(b[1]) - scoreEntry(a[1]));
    if (canonicalCandidates.length > 0) {
        const [dateRange, entry] = canonicalCandidates[0];
        return { dateRange, ...entry };
    }

    const active = Object.entries(ranges)
        .filter(([, entry]) => entry.active && entry.dashboard_index)
        .sort((a, b) => {
            const score = (entry) =>
                (entry.public_safe ? 2 : 0) +
                ((entry.dashboard_index || '').includes('/dashboards/index.html') ? 1 : 0);
            const diff = score(b[1]) - score(a[1]);
            if (diff !== 0) {
                return diff;
            }
            const endA = a[1].end || a[1].end_date || '';
            const endB = b[1].end || b[1].end_date || '';
            return endB.localeCompare(endA);
        });

    if (active.length === 0) {
        return null;
    }

    return { dateRange: active[0][0], ...active[0][1] };
}

/**
 * Navigate to the report dashboard index (normal history-preserving redirect).
 */
function navigateToDashboard(report, contract, timeframe) {
    if (!report?.dashboard_index) {
        return false;
    }
    syncGalleryUrl(contract, timeframe);
    const target = new URL(report.dashboard_index, window.location.href);
    window.location.assign(target.href);
    return true;
}

function showRoutingMessage(text) {
    if (!routingMessage || !routingMessageText) {
        return;
    }
    routingMessageText.textContent = text;
    routingMessage.classList.remove('hidden');
    noSelection.classList.add('hidden');
    reportContent.classList.add('hidden');
}

function hideRoutingMessage() {
    if (routingMessage) {
        routingMessage.classList.add('hidden');
    }
}

function clearGalleryView() {
    hideRoutingMessage();
    reportContent.classList.add('hidden');
    noSelection.classList.remove('hidden');
}

/**
 * Attempt route for contract + timeframe; returns true if redirect started.
 */
function routeSelection(contract, timeframe) {
    hideRoutingMessage();
    if (!contract || !timeframe) {
        clearGalleryView();
        return false;
    }

    const report = resolveReport(contract, timeframe);
    if (!report) {
        showRoutingMessage(
            'No public report is available for this contract/timeframe.'
        );
        return false;
    }

    return navigateToDashboard(report, contract, timeframe);
}

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

function populateContracts() {
    const contracts = Object.keys(manifest)
        .filter(contractHasActiveRoutes)
        .sort();

    contracts.forEach((contract) => {
        const option = document.createElement('option');
        option.value = contract;
        option.textContent = contract;
        contractSelect.appendChild(option);
    });
}

function populateTimeframes(contract) {
    timeframeSelect.innerHTML = '<option value="">-- Select Timeframe --</option>';

    if (!contract || !manifest[contract]) {
        timeframeSelect.disabled = true;
        return;
    }

    const timeframes = Object.keys(manifest[contract])
        .filter((tf) => resolveReport(contract, tf) !== null)
        .sort((a, b) => parseInt(a, 10) - parseInt(b, 10));

    if (timeframes.length === 0) {
        timeframeSelect.disabled = true;
        return;
    }

    timeframeSelect.disabled = false;
    timeframes.forEach((tf) => {
        const option = document.createElement('option');
        option.value = tf;
        option.textContent = tf;
        timeframeSelect.appendChild(option);
    });
}

function handleContractChange() {
    const contract = contractSelect.value || null;
    timeframeSelect.value = '';
    populateTimeframes(contract);
    syncGalleryUrl(contract, null);
    clearGalleryView();
}

function handleTimeframeChange() {
    const contract = contractSelect.value || null;
    const timeframe = timeframeSelect.value || null;
    if (contract && timeframe) {
        routeSelection(contract, timeframe);
    } else {
        syncGalleryUrl(contract, null);
        clearGalleryView();
    }
}

function initializeApp() {
    populateContracts();

    contractSelect.addEventListener('change', handleContractChange);
    timeframeSelect.addEventListener('change', handleTimeframeChange);

    const urlParams = new URLSearchParams(window.location.search);
    const contractParam = urlParams.get('contract');
    const tfParam = getTimeframeParam(urlParams);

    if (contractParam && contractHasActiveRoutes(contractParam)) {
        contractSelect.value = contractParam;
        populateTimeframes(contractParam);
        if (tfParam) {
            if (resolveReport(contractParam, tfParam)) {
                timeframeSelect.value = tfParam;
            } else {
                showRoutingMessage(
                    'No public report is available for this contract/timeframe.'
                );
                return;
            }
        }
        clearGalleryView();
        return;
    }

    if (contractParam) {
        showRoutingMessage(
            'No public report is available for this contract/timeframe.'
        );
        return;
    }

    clearGalleryView();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadManifest);
} else {
    loadManifest();
}
