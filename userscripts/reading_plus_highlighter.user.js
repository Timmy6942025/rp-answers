// ==UserScript==
// @name         Reading Plus Highlighter
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Highlights Reading Plus stories with answers available. Features: fuzzy search, level filtering, click-to-copy, keyboard shortcuts, debug mode.
// @author       Timmy6942025
// @match        *://*/seereader/api/sr/start*
// @match        *://*/dashboard/*
// @match        *://*/student/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      raw.githubusercontent.com
// @connect      githubusercontent.com
// ==/UserScript==

/**
 * Reading Plus Highlighter Userscript
 *
 * Features:
 * - Automatic highlighting of stories with answers in database
 * - Fuzzy search with level filtering
 * - Click-to-copy question counts
 * - Keyboard shortcuts (Ctrl+/ to toggle panel, Esc to close)
 * - Debug mode for troubleshooting
 * - Shadow DOM for style isolation
 * - Robust error handling with user feedback
 */

(function() {
    'use strict';

    // ============== CONFIGURATION ==============
    const CONFIG = {
        manifestUrl: 'https://raw.githubusercontent.com/Timmy6942025/rp-answers/main/data/book_manifest.json',
        debugMode: false,
        matchThreshold: 0.6,
        debounceMs: 150,
        requestTimeout: 10000,
        highlightClass: 'rp-highlight',
        badgeClass: 'rp-badge',
        panelId: 'rpHighlighterPanel'
    };

    // ============== STATE ==============
    let bookManifest = [];
    let isPanelVisible = true;
    let processedElements = new WeakSet();
    let observerThrottleTimer = null;
    let domObserver = null;
    let shadowRoot = null;

    // DOM references
    let panelContainer = null;
    let panelElement = null;
    let searchInput = null;
    let levelSelect = null;
    let resultsList = null;
    let totalBooksEl = null;
    let highlightedCountEl = null;
    let statusMessageEl = null;
    let loadingSpinnerEl = null;

    // ============== UTILITIES ==============

    /**
     * Escape HTML special characters to prevent XSS
     */
    function escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    /**
     * Log debug messages (only when debug mode is enabled)
     */
    function debugLog(...args) {
        if (CONFIG.debugMode) {
            console.log('[RP Highlighter]', ...args);
        }
    }

    /**
     * Update status message for user feedback
     */
    function setStatus(message, type = 'info') {
        if (statusMessageEl) {
            statusMessageEl.textContent = message;
            statusMessageEl.className = 'rp-status-message rp-status-' + type;
            statusMessageEl.style.display = 'block';

            // Auto-hide after 5 seconds for success messages
            if (type === 'success') {
                setTimeout(() => {
                    statusMessageEl.style.display = 'none';
                }, 5000);
            }
        }
    }

    /**
     * Toggle loading spinner
     */
    function setLoading(isLoading) {
        if (loadingSpinnerEl) {
            loadingSpinnerEl.style.display = isLoading ? 'block' : 'none';
        }
    }

    /**
     * Normalize text for comparison
     */
    function normalizeText(text) {
        return String(text).toLowerCase().trim().replace(/\s+/g, ' ');
    }

    /**
     * Fuzzy matching algorithm for book titles
     */
    function fuzzyMatch(title, manifestTitle) {
        const t1 = normalizeText(title);
        const t2 = normalizeText(manifestTitle);

        if (t1 === t2) return 1.0;
        if (t1.includes(t2) || t2.includes(t1)) return 0.9;

        const words1 = t1.split(' ').filter(w => w.length > 2);
        const words2 = t2.split(' ').filter(w => w.length > 2);

        if (words1.length === 0 || words2.length === 0) return 0;

        const matches = words1.filter(w => words2.some(w2 => w2.startsWith(w) || w.startsWith(w2)));
        return matches.length / Math.max(words1.length, words2.length);
    }

    // ============== PANEL CREATION ==============

    /**
     * Create the floating panel using Shadow DOM for style isolation
     */
    function createPanel() {
        // Create container for Shadow DOM
        panelContainer = document.createElement('div');
        panelContainer.id = CONFIG.panelId + '-container';
        panelContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;';

        // Attach Shadow DOM
        shadowRoot = panelContainer.attachShadow({ mode: 'open' });
        document.body.appendChild(panelContainer);

        // Create panel element
        panelElement = document.createElement('div');
        panelElement.className = 'rp-panel';

        // Build panel HTML
        panelElement.innerHTML = `
            <div class="rp-panel-header">
                <h3>Reading Plus Highlighter</h3>
                <div class="rp-header-controls">
                    <button class="rp-btn-icon rp-debug-btn" id="rpDebugBtn" title="Toggle debug mode">🐛</button>
                    <button class="rp-btn-icon rp-toggle-btn" id="rpToggleBtn" title="Toggle panel">−</button>
                </div>
            </div>
            <div class="rp-panel-content">
                <div class="rp-search-section">
                    <input type="text" id="rpSearchInput" placeholder="Search stories..." class="rp-input">
                    <select id="rpLevelSelect" class="rp-select">
                        <option value="">All Levels</option>
                        <option value="A">Level A</option>
                        <option value="B">Level B</option>
                        <option value="C">Level C</option>
                        <option value="D">Level D</option>
                        <option value="E">Level E</option>
                        <option value="F">Level F</option>
                        <option value="G">Level G</option>
                        <option value="H">Level H</option>
                        <option value="HiE">Level HiE</option>
                        <option value="I">Level I</option>
                        <option value="J">Level J</option>
                        <option value="K">Level K</option>
                        <option value="L">Level L</option>
                        <option value="M">Level M</option>
                    </select>
                    <button id="rpSearchBtn" class="rp-btn rp-btn-primary">Search</button>
                </div>

                <div class="rp-status-section">
                    <div id="rpStatusMessage" class="rp-status-message" style="display: none;"></div>
                    <div id="rpLoadingSpinner" class="rp-spinner" style="display: none;"></div>
                </div>

                <div class="rp-results-section">
                    <div class="rp-results-header">
                        <h4>Search Results</h4>
                        <span id="rpResultsCount" class="rp-results-count">0 found</span>
                    </div>
                    <div id="rpResultsList" class="rp-results-list"></div>
                </div>

                <div class="rp-stats-section">
                    <div class="rp-stat-row">
                        <span class="rp-stat-label">Database:</span>
                        <span id="rpTotalBooks" class="rp-stat-value">-</span>
                    </div>
                    <div class="rp-stat-row">
                        <span class="rp-stat-label">Highlighted:</span>
                        <span id="rpHighlightedCount" class="rp-stat-value">-</span>
                    </div>
                    <div class="rp-stat-row">
                        <span class="rp-stat-label">Mode:</span>
                        <span id="rpDebugStatus" class="rp-stat-value">Normal</span>
                    </div>
                </div>

                <div class="rp-help-section">
                    <small>⌨️ Ctrl+/ to toggle • Esc to close • Click count to copy</small>
                </div>
            </div>
        `;

        shadowRoot.appendChild(panelElement);
        addStyles();
        cacheDOMElements();
        setupEventListeners();
    }

    /**
     * Cache frequently accessed DOM elements
     */
    function cacheDOMElements() {
        searchInput = shadowRoot.getElementById('rpSearchInput');
        levelSelect = shadowRoot.getElementById('rpLevelSelect');
        resultsList = shadowRoot.getElementById('rpResultsList');
        totalBooksEl = shadowRoot.getElementById('rpTotalBooks');
        highlightedCountEl = shadowRoot.getElementById('rpHighlightedCount');
        statusMessageEl = shadowRoot.getElementById('rpStatusMessage');
        loadingSpinnerEl = shadowRoot.getElementById('rpLoadingSpinner');
    }

    /**
     * Add scoped styles using Shadow DOM
     */
    function addStyles() {
        const styles = document.createElement('style');
        styles.textContent = `
            .rp-panel {
                width: 320px;
                background: rgba(255, 255, 255, 0.98);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.05);
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .rp-panel.collapsed {
                width: auto;
            }

            .rp-panel.collapsed .rp-panel-content {
                display: none;
            }

            .rp-panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                cursor: pointer;
            }

            .rp-panel-header h3 {
                margin: 0;
                font-size: 14px;
                font-weight: 600;
            }

            .rp-header-controls {
                display: flex;
                gap: 8px;
            }

            .rp-btn-icon {
                background: rgba(255, 255, 255, 0.15);
                border: none;
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .rp-btn-icon:hover {
                background: rgba(255, 255, 255, 0.25);
                transform: scale(1.05);
            }

            .rp-panel.collapsed .rp-toggle-btn {
                transform: rotate(-90deg);
            }

            .rp-panel-content {
                padding: 16px;
            }

            .rp-search-section {
                margin-bottom: 16px;
            }

            .rp-input, .rp-select {
                width: 100%;
                padding: 10px 12px;
                margin-bottom: 8px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 14px;
                box-sizing: border-box;
                transition: all 0.2s;
            }

            .rp-input:focus, .rp-select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
            }

            .rp-btn {
                width: 100%;
                padding: 10px 16px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }

            .rp-btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .rp-btn-primary:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
            }

            .rp-status-section {
                margin-bottom: 12px;
                min-height: 24px;
            }

            .rp-status-message {
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                margin-bottom: 8px;
            }

            .rp-status-info {
                background: #e0e7ff;
                color: #4338ca;
            }

            .rp-status-success {
                background: #dcfce7;
                color: #166534;
            }

            .rp-status-error {
                background: #fee2e2;
                color: #991b1b;
            }

            .rp-spinner {
                width: 20px;
                height: 20px;
                border: 2px solid #e2e8f0;
                border-top-color: #667eea;
                border-radius: 50%;
                animation: rp-spin 0.8s linear infinite;
            }

            @keyframes rp-spin {
                to { transform: rotate(360deg); }
            }

            .rp-results-section {
                margin-bottom: 16px;
            }

            .rp-results-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .rp-results-header h4 {
                margin: 0;
                font-size: 13px;
                font-weight: 600;
                color: #334155;
            }

            .rp-results-count {
                font-size: 12px;
                color: #64748b;
            }

            .rp-results-list {
                max-height: 180px;
                overflow-y: auto;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }

            .rp-result-item {
                padding: 10px 12px;
                margin: 4px;
                background: white;
                border-radius: 6px;
                border-left: 3px solid #22c55e;
                cursor: pointer;
                transition: all 0.2s;
            }

            .rp-result-item:hover {
                background: #f1f5f9;
                transform: translateX(2px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }

            .rp-result-title {
                font-weight: 600;
                font-size: 12px;
                color: #1e293b;
                margin-bottom: 4px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .rp-result-meta {
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: #64748b;
            }

            .rp-result-count {
                font-weight: 600;
                color: #667eea;
                cursor: pointer;
                padding: 2px 6px;
                border-radius: 4px;
                transition: all 0.2s;
            }

            .rp-result-count:hover {
                background: #e0e7ff;
            }

            .rp-result-count.copied {
                background: #22c55e;
                color: white;
            }

            .rp-stats-section {
                background: #f8fafc;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #e2e8f0;
            }

            .rp-stat-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 6px;
                font-size: 12px;
            }

            .rp-stat-row:last-child {
                margin-bottom: 0;
            }

            .rp-stat-label {
                color: #64748b;
            }

            .rp-stat-value {
                font-weight: 600;
                color: #334155;
            }

            .rp-help-section {
                margin-top: 12px;
                text-align: center;
                color: #94a3b8;
                font-size: 11px;
            }

            /* Highlight styles (applied to page elements, not in Shadow DOM) */
            .${CONFIG.highlightClass} {
                background: linear-gradient(120deg, #f093fb 0%, #f5576c 100%) !important;
                color: white !important;
                font-weight: bold !important;
                padding: 2px 6px !important;
                border-radius: 4px !important;
                animation: rp-highlight-pulse 2s ease-in-out infinite;
            }

            @keyframes rp-highlight-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.85; }
            }

            .${CONFIG.badgeClass} {
                position: absolute;
                top: 6px;
                right: 6px;
                background: #22c55e !important;
                color: white !important;
                padding: 3px 8px !important;
                border-radius: 4px !important;
                font-size: 10px !important;
                font-weight: bold !important;
                z-index: 100;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
                pointer-events: none;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .rp-panel {
                    width: 280px;
                    right: 10px;
                    top: 10px;
                }
            }
        `;
        shadowRoot.appendChild(styles);
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Toggle panel
        shadowRoot.querySelector('.rp-panel-header').addEventListener('click', (e) => {
            if (!e.target.closest('.rp-btn-icon')) {
                togglePanel();
            }
        });

        // Debug toggle
        shadowRoot.getElementById('rpDebugBtn').addEventListener('click', toggleDebugMode);

        // Toggle button
        shadowRoot.getElementById('rpToggleBtn').addEventListener('click', togglePanel);

        // Search
        shadowRoot.getElementById('rpSearchBtn').addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
        levelSelect.addEventListener('change', performSearch);

        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    /**
     * Handle keyboard shortcuts
     */
    function handleKeyboardShortcuts(e) {
        // Ctrl+/ or Ctrl+\ to toggle panel
        if ((e.ctrlKey || e.metaKey) && (e.key === '/' || e.key === '\\')) {
            e.preventDefault();
            togglePanel();
        }

        // Escape to close panel
        if (e.key === 'Escape' && isPanelVisible) {
            panelElement.classList.add('collapsed');
            isPanelVisible = false;
        }
    }

    /**
     * Toggle panel visibility
     */
    function togglePanel() {
        isPanelVisible = !isPanelVisible;
        if (isPanelVisible) {
            panelElement.classList.remove('collapsed');
        } else {
            panelElement.classList.add('collapsed');
        }
    }

    /**
     * Toggle debug mode
     */
    function toggleDebugMode() {
        CONFIG.debugMode = !CONFIG.debugMode;
        const debugStatus = shadowRoot.getElementById('rpDebugStatus');
        debugStatus.textContent = CONFIG.debugMode ? 'Debug' : 'Normal';

        if (CONFIG.debugMode) {
            setStatus('Debug mode enabled - check console for logs', 'info');
            debugLog('Debug mode activated');
        }
    }

    // ============== DATA LOADING ==============

    /**
     * Load book manifest from GitHub
     */
    function loadBookManifest() {
        setLoading(true);
        setStatus('Loading database...', 'info');

        GM_xmlhttpRequest({
            method: 'GET',
            url: CONFIG.manifestUrl,
            timeout: CONFIG.requestTimeout,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            onload: function(response) {
                setLoading(false);
                try {
                    bookManifest = JSON.parse(response.responseText);

                    if (!Array.isArray(bookManifest) || bookManifest.length === 0) {
                        throw new Error('Invalid manifest format or empty');
                    }

                    debugLog('Loaded', bookManifest.length, 'books');
                    setStatus(`Loaded ${bookManifest.length} stories`, 'success');

                    // Update stats
                    totalBooksEl.textContent = bookManifest.length;

                    // Initial search
                    if (domObserver) domObserver.disconnect();
                    performSearch();
                    if (domObserver) resumeObserver();

                } catch (error) {
                    debugLog('Parse error:', error);
                    setStatus('Error loading database', 'error');
                    totalBooksEl.textContent = 'Error';
                }
            },
            onerror: function(error) {
                setLoading(false);
                debugLog('Network error:', error);
                setStatus('Failed to load database', 'error');
                totalBooksEl.textContent = 'Offline';
            },
            ontimeout: function() {
                setLoading(false);
                debugLog('Request timeout');
                setStatus('Database request timed out', 'error');
            }
        });
    }

    // ============== SEARCH ==============

    /**
     * Search books in manifest
     */
    function searchBooks(query, level) {
        if (!bookManifest.length) return [];

        let results = [];

        if (query) {
            results = bookManifest.filter(book => {
                const score = fuzzyMatch(book.title, query);
                const levelMatch = !level || book.level === level;
                return score >= CONFIG.matchThreshold && levelMatch;
            });
        } else if (level) {
            results = bookManifest.filter(book => book.level === level);
        }

        // Sort by question count (most questions first)
        return results.sort((a, b) => b.count - a.count);
    }

    /**
     * Perform search and display results
     */
    function performSearch() {
        const query = searchInput.value.trim();
        const level = levelSelect.value;

        const results = searchBooks(query, level);

        // Update results count
        const countEl = shadowRoot.getElementById('rpResultsCount');
        countEl.textContent = results.length + ' found';

        // Display results
        if (results.length === 0) {
            resultsList.innerHTML = '<div class="rp-result-item" style="border-left-color: #94a3b8; cursor: default;">' +
                '<div class="rp-result-title">No matches found</div>' +
                '<div class="rp-result-meta">Try different keywords or level</div>' +
                '</div>';
            return;
        }

        const resultsHTML = results.slice(0, 20).map(book => `
            <div class="rp-result-item" data-title="${escapeHtml(book.title)}" data-level="${escapeHtml(book.level)}" data-count="${book.count}">
                <div class="rp-result-title" title="${escapeHtml(book.title)}">${escapeHtml(book.title)}</div>
                <div class="rp-result-meta">
                    <span>Level ${escapeHtml(book.level)}</span>
                    <span class="rp-result-count" data-count="${book.count}">${book.count} questions</span>
                </div>
            </div>
        `).join('');

        resultsList.innerHTML = resultsHTML;

        // Add click-to-copy handlers
        resultsList.querySelectorAll('.rp-result-count').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const count = e.target.dataset.count;
                navigator.clipboard.writeText(count).then(() => {
                    e.target.classList.add('copied');
                    e.target.textContent = 'Copied!';
                    setTimeout(() => {
                        e.target.classList.remove('copied');
                        e.target.textContent = count + ' questions';
                    }, 1500);
                });
            });
        });

        debugLog('Search returned', results.length, 'results');
    }

    // ============== HIGHLIGHTING ==============

    /**
     * Setup MutationObserver for dynamic content
     */
    function setupObserver() {
        domObserver = new MutationObserver(() => {
            if (observerThrottleTimer) return;
            observerThrottleTimer = setTimeout(() => {
                observerThrottleTimer = null;
                checkAndHighlightBooks();
            }, CONFIG.debounceMs);
        });

        resumeObserver();
    }

    /**
     * Resume observer observation
     */
    function resumeObserver() {
        if (domObserver) {
            domObserver.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: false,
                attributes: false
            });
        }
    }

    /**
     * Check and highlight matching books
     */
    function checkAndHighlightBooks() {
        if (!bookManifest.length) return;

        const bookElements = findBookElements();
        let highlightedCount = 0;

        bookElements.forEach(element => {
            if (processedElements.has(element)) return;

            const bookTitle = extractBookTitle(element);
            if (!bookTitle) return;

            const matchingBook = findMatchingBook(bookTitle);
            if (!matchingBook) return;

            // Pause observer, highlight, resume
            domObserver.disconnect();
            highlightBook(element, matchingBook);
            processedElements.add(element);
            resumeObserver();
            highlightedCount++;
        });

        if (highlightedCount > 0) {
            highlightedCountEl.textContent = highlightedCount;
            debugLog('Highlighted', highlightedCount, 'new books');
        }
    }

    /**
     * Find potential book elements on page
     */
    function findBookElements() {
        const selectors = [
            '[class*="book"]',
            '[class*="story"]',
            '[class*="card"]',
            '[class*="title"]',
            '[data-book-title]',
            '[data-story-title]',
            '[data-testid*="title"]'
        ];

        const elements = [];
        selectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(el => {
                    const text = el.textContent?.trim();
                    if (text && text.length > 10 && text.length < 500 && !elements.includes(el)) {
                        elements.push(el);
                    }
                });
            } catch (e) {
                // Invalid selector, skip
            }
        });

        return elements;
    }

    /**
     * Extract book title from element
     */
    function extractBookTitle(element) {
        const titleAttrs = ['data-book-title', 'data-story-title', 'data-title', 'title'];

        for (const attr of titleAttrs) {
            const val = element.getAttribute(attr);
            if (val && val.trim().length > 0) {
                return val.trim();
            }
        }

        // Use text content
        const text = element.textContent?.trim();
        if (text && text.length > 5 && text.length < 300) {
            return text;
        }

        return null;
    }

    /**
     * Find best matching book in manifest
     */
    function findMatchingBook(title) {
        let bestMatch = null;
        let bestScore = 0;

        for (const book of bookManifest) {
            const score = fuzzyMatch(title, book.title);
            if (score > bestScore) {
                bestScore = score;
                bestMatch = book;
            }
        }

        return bestScore >= CONFIG.matchThreshold ? bestMatch : null;
    }

    /**
     * Apply highlight to element
     */
    function highlightBook(element, book) {
        if (element.classList.contains(CONFIG.highlightClass)) return;

        element.classList.add(CONFIG.highlightClass);
        element.style.position = 'relative';

        // Check for existing badge
        if (!element.querySelector('.' + CONFIG.badgeClass)) {
            const badge = document.createElement('span');
            badge.className = CONFIG.badgeClass;
            badge.textContent = book.count + ' answers';
            element.appendChild(badge);
        }

        debugLog('Highlighted:', book.title);
    }

    // ============== INITIALIZATION ==============

    /**
     * Initialize the userscript
     */
    function initialize() {
        debugLog('Initializing...');

        createPanel();
        setupObserver();
        loadBookManifest();

        // Initial check after delay
        setTimeout(() => {
            if (domObserver) domObserver.disconnect();
            checkAndHighlightBooks();
            resumeObserver();
        }, 2000);

        debugLog('Initialization complete');
    }

    /**
     * Cleanup on script unload
     */
    function cleanup() {
        if (domObserver) {
            domObserver.disconnect();
        }
        document.removeEventListener('keydown', handleKeyboardShortcuts);
        debugLog('Cleanup complete');
    }

    // Handle page unload
    window.addEventListener('beforeunload', cleanup);

    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();
