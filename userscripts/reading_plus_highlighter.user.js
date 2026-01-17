// ==UserScript==
// @name         Reading Plus Highlighter
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Highlights Reading Plus stories with answers. Features: fuzzy search, level filtering, click-to-copy, keyboard shortcuts, auto-update, debug mode.
// @author       Timmy6942025
// @match        *://*/seereader/api/sr/start*
// @match        *://*/dashboard/*
// @match        *://*/student/*
// @match        *://*.readingplus.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      raw.githubusercontent.com
// @connect      githubusercontent.com
// ==/UserScript==

/**
 * Reading Plus Highlighter Userscript v2.1
 *
 * Features:
 * - Auto-highlighting of stories with answers in database
 * - Fuzzy search with level filtering
 * - Click-to-copy question counts
 * - Keyboard shortcuts (Ctrl+/ toggle, Esc close, F mini mode)
 * - Auto-update manifest checking
 * - Debug mode for troubleshooting
 * - Shadow DOM for style isolation
 * - Performance metrics display
 * - Offline mode with local caching
 * - Smart Reading Plus page detection
 */

(function() {
    'use strict';

    // ============== VERSION & CONFIG ==============
    const VERSION = '2.1';
    const SCRIPT_ID = 'reading-plus-highlighter';

    const CONFIG = {
        manifestUrl: 'https://raw.githubusercontent.com/Timmy6942025/rp-answers/main/data/book_manifest.json',
        versionUrl: 'https://raw.githubusercontent.com/Timmy6942025/rp-answers/main/userscripts/reading_plus_highlighter.user.js',
        debugMode: false,
        matchThreshold: 0.6,
        debounceMs: 150,
        requestTimeout: 15000,
        cacheExpiryMs: 24 * 60 * 60 * 1000, // 24 hours
        highlightClass: 'rp-highlight',
        badgeClass: 'rp-badge',
        panelId: 'rpHighlighterPanel',
        storageKey: SCRIPT_ID
    };

    // ============== STATE ==============
    let bookManifest = [];
    let isPanelVisible = true;
    let isMiniMode = false;
    let processedElements = new WeakSet();
    let observerThrottleTimer = null;
    let domObserver = null;
    let shadowRoot = null;
    let cachedManifest = null;

    // Performance tracking
    let perfMetrics = {
        loadTime: 0,
        highlightCount: 0,
        searchCount: 0,
        lastUpdate: null
    };

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
    let perfMetricsEl = null;

    // ============== UTILITIES ==============

    function escapeHtml(text) {
        if (text == null) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    function debugLog(...args) {
        if (CONFIG.debugMode) {
            console.log(`[RP Highlighter v${VERSION}]`, ...args);
        }
    }

    function setStatus(message, type = 'info', duration = 0) {
        if (statusMessageEl) {
            statusMessageEl.textContent = message;
            statusMessageEl.className = 'rp-status-message rp-status-' + type;
            statusMessageEl.style.display = 'block';

            // Auto-hide after duration (0 = never)
            if (duration > 0) {
                setTimeout(() => {
                    statusMessageEl.style.display = 'none';
                }, duration);
            }
        }
    }

    function setLoading(isLoading) {
        if (loadingSpinnerEl) {
            loadingSpinnerEl.style.display = isLoading ? 'block' : 'none';
        }
    }

    function normalizeText(text) {
        return String(text).toLowerCase().trim().replace(/\s+/g, ' ');
    }

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

    // ============== STORAGE ==============

    function saveToCache(manifest, timestamp) {
        try {
            const data = { manifest, timestamp };
            GM_setValue(CONFIG.storageKey + '_cache', JSON.stringify(data));
            debugLog('Manifest cached');
        } catch (e) {
            debugLog('Cache save failed:', e);
        }
    }

    function loadFromCache() {
        try {
            const cached = GM_getValue(CONFIG.storageKey + '_cache', null);
            if (cached) {
                const data = JSON.parse(cached);
                const age = Date.now() - data.timestamp;
                if (age < CONFIG.cacheExpiryMs) {
                    debugLog('Using cached manifest, age:', Math.round(age / 60000), 'minutes');
                    return data.manifest;
                }
                debugLog('Cache expired, age:', Math.round(age / 60000), 'minutes');
            }
        } catch (e) {
            debugLog('Cache load failed:', e);
        }
        return null;
    }

    // ============== PAGE DETECTION ==============

    function detectReadingPlusPage() {
        const url = window.location.href;
        const path = window.location.pathname;

        // Check URL patterns
        if (url.includes('/seereader/api/sr/start')) {
            return { type: 'reader', name: 'SeeReader' };
        }
        if (url.includes('/dashboard')) {
            return { type: 'dashboard', name: 'Dashboard' };
        }
        if (url.includes('/student')) {
            return { type: 'student', name: 'Student Portal' };
        }
        if (url.includes('readingplus.com')) {
            return { type: 'other', name: 'Reading Plus' };
        }

        return { type: 'unknown', name: 'Unknown' };
    }

    // ============== PANEL CREATION ==============

    function createPanel() {
        panelContainer = document.createElement('div');
        panelContainer.id = CONFIG.panelId + '-container';
        panelContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 2147483647; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;';

        shadowRoot = panelContainer.attachShadow({ mode: 'open' });
        document.body.appendChild(panelContainer);

        panelElement = document.createElement('div');
        panelElement.className = 'rp-panel';

        panelElement.innerHTML = `
            <div class="rp-panel-header">
                <h3><span class="rp-version-badge">v${VERSION}</span> Reading Plus Highlighter</h3>
                <div class="rp-header-controls">
                    <button class="rp-btn-icon rp-mini-btn" id="rpMiniBtn" title="Mini mode (F)">◧</button>
                    <button class="rp-btn-icon rp-debug-btn" id="rpDebugBtn" title="Debug (D)">🐛</button>
                    <button class="rp-btn-icon rp-toggle-btn" id="rpToggleBtn" title="Toggle">−</button>
                </div>
            </div>
            <div class="rp-panel-content">
                <div class="rp-page-info" id="rpPageInfo">
                    <span class="rp-page-badge">Detecting...</span>
                </div>

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
                    <button id="rpRefreshBtn" class="rp-btn rp-btn-secondary">Refresh</button>
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
                        <span class="rp-stat-label">Status:</span>
                        <span id="rpStatusIndicator" class="rp-stat-value">-</span>
                    </div>
                </div>

                <div class="rp-perf-section" id="rpPerfSection">
                    <div class="rp-perf-row">
                        <span>Load: <span id="rpLoadTime">-</span></span>
                        <span>Searches: <span id="rpSearchCount">0</span></span>
                    </div>
                </div>

                <div class="rp-help-section">
                    <small>⌨️ Ctrl+/ toggle • Esc close • F mini • D debug • Click count to copy</small>
                </div>
            </div>
        `;

        shadowRoot.appendChild(panelElement);
        addStyles();
        cacheDOMElements();
        setupEventListeners();
        updatePageInfo();
    }

    function cacheDOMElements() {
        searchInput = shadowRoot.getElementById('rpSearchInput');
        levelSelect = shadowRoot.getElementById('rpLevelSelect');
        resultsList = shadowRoot.getElementById('rpResultsList');
        totalBooksEl = shadowRoot.getElementById('rpTotalBooks');
        highlightedCountEl = shadowRoot.getElementById('rpHighlightedCount');
        statusMessageEl = shadowRoot.getElementById('rpStatusMessage');
        loadingSpinnerEl = shadowRoot.getElementById('rpLoadingSpinner');
        perfMetricsEl = shadowRoot.getElementById('rpPerfSection');
    }

    function updatePageInfo() {
        const pageInfo = shadowRoot.getElementById('rpPageInfo');
        const page = detectReadingPlusPage();
        pageInfo.innerHTML = `<span class="rp-page-badge rp-page-${page.type}">${page.name}</span>`;
        debugLog('Detected page type:', page.type);
    }

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

            .rp-panel.mini {
                width: 200px;
            }

            .rp-panel.mini .rp-panel-content,
            .rp-panel.mini .rp-help-section,
            .rp-panel.mini .rp-search-section {
                display: none;
            }

            .rp-panel.collapsed .rp-panel-content {
                display: none;
            }

            .rp-panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                cursor: pointer;
            }

            .rp-panel-header h3 {
                margin: 0;
                font-size: 13px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .rp-version-badge {
                background: rgba(255,255,255,0.2);
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
            }

            .rp-header-controls {
                display: flex;
                gap: 6px;
            }

            .rp-btn-icon {
                background: rgba(255, 255, 255, 0.15);
                border: none;
                color: white;
                width: 26px;
                height: 26px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
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
                padding: 14px;
            }

            .rp-page-info {
                margin-bottom: 12px;
            }

            .rp-page-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                background: #e0e7ff;
                color: #4338ca;
            }

            .rp-page-reader { background: #dcfce7; color: #166534; }
            .rp-page-dashboard { background: #dbeafe; color: #1e40af; }
            .rp-page-student { background: #fef3c7; color: #92400e; }

            .rp-search-section {
                margin-bottom: 12px;
            }

            .rp-input, .rp-select {
                width: 100%;
                padding: 8px 10px;
                margin-bottom: 6px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 13px;
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
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                margin-bottom: 6px;
            }

            .rp-btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .rp-btn-primary:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
            }

            .rp-btn-secondary {
                background: #f1f5f9;
                color: #475569;
            }

            .rp-btn-secondary:hover {
                background: #e2e8f0;
            }

            .rp-status-section {
                margin-bottom: 10px;
                min-height: 20px;
            }

            .rp-status-message {
                padding: 6px 10px;
                border-radius: 5px;
                font-size: 11px;
                margin-bottom: 6px;
            }

            .rp-status-info { background: #e0e7ff; color: #4338ca; }
            .rp-status-success { background: #dcfce7; color: #166534; }
            .rp-status-error { background: #fee2e2; color: #991b1b; }
            .rp-status-warning { background: #fef3c7; color: #92400e; }

            .rp-spinner {
                width: 18px;
                height: 18px;
                border: 2px solid #e2e8f0;
                border-top-color: #667eea;
                border-radius: 50%;
                animation: rp-spin 0.8s linear infinite;
            }

            @keyframes rp-spin { to { transform: rotate(360deg); } }

            .rp-results-section {
                margin-bottom: 12px;
            }

            .rp-results-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }

            .rp-results-header h4 {
                margin: 0;
                font-size: 12px;
                font-weight: 600;
                color: #334155;
            }

            .rp-results-count {
                font-size: 11px;
                color: #64748b;
            }

            .rp-results-list {
                max-height: 150px;
                overflow-y: auto;
                background: #f8fafc;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
            }

            .rp-result-item {
                padding: 8px 10px;
                margin: 3px;
                background: white;
                border-radius: 5px;
                border-left: 3px solid #22c55e;
                cursor: pointer;
                transition: all 0.2s;
            }

            .rp-result-item:hover {
                background: #f1f5f9;
                transform: translateX(2px);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            }

            .rp-result-title {
                font-weight: 600;
                font-size: 11px;
                color: #1e293b;
                margin-bottom: 3px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .rp-result-meta {
                display: flex;
                justify-content: space-between;
                font-size: 10px;
                color: #64748b;
            }

            .rp-result-count {
                font-weight: 600;
                color: #667eea;
                cursor: pointer;
                padding: 1px 5px;
                border-radius: 3px;
                transition: all 0.2s;
            }

            .rp-result-count:hover { background: #e0e7ff; }
            .rp-result-count.copied { background: #22c55e; color: white; }

            .rp-stats-section {
                background: #f8fafc;
                border-radius: 6px;
                padding: 10px;
                border: 1px solid #e2e8f0;
                margin-bottom: 10px;
            }

            .rp-stat-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 4px;
                font-size: 11px;
            }

            .rp-stat-row:last-child { margin-bottom: 0; }
            .rp-stat-label { color: #64748b; }
            .rp-stat-value { font-weight: 600; color: #334155; }

            .rp-perf-section {
                background: #fef3c7;
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 10px;
                font-size: 10px;
                color: #92400e;
            }

            .rp-perf-row {
                display: flex;
                justify-content: space-between;
            }

            .rp-help-section {
                margin-top: 10px;
                text-align: center;
                color: #94a3b8;
                font-size: 10px;
            }

            /* Highlight styles (outside Shadow DOM) */
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
                top: 4px;
                right: 4px;
                background: #22c55e !important;
                color: white !important;
                padding: 2px 6px !important;
                border-radius: 4px !important;
                font-size: 9px !important;
                font-weight: bold !important;
                z-index: 100;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                pointer-events: none;
            }

            @media (max-width: 768px) {
                .rp-panel { width: 280px; right: 10px; top: 10px; }
            }
        `;
        shadowRoot.appendChild(styles);
    }

    function setupEventListeners() {
        // Header click (except buttons)
        shadowRoot.querySelector('.rp-panel-header').addEventListener('click', (e) => {
            if (!e.target.closest('.rp-btn-icon')) {
                togglePanel();
            }
        });

        // Mini mode toggle
        shadowRoot.getElementById('rpMiniBtn').addEventListener('click', toggleMiniMode);

        // Debug toggle
        shadowRoot.getElementById('rpDebugBtn').addEventListener('click', toggleDebugMode);

        // Toggle button
        shadowRoot.getElementById('rpToggleBtn').addEventListener('click', togglePanel);

        // Search and refresh
        shadowRoot.getElementById('rpSearchBtn').addEventListener('click', performSearch);
        shadowRoot.getElementById('rpRefreshBtn').addEventListener('click', () => loadBookManifest(true));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
        levelSelect.addEventListener('change', performSearch);

        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    function handleKeyboardShortcuts(e) {
        // Ctrl+/ or Ctrl+\ to toggle panel
        if ((e.ctrlKey || e.metaKey) && (e.key === '/' || e.key === '\\')) {
            e.preventDefault();
            togglePanel();
        }

        // F for mini mode
        if (e.key === 'F' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            if (document.activeElement === document.body || document.activeElement === panelContainer) {
                e.preventDefault();
                toggleMiniMode();
            }
        }

        // D for debug mode
        if (e.key === 'D' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            if (document.activeElement === document.body || document.activeElement === panelContainer) {
                e.preventDefault();
                toggleDebugMode();
            }
        }

        // Escape to close panel
        if (e.key === 'Escape' && isPanelVisible) {
            panelElement.classList.add('collapsed');
            isPanelVisible = false;
        }
    }

    function togglePanel() {
        isPanelVisible = !isPanelVisible;
        if (isPanelVisible) {
            panelElement.classList.remove('collapsed');
        } else {
            panelElement.classList.add('collapsed');
        }
    }

    function toggleMiniMode() {
        isMiniMode = !isMiniMode;
        panelElement.classList.toggle('mini', isMiniMode);
        debugLog('Mini mode:', isMiniMode);
    }

    function toggleDebugMode() {
        CONFIG.debugMode = !CONFIG.debugMode;

        if (CONFIG.debugMode) {
            setStatus('Debug mode ON - check console (D to toggle)', 'info', 3000);
            debugLog('Debug mode activated');
        } else {
            setStatus('Debug mode OFF', 'info', 2000);
        }

        // Update status indicator
        const statusIndicator = shadowRoot.getElementById('rpStatusIndicator');
        if (statusIndicator) {
            statusIndicator.textContent = CONFIG.debugMode ? 'Debug' : 'Normal';
        }
    }

    // ============== DATA LOADING ==============

    function loadBookManifest(forceRefresh = false) {
        setLoading(true);

        // Try cache first (unless force refresh)
        if (!forceRefresh) {
            cachedManifest = loadFromCache();
            if (cachedManifest && cachedManifest.length > 0) {
                bookManifest = cachedManifest;
                setLoading(false);
                onManifestLoaded(true);
                return;
            }
        }

        setStatus('Loading database...', 'info');

        const startTime = Date.now();

        GM_xmlhttpRequest({
            method: 'GET',
            url: CONFIG.manifestUrl,
            timeout: CONFIG.requestTimeout,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            onload: function(response) {
                setLoading(false);
                const loadTime = Date.now() - startTime;
                perfMetrics.loadTime = loadTime;

                try {
                    bookManifest = JSON.parse(response.responseText);

                    if (!Array.isArray(bookManifest) || bookManifest.length === 0) {
                        throw new Error('Invalid manifest format or empty');
                    }

                    // Cache the manifest
                    saveToCache(bookManifest, Date.now());
                    perfMetrics.lastUpdate = Date.now();

                    debugLog('Loaded', bookManifest.length, 'books in', loadTime, 'ms');
                    setStatus(`Loaded ${bookManifest.length} stories (${loadTime}ms)`, 'success', 3000);

                    onManifestLoaded(false);

                } catch (error) {
                    debugLog('Parse error:', error);
                    setStatus('Error loading database', 'error');

                    // Try to use cache on error
                    cachedManifest = loadFromCache();
                    if (cachedManifest && cachedManifest.length > 0) {
                        bookManifest = cachedManifest;
                        setStatus('Using cached data', 'warning', 3000);
                        onManifestLoaded(true);
                    } else {
                        totalBooksEl.textContent = 'Error';
                    }
                }
            },
            onerror: function(error) {
                setLoading(false);
                debugLog('Network error:', error);
                setStatus('Failed to load - checking cache...', 'error');

                // Try cache on network error
                cachedManifest = loadFromCache();
                if (cachedManifest && cachedManifest.length > 0) {
                    bookManifest = cachedManifest;
                    setStatus('Offline mode - using cached data', 'warning', 5000);
                    onManifestLoaded(true);
                } else {
                    totalBooksEl.textContent = 'Offline';
                    setStatus('No cached data available', 'error');
                }
            },
            ontimeout: function() {
                setLoading(false);
                debugLog('Request timeout');
                setStatus('Request timed out - checking cache...', 'error');

                cachedManifest = loadFromCache();
                if (cachedManifest && cachedManifest.length > 0) {
                    bookManifest = cachedManifest;
                    setStatus('Timeout - using cached data', 'warning', 5000);
                    onManifestLoaded(true);
                }
            }
        });
    }

    function onManifestLoaded(fromCache) {
        totalBooksEl.textContent = bookManifest.length;

        const statusIndicator = shadowRoot.getElementById('rpStatusIndicator');
        if (statusIndicator) {
            statusIndicator.textContent = fromCache ? 'Cached' : 'Live';
            statusIndicator.style.color = fromCache ? '#f59e0b' : '#22c55e';
        }

        updatePerfMetrics();

        if (domObserver) domObserver.disconnect();
        performSearch();
        if (domObserver) resumeObserver();
    }

    function updatePerfMetrics() {
        const loadTimeEl = shadowRoot.getElementById('rpLoadTime');
        const searchCountEl = shadowRoot.getElementById('rpSearchCount');

        if (loadTimeEl) {
            loadTimeEl.textContent = perfMetrics.loadTime > 0 ? perfMetrics.loadTime + 'ms' : '-';
        }
        if (searchCountEl) {
            searchCountEl.textContent = perfMetrics.searchCount;
        }
    }

    // ============== SEARCH ==============

    function searchBooks(query, level) {
        if (!bookManifest.length) return [];

        perfMetrics.searchCount++;

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

        return results.sort((a, b) => b.count - a.count);
    }

    function performSearch() {
        const query = searchInput.value.trim();
        const level = levelSelect.value;

        const results = searchBooks(query, level);
        updatePerfMetrics();

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

        // Click-to-copy handlers
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

            domObserver.disconnect();
            highlightBook(element, matchingBook);
            processedElements.add(element);
            resumeObserver();
            highlightedCount++;
        });

        if (highlightedCount > 0) {
            perfMetrics.highlightCount += highlightedCount;
            highlightedCountEl.textContent = perfMetrics.highlightCount;
            debugLog('Highlighted', highlightedCount, 'new books (total:', perfMetrics.highlightCount, ')');
        }
    }

    function findBookElements() {
        // Reading Plus specific selectors
        const selectors = [
            // Common Reading Plus patterns
            '[class*="book"]',
            '[class*="story"]',
            '[class*="passage"]',
            '[class*="selection"]',
            '[class*="card"]',
            '[class*="title"]',
            '[class*="heading"]',
            // Data attributes
            '[data-book-title]',
            '[data-story-title]',
            '[data-selection-title]',
            '[data-testid*="title"]',
            // SeeReader specific
            '.sr-book-title',
            '.sr-story-title',
            '.sr-selection-title'
        ];

        const elements = [];
        const seen = new Set();

        selectors.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(el => {
                    const text = el.textContent?.trim();
                    // Filter: reasonable length, not already seen
                    if (text && text.length > 10 && text.length < 400 && !seen.has(el)) {
                        // Additional check: skip elements that are too nested or contain too many children
                        if (el.children.length < 20) {
                            seen.add(el);
                            elements.push(el);
                        }
                    }
                });
            } catch (e) {
                // Invalid selector, skip
            }
        });

        return elements;
    }

    function extractBookTitle(element) {
        const titleAttrs = [
            'data-book-title',
            'data-story-title',
            'data-selection-title',
            'data-title',
            'title'
        ];

        for (const attr of titleAttrs) {
            const val = element.getAttribute(attr);
            if (val && val.trim().length > 0) {
                return val.trim();
            }
        }

        // Use text content, but be more selective
        const text = element.textContent?.trim();
        if (text && text.length > 5 && text.length < 300) {
            // Skip if it looks like UI text rather than a title
            const lower = text.toLowerCase();
            const skipPatterns = ['click', 'select', 'choose', 'answer', 'question', 'read more', 'show less'];
            if (!skipPatterns.some(p => lower.includes(p))) {
                return text;
            }
        }

        return null;
    }

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

    function highlightBook(element, book) {
        if (element.classList.contains(CONFIG.highlightClass)) return;

        element.classList.add(CONFIG.highlightClass);
        element.style.position = 'relative';

        if (!element.querySelector('.' + CONFIG.badgeClass)) {
            const badge = document.createElement('span');
            badge.className = CONFIG.badgeClass;
            badge.textContent = book.count + ' answers';
            element.appendChild(badge);
        }

        debugLog('Highlighted:', book.title);
    }

    // ============== INITIALIZATION ==============

    function initialize() {
        debugLog('Initializing v' + VERSION + '...');

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

    function cleanup() {
        if (domObserver) {
            domObserver.disconnect();
        }
        document.removeEventListener('keydown', handleKeyboardShortcuts);
        debugLog('Cleanup complete');
    }

    window.addEventListener('beforeunload', cleanup);

    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();
